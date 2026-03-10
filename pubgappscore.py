import streamlit as st
import pandas as pd
import subprocess
import time

# =============================
# CONFIGURAÇÃO DA PÁGINA (ORIGINAL)
# =============================

st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# =============================
# ATUALIZAÇÃO AUTOMÁTICA DO BANCO
# =============================

@st.cache_data(ttl=60)
def atualizar_banco():
    try:
        subprocess.run(["python", "pubg_import.py"], check=True)
    except Exception as e:
        st.warning(f"Erro ao atualizar ranking: {e}")

atualizar_banco()

# =============================
# CSS ORIGINAL
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
[data-testid="stMetricLabel"] * {
    font-size: 40px !important;
}
[data-testid="stMetricValue"] {
    font-size: 38px !important;
}
div[data-testid="stTabs"] button {
    font-size: 16px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO BANCO
# =============================

def get_data(table):

    try:

        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )

        df = conn.query(f"SELECT * FROM {table}", ttl=0)

        return df

    except Exception as e:

        st.error(f"Erro banco: {e}")
        return pd.DataFrame()

# =============================
# PROCESSAMENTO RANKING
# =============================

def processar_ranking(df, col_score):

    total = len(df)

    df = df.sort_values(col_score, ascending=False).reset_index(drop=True)

    novos = []
    zonas = []

    for i,row in df.iterrows():

        pos = i+1
        nick = row["nick"]

        if pos <=3:
            novos.append(f"💀 {nick}")
            zonas.append("Elite Zone")

        elif pos > total-3:
            novos.append(f"💩 {nick}")
            zonas.append("Cocô Zone")

        else:
            novos.append(f"👤 {nick}")
            zonas.append("Medíocre Zone")

    df["Pos"] = range(1,total+1)
    df["nick"] = novos
    df["Classificação"] = zonas

    return df

# =============================
# TÍTULO
# =============================

st.markdown(
"<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>",
unsafe_allow_html=True
)

# =============================
# BUSCAR DADOS
# =============================

df_bruto = get_data("v_ranking_squad_completo")
df_bots_raw = get_data("ranking_bot")

# =============================
# ÚLTIMA ATUALIZAÇÃO
# =============================

if "ultima_atualizacao" in df_bruto.columns:

    try:

        dt = pd.to_datetime(df_bruto["ultima_atualizacao"].iloc[0])

        st.markdown(
        f"<p style='color:#888;'>📅 Última atualização do banco: <b>{dt.strftime('%d/%m/%Y %H:%M')}</b></p>",
        unsafe_allow_html=True)

    except:
        pass

st.markdown("---")

# =============================
# AJUSTE CASUAL
# =============================

if not df_bots_raw.empty:

    cols = ["partidas","vitorias","kills","assists","headshots","revives"]

    for _,row in df_bots_raw.iterrows():

        nick = row["nick"]

        if nick in df_bruto["nick"].values:

            for col in cols:

                total = df_bruto.loc[df_bruto.nick==nick,col].values[0]
                casual = abs(row[col])

                df_bruto.loc[df_bruto.nick==nick,col] = max(0,total-casual)

            partidas = max(1,df_bruto.loc[df_bruto.nick==nick,"partidas"].values[0])
            kills = df_bruto.loc[df_bruto.nick==nick,"kills"].values[0]

            df_bruto.loc[df_bruto.nick==nick,"kr"] = kills/partidas

# =============================
# FORMATAR NUMEROS
# =============================

df_bruto["kr"] = df_bruto["kr"].astype(float).round(2)
df_bruto["kill_dist_max"] = df_bruto["kill_dist_max"].astype(float).round(2)

# =============================
# TABS
# =============================

tab1,tab2,tab3,tab4 = st.tabs([
"🔥 PRO Player",
"🤝 TEAM Player",
"🎯 Atirador de Elite",
"🤖 Bot Detector"
])

df_valid = df_bruto[df_bruto["partidas"]>0].copy()
df_valid["partidas_calc"] = df_valid["partidas"].replace(0,1)

# =============================
# FUNÇÃO RENDER
# =============================

def renderizar_ranking(df,col_score,formula,descricao):

    if formula is not None:
        df[col_score] = formula.round(2)

    ranking = processar_ranking(df,col_score)

    c1,c2,c3 = st.columns(3)

    if len(ranking)>0:
        c1.metric("🥇 1º Lugar",ranking.iloc[0]["nick"],f'{ranking.iloc[0][col_score]:.2f}')

    if len(ranking)>1:
        c2.metric("🥈 2º Lugar",ranking.iloc[1]["nick"],f'{ranking.iloc[1][col_score]:.2f}')

    if len(ranking)>2:
        c3.metric("🥉 3º Lugar",ranking.iloc[2]["nick"],f'{ranking.iloc[2][col_score]:.2f}')

    st.markdown(
    f"<div style='background:#161b22;padding:12px;border-radius:8px;border-left:5px solid #0078ff;margin-bottom:20px;'>💡 {descricao}</div>",
    unsafe_allow_html=True
    )

    ranking["kr"] = ranking["kr"].astype(float).round(2)
    ranking["kill_dist_max"] = ranking["kill_dist_max"].astype(float).round(2)
    ranking[col_score] = ranking[col_score].astype(float).round(2)

    st.dataframe(
        ranking.style
        .background_gradient(
            cmap="YlGnBu" if col_score!="score" else "RdYlGn",
            subset=[col_score]
        ),
        use_container_width=True,
        height=(len(ranking)*35)+80,
        hide_index=True,
        column_config={
            "nick":"Nickname",
            "partidas":"Partidas",
            "kr":"K/R",
            "vitorias":"Vitórias",
            "kills":"Kills",
            "assists":"Assists",
            "headshots":"Headshots",
            "revives":"Revives",
            "kill_dist_max":"Kill Dist Máx",
            "dano_medio":"Dano Médio",
            "Score_Pro":"Score Pro",
            "Score_Team":"Score Team",
            "Score_Elite":"Score Elite",
            "score":"Penalidade"
        }
    )

# =============================
# PRO
# =============================

with tab1:

    f = (
        df_valid["kr"]*40
        + df_valid["dano_medio"]/8
        + (df_valid["vitorias"]/df_valid["partidas_calc"])*500
    )

    renderizar_ranking(
        df_valid.copy(),
        "Score_Pro",
        f,
        "Fórmula PRO: Valoriza equilíbrio entre sobrevivência e agressividade. Foca em K/R alto, dano consistente e taxa de vitória"
    )

# =============================
# TEAM
# =============================

with tab2:

    f = (
        (df_valid["vitorias"]/df_valid["partidas_calc"])*1000
        + (df_valid["revives"]/df_valid["partidas_calc"])*50
        + (df_valid["assists"]/df_valid["partidas_calc"])*35
    )

    renderizar_ranking(
        df_valid.copy(),
        "Score_Team",
        f,
        "Fórmula TEAM: Foco total no jogo coletivo. Pontua mais quem revive aliados, dá assistências e garante a vitória."
    )

# =============================
# ELITE
# =============================

with tab3:

    f = (
        df_valid["kr"]*50
        + (df_valid["headshots"]/df_valid["partidas_calc"])*60
        + df_valid["dano_medio"]/5
    )

    renderizar_ranking(
        df_valid.copy(),
        "Score_Elite",
        f,
        "Fórmula ELITE: Prioriza K/R, precisão de Headshots e volume de dano."
    )

# =============================
# BOTS
# =============================

with tab4:

    if not df_bots_raw.empty:

        df_bots = df_bots_raw[df_bots_raw["partidas"]>0]

        if len(df_bots)>0:

            renderizar_ranking(
                df_bots,
                "score",
                None,
                "Anti-Casual: Jogadores penalizados por matar bots em partidas no modo casual."
            )

        else:
            st.info("Nenhuma penalidade registrada.")

# =============================
# FOOTER
# =============================

st.markdown("---")

st.markdown(
"<div style='text-align:center;color:gray;padding:20px;'>📊 <b>By Adriano Vieira</b></div>",
unsafe_allow_html=True
)
