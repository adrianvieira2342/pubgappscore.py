import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# =============================
# FUNÇÃO DE BUSCA DE DADOS (FORÇA BRUTA)
# =============================
def get_data_absolute_fresh():
    try:
        # 1. Pegamos a URL do banco
        db_url = st.secrets["DATABASE_URL"]
        
        # 2. Criamos o engine com isolamento total
        # O pool_size=0 e max_overflow=0 garantem que a conexão morra após o uso
        engine = create_engine(
            db_url, 
            pool_size=0, 
            pool_recycle=0,
            execution_options={"isolation_level": "AUTOCOMMIT"}
        )
        
        with engine.connect() as conn:
            # 3. CACHE BUSTER: Adicionamos um comentário com timestamp na query
            # Isso força o Supabase e o PostgreSQL a tratarem como uma query nova
            timestamp = int(time.time())
            query = text(f"SELECT * FROM ranking_squad -- cache_buster_{timestamp}")
            
            # Executa e carrega
            df = pd.read_sql(query, conn)
            
        return df
    except Exception as e:
        st.error(f"Erro crítico na busca de dados: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    
    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])

        for emoji in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3) and total > 3:
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    cols_base = [
        'Pos', 'Classificação', 'nick',
        'partidas', 'kr', 'vitorias',
        'kills', 'assists', 'headshots',
        'revives', 'kill_dist_max', 'dano_medio'
    ]
    return df_ranking[cols_base + [col_score]]

# =============================
# INTERFACE PRINCIPAL
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")

# Botão de refresh que limpa TUDO
if st.button("🔄 CLIQUE AQUI PARA SINCRONIZAR AGORA"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

st.markdown("---")

# Busca os dados
df_bruto = get_data_absolute_fresh()

if not df_bruto.empty:
    # Garante que as colunas numéricas sejam tratadas
    df_bruto['partidas'] = pd.to_numeric(df_bruto['partidas'], errors='coerce').fillna(1).replace(0, 1)
    
    # Debug opcional (descomente a linha abaixo se quiser ver se os números mudam no console)
    # st.write(f"Última atualização interna: {time.strftime('%H:%M:%S')}")

    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)

        if len(ranking_ordenado) >= 3:
            m1, m2, m3 = st.columns(3)
            m1.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
            m2.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
            m3.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

        st.markdown("---")
        ranking_final = processar_ranking_completo(ranking_ordenado, col_score)

        st.dataframe(
            ranking_final.style
            .apply(lambda row: ['background-color: #004d00; color: white' if row['Classificação'] == "Elite Zone" 
                               else 'background-color: #4d2600; color: white' if row['Classificação'] == "Cocô Zone" 
                               else '' for _ in row], axis=1)
            .background_gradient(cmap='YlGnBu', subset=[col_score])
            .format(precision=2),
            use_container_width=True,
            height=600,
            hide_index=True
        )

    # Cálculos com cópia profunda para evitar interferência
    with tab1:
        d = df_bruto.copy()
        f = (d['kr'] * 40) + (d['dano_medio'] / 8) + ((d['vitorias'] / d['partidas']) * 500)
        renderizar_ranking(d, 'Score_Pro', f)

    with tab2:
        d = df_bruto.copy()
        f = ((d['vitorias'] / d['partidas']) * 1000) + ((d['revives'] / d['partidas']) * 50) + ((d['assists'] / d['partidas']) * 35)
        renderizar_ranking(d, 'Score_Team', f)

    with tab3:
        d = df_bruto.copy()
        f = (d['kr'] * 50) + ((d['headshots'] / d['partidas']) * 60) + (d['dano_medio'] / 5)
        renderizar_ranking(d, 'Score_Elite', f)

else:
    st.error("Banco de dados retornou vazio. Verifique sua tabela 'ranking_squad'.")

st.markdown("---")
st.caption(f"Última leitura do banco às {time.strftime('%H:%M:%S')}")
