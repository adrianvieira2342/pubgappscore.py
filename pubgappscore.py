import streamlit as st
import pandas as pd
from datetime import datetime

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮",
    initial_sidebar_state="collapsed"
)

# =============================
# CSS TEMA ESCURO CUSTOM
# =============================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: white;
    }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
    }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 12px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        font-size: 16px;
        border: 1px solid #2ea043;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO
# =============================
def get_data():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        # IMPORTANTE: Forçamos o banco a entregar a data como texto puro (::text)
        # Isso evita que o Streamlit tente "ajustar" o fuso horário sozinho
        query = "SELECT *, atualizado_em::text as data_texto FROM ranking_squad"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    df_ranking = df_ranking.sort_values(by=col_score, ascending=False).reset_index(drop=True)
    
    novos_nicks = []
    zonas = []

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick']).replace("💀", "").replace("💩", "").replace("👤", "").strip()

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas
    
    return df_ranking

# =============================
# INTERFACE PRINCIPAL
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data()

if not df_bruto.empty:
    # --- LÓGICA DA BARRA DE SINCRONIZAÇÃO ---
    try:
        # Pegamos o valor máximo da coluna de texto que veio do banco
        # Isso reflete o exato momento em que o GitHub Actions salvou os dados
        horario_banco = df_bruto['data_texto'].max()
        
        # Formatamos para o padrão brasileiro (DD/MM/AAAA HH:MM:SS)
        dt_obj = datetime.strptime(horario_banco[:19], '%Y-%m-%d %H:%M:%S')
        data_exibicao = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
    except:
        data_exibicao = "Horário indisponível"

    # Exibe a barra verde com o horário REAL do banco
    st.markdown(f"""
        <div class="sync-bar">
            ● Última Atualização do Banco: {data_exibicao}
        </div>
    """, unsafe_allow_html=True)

    # Tratamento de dados numéricos
    cols_inteiras = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_inteiras:
        df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0).astype(int)
    
    df_bruto = df_bruto[df_bruto['partidas'] > 0].copy()
    df_bruto['partidas_calc'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_final = processar_ranking_completo(df_local, col_score)
        
        # Métricas de topo
        t1, t2, t3 = st.columns(3)
        with t1: st.metric("🥇 1º Lugar", ranking_final.iloc[0]['nick'], f"{ranking_final.iloc[0][col_score]} pts")
        with t2: st.metric("🥈 2º Lugar", ranking_final.iloc[1]['nick'], f"{ranking_final.iloc[1][col_score]} pts")
        with t3: st.metric("🥉 3º Lugar", ranking_final.iloc[2]['nick'], f"{ranking_final.iloc[2][col_score]} pts")

        st.dataframe(
            ranking_final[['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', col_score]],
            use_container_width=True,
            hide_index=True
        )

    with tab1:
        f_pro = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas_calc']) * 500)
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)
    
    # ... (Tabs 2 e 3 seguem a mesma lógica)

    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)
else:
    st.warning("Aguardando conexão com o banco...")
