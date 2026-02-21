import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# =============================
# FUNÇÃO DE BUSCA DE DADOS (SEM CACHE)
# =============================
def get_data_fresh():
    """
    Usa SQLAlchemy direto para garantir que a conexão seja aberta e 
    fechada a cada chamada, forçando a leitura dos dados mais recentes.
    """
    try:
        # Pega a URL dos secrets
        db_url = st.secrets["DATABASE_URL"]
        
        # Cria o engine sem pool de conexões persistentes para evitar dados antigos
        engine = create_engine(db_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            query = text("SELECT * FROM ranking_squad")
            df = pd.read_sql(query, conn)
            
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados atualizados: {e}")
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

        # Remove emojis para evitar duplicação visual
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
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown("# 🎮 Ranking Squad - Season 40")
with col2:
    if st.button("🔄 Forçar Atualização"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# Buscando dados SEMPRE que a página carrega
df_bruto = get_data_fresh()

if not df_bruto.empty:
    # Garante que 'partidas' seja tratado para evitar divisão por zero
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        
        # Ordenar antes de processar zonas e emojis
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)

        # Metrics Top 3
        if len(ranking_ordenado) >= 3:
            m1, m2, m3 = st.columns(3)
            m1.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
            m2.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
            m3.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

        st.markdown("---")

        ranking_final = processar_ranking_completo(ranking_ordenado, col_score)

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone":
                return ['background-color: #004d00; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone":
                return ['background-color: #4d2600; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            ranking_final.style
            .apply(highlight_zones, axis=1)
            .background_gradient(cmap='YlGnBu', subset=[col_score])
            .format(precision=2),
            use_container_width=True,
            height=600,
            hide_index=True
        )

    with tab1:
        f_pro = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas']) * 500)
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

    with tab2:
        f_team = ((df_bruto['vitorias'] / df_bruto['partidas']) * 1000) + ((df_bruto['revives'] / df_bruto['partidas']) * 50) + ((df_bruto['assists'] / df_bruto['partidas']) * 35)
        renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

    with tab3:
        f_elite = (df_bruto['kr'] * 50) + ((df_bruto['headshots'] / df_bruto['partidas']) * 60) + (df_bruto['dano_medio'] / 5)
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

else:
    st.warning("Nenhum dado encontrado ou erro na conexão. Verifique o Supabase.")

st.markdown("---")
st.caption("📊 Sistema de Ranking Automático - Desenvolvido por Adriano Vieira")
