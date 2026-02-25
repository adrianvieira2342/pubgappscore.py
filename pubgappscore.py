import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# CSS para forçar largura total e remover espaços desnecessários
st.markdown("""
    <style>
    .stDataFrame {width: 100%;}
    [data-testid="stMetricValue"] {font-size: 1.6rem !important;}
    /* Remove o limite de altura do container interno da tabela */
    [data-testid="stTable"] {overflow: visible !important;}
    </style>
    """, unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO (SUPABASE)
# =============================
def get_data():
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        query = "SELECT * FROM ranking_squad"
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
    novos_nicks, zonas = [], []
    df_ranking = df_ranking.sort_values(by=col_score, ascending=False).reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for emoji in ["💀", "💩", "👤"]: nick_limpo = nick_limpo.replace(emoji, "").strip()

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}"); zonas.append("Elite Zone")
        elif pos > (total - 2):
            novos_nicks.append(f"💩 {nick_limpo}"); zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}"); zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'] = novos_nicks
    
    # Colunas equalizadas para evitar scroll lateral
    cols_fixas = ['Pos', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'revives', 'dano_medio']
    if col_score not in cols_fixas:
        cols_fixas.append(col_score)
        
    return df_ranking[cols_fixas]

# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")

df_bruto = get_data()

if not df_bruto.empty:
    # Tratamento de inteiros (remove .00)
    cols_int = ['partidas', 'vitorias', 'kills', 'assists', 'revives', 'dano_medio']
    for c in cols_int: 
        df_bruto[c] = pd.to_numeric(df_bruto[c], errors='coerce').fillna(0).astype(int)
    
    df_bruto['partidas_calc'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE", "📊 GERAL"])

    def highlight_zones(row):
        if "💀" in str(row['nick']): return ['background-color: #004d00; color: white'] * len(row)
        if "💩" in str(row['nick']): return ['background-color: #4d2600; color: white'] * len(row)
        return [''] * len(row)

    base_format = {
        'kr': "{:.2f}", 'partidas': "{:d}", 'vitorias': "{:d}", 
        'kills': "{:d}", 'assists': "{:d}", 'revives': "{:d}", 'dano_medio': "{:d}"
    }

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_final = processar_ranking_completo(df_local, col_score)

        t1, t2, t3 = st.columns(3)
        t1.metric("🥇 1º", ranking_final.iloc[0]['nick'], f"{ranking_final.iloc[0][col_score]} pts")
        t2.metric("🥈 2º", ranking_final.iloc[1]['nick'], f"{ranking_final.iloc[1][col_score]} pts")
        t3.metric("🥉 3º", ranking_final.iloc[2]['nick'], f"{ranking_final.iloc[2][col_score]} pts")

        fmt = base_format.copy()
        fmt[col_score] = "{:.2f}"

        # height=None faz com que a tabela se expanda para mostrar todas as linhas
        st.dataframe(
            ranking_final.style.apply(highlight_zones, axis=1).format(fmt), 
            use_container_width=True, 
            hide_index=True,
            height=None 
        )

    with tab1:
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', (df_bruto['kr']*40)+(df_bruto['dano_medio']/8)+((df_bruto['vitorias']/df_bruto['partidas_calc'])*500))
    with tab2:
        renderizar_ranking(df_bruto.copy(), 'Score_Team', ((df_bruto['vitorias']/df_bruto['partidas_calc'])*1000)+((df_bruto['revives']/df_bruto['partidas_calc'])*50)+((df_bruto['assists']/df_bruto['partidas_calc'])*35))
    with tab3:
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', (df_bruto['kr']*50)+((df_bruto['headshots'].fillna(0)/df_bruto['partidas_calc'])*60)+(df_bruto['dano_medio']/5))
    with tab4:
        st.subheader("Métricas Gerais")
        ranking_geral = processar_ranking_completo(df_bruto.copy(), 'kills')
        st.dataframe(
            ranking_geral.style.apply(highlight_zones, axis=1).format(base_format), 
            use_container_width=True, 
            hide_index=True,
            height=None
        )

    st.markdown("<div style='text-align: center; color: gray; font-size: 0.8rem; padding: 40px;'>📊 By Adriano Vieira</div>", unsafe_allow_html=True)
else:
    st.warning("Aguardando dados...")
