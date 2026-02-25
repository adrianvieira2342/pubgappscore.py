import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide", # Garante o uso de toda a largura da tela
    page_icon="🎮"
)

# CSS para forçar a tabela a ocupar 100% sem scroll e reduzir fontes
st.markdown("""
    <style>
    .stDataFrame {width: 100%;}
    [data-testid="stMetricValue"] {font-size: 1.8rem !important;}
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
        elif pos > (total - 2): # Ajustado para os 2 últimos como no seu SQL original
            novos_nicks.append(f"💩 {nick_limpo}"); zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}"); zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1, total + 1)
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    # Seleção estrita de colunas para evitar scroll lateral
    cols_base = ['Pos', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'revives', 'dano_medio', col_score]
    return df_ranking[cols_base]

# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")

df_bruto = get_data()

if not df_bruto.empty:
    # Conversão para Inteiros (Remove o .00)
    cols_int = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for c in cols_int: df_bruto[c] = pd.to_numeric(df_bruto[c], errors='coerce').fillna(0).astype(int)
    
    df_bruto['partidas_calc'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE", "📊 GERAL"])

    def highlight_zones(row):
        if "💀" in row['nick']: return ['background-color: #004d00; color: white'] * len(row)
        if "💩" in row['nick']: return ['background-color: #4d2600; color: white'] * len(row)
        return [''] * len(row)

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_final = processar_ranking_completo(df_local, col_score)

        t1, t2, t3 = st.columns(3)
        t1.metric("🥇 1º", ranking_final.iloc[0]['nick'], f"{ranking_final.iloc[0][col_score]} pts")
        t2.metric("🥈 2º", ranking_final.iloc[1]['nick'], f"{ranking_final.iloc[1][col_score]} pts")
        t3.metric("🥉 3º", ranking_final.iloc[2]['nick'], f"{ranking_final.iloc[2][col_score]} pts")

        # Dicionário de formatos compacto
        fmt = {col_score: "{:.2f}", 'kr': "{:.2f}", 'partidas': "{:d}", 'vitorias': "{:d}", 'kills': "{:d}", 'assists': "{:d}", 'revives': "{:d}", 'dano_medio': "{:d}"}

        st.dataframe(ranking_final.style.apply(highlight_zones, axis=1).format(fmt), use_container_width=True, hide_index=True)

    with tab1:
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', (df_bruto['kr']*40)+(df_bruto['dano_medio']/8)+((df_bruto['vitorias']/df_bruto['partidas_calc'])*500))
    with tab2:
        renderizar_ranking(df_bruto.copy(), 'Score_Team', ((df_bruto['vitorias']/df_bruto['partidas_calc'])*1000)+((df_bruto['revives']/df_bruto['partidas_calc'])*50)+((df_bruto['assists']/df_bruto['partidas_calc'])*35))
    with tab3:
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', (df_bruto['kr']*50)+((df_bruto['headshots']/df_bruto['partidas_calc'])*60)+(df_bruto['dano_medio']/5))
    with tab4:
        st.dataframe(processar_ranking_completo(df_bruto.copy(), 'kills').style.apply(highlight_zones, axis=1), use_container_width=True, hide_index=True)

    st.markdown("<div style='text-align: center; color: gray; font-size: 0.8rem;'>📊 By Adriano Vieira</div>", unsafe_allow_html=True)
