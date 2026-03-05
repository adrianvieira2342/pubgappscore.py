import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# =============================
# CSS TEMA ESCURO CUSTOM
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #161b22; padding: 15px;
        border-radius: 12px; border: 1px solid #30363d; text-align: center;
    }
    [data-testid="stMetricLabel"] * { font-size: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 38px !important; }
    div[data-testid="stTabs"] button { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO
# =============================
def get_data(query):
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        df = conn.query(query, ttl=0) 
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score, reverse=False):
    total = len(df_ranking)
    # Para o ranking de bots, queremos os MAIS penalizados (menor score) no topo? 
    # Ou os menos penalizados? Geralmente penalidade o topo é o "pior".
    # Se reverse=True, ele ordena do menor para o maior (mais negativos primeiro).
    df_ranking = df_ranking.sort_values(by=col_score, ascending=reverse).reset_index(drop=True)
    
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
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

# Tabs agora com a 4ª opção
tab1, tab2, tab3, tab4 = st.tabs([
    "🔥 PRO Player", 
    "🤝 TEAM Player", 
    "🎯 Atirador de Elite",
    "🤖 Anti-Casual (Bots)"
])

# Lógica compartilhada de renderização
def renderizar_ui(df_local, col_score, explicacao, reverse=False):
    ranking_final = processar_ranking_completo(df_local, col_score, reverse=reverse)
    
    t1, t2, t3 = st.columns(3)
    with t1: st.metric("🥇 1º Lugar", ranking_final.iloc[0]['nick'] if len(ranking_final) > 0 else "-", f"{ranking_final.iloc[0][col_score]:.2f} pts")
    with t2: st.metric("🥈 2º Lugar", ranking_final.iloc[1]['nick'] if len(ranking_final) > 1 else "-", f"{ranking_final.iloc[1][col_score]:.2f} pts")
    with t3: st.metric("🥉 3º Lugar", ranking_final.iloc[2]['nick'] if len(ranking_final) > 2 else "-", f"{ranking_final.iloc[2][col_score]:.2f} pts")

    st.markdown(f"<div style='background-color: #161b22; padding: 12px; border-radius: 8px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;'>💡 {explicacao}</div>", unsafe_allow_html=True)

    st.dataframe(
        ranking_final.style.background_gradient(cmap='RdYlGn' if reverse else 'YlGnBu', subset=[col_score]),
        use_container_width=True,
        hide_index=True,
        column_config={"score": "Penalidade Total", "kr": "K/R Bot", "kill_dist_max": "Dist Máx Bot"}
    )

# --- CARREGAMENTO DOS DADOS ---
df_original = get_data("SELECT * FROM v_ranking_squad_completo")
df_bots = get_data("SELECT * FROM ranking_bot")

with tab1:
    if not df_original.empty:
        df = df_original[df_original['partidas'] > 0].copy()
        f = (df['kr'] * 40) + (df['dano_medio'] / 8) + ((df['vitorias'] / df['partidas'].replace(0,1)) * 500)
        df['Score_Pro'] = f.round(2)
        renderizar_ui(df, 'Score_Pro', "Fórmula PRO: Valoriza o equilíbrio entre sobrevivência e agressividade.")

with tab2:
    if not df_original.empty:
        df = df_original[df_original['partidas'] > 0].copy()
        f = ((df['vitorias'] / df['partidas'].replace(0,1)) * 1000) + ((df['revives'] / df['partidas'].replace(0,1)) * 50)
        df['Score_Team'] = f.round(2)
        renderizar_ui(df, 'Score_Team', "Fórmula TEAM: Foco total no jogo coletivo e assistências.")

with tab3:
    if not df_original.empty:
        df = df_original[df_original['partidas'] > 0].copy()
        f = (df['kr'] * 50) + ((df['headshots'] / df['partidas'].replace(0,1)) * 60) + (df['dano_medio'] / 5)
        df['Score_Elite'] = f.round(2)
        renderizar_ui(df, 'Score_Elite', "Fórmula ELITE: Prioriza K/R, Headshots e volume de dano.")

with tab4:
    if not df_bots.empty:
        # No ranking de BOTS, queremos mostrar quem tem mais "score negativo" (penalidade)
        # Por isso usamos reverse=True para o menor valor (ex: -100) aparecer no topo
        renderizar_ui(df_bots, 'score', "Mural da Vergonha: Ranking de penalidades acumuladas em partidas Casuais ou com excesso de Bots. Score negativo reduz seu prestígio.", reverse=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)
