import streamlit as st
import pandas as pd
import subprocess
import sys

# =============================
# ATUALIZAÇÃO AUTOMÁTICA DO BANCO
# =============================
try:
    subprocess.run([sys.executable, "pubg_import.py"], check=True)
except Exception as e:
    st.warning(f"Erro ao atualizar ranking: {e}")

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
# CSS TEMA ESCURO CUSTOM (ORIGINAL)
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
# CONEXÃO COM BANCO
# =============================
def get_data(table_name="v_ranking_squad_completo"):
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        query = f"SELECT * FROM {table_name}"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# INTERFACE
# =============================
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data("v_ranking_squad_completo")
df_bots_raw = get_data("ranking_bot")

# =============================
# CORREÇÃO DE TIPOS NUMÉRICOS
# =============================
cols_numeric = [
    "partidas","kr","vitorias","kills",
    "assists","headshots","revives",
    "kill_dist_max","dano_medio"
]

for col in cols_numeric:
    if col in df_bruto.columns:
        df_bruto[col] = pd.to_numeric(df_bruto[col], errors="coerce").fillna(0)

if not df_bots_raw.empty:
    for col in cols_numeric:
        if col in df_bots_raw.columns:
            df_bots_raw[col] = pd.to_numeric(df_bots_raw[col], errors="coerce").fillna(0)

# =============================
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):

    total = len(df_ranking)
    novos_nicks = []
    zonas = []

    is_bot_ranking = col_score == 'score'
    df_ranking = df_ranking.sort_values(by=col_score, ascending=is_bot_ranking).reset_index(drop=True)

    for i, row in df_ranking.iterrows():

        pos = i + 1
        nick_limpo = str(row['nick'])

        for emoji in ["💀","💩","👤"]:
            nick_limpo = nick_limpo.replace(emoji,"").strip()

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")

        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")

        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = range(1,total+1)
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    cols_base = [
        'Pos','Classificação','nick',
        'partidas','kr','vitorias',
        'kills','assists','headshots',
        'revives','kill_dist_max','dano_medio'
    ]

    if col_score not in cols_base:
        cols_base.append(col_score)

    return df_ranking[cols_base]

# =============================
# UI FUNÇÕES
# =============================
def highlight_zones(row):

    if row['Classificação']=="Elite Zone":
        return ['background-color:#003300;color:white;font-weight:bold']*len(row)

    if row['Classificação']=="Cocô Zone":
        return ['background-color:#4d0000;color:white;font-weight:bold']*len(row)

    return ['']*len(row)

def renderizar_ranking(df_local,col_score,formula,explicacao):

    if formula is not None:
        df_local[col_score]=formula.round(2)

    ranking_final=processar_ranking_completo(df_local,col_score)

    # TOP 3 SEGURO
    top1,top2,top3=st.columns(3)

    with top1:
        if len(ranking_final)>=1:
            st.metric("🥇 1º Lugar",
                ranking_final.iloc[0]['nick'],
                f"{ranking_final.iloc[0][col_score]:.2f} pts")
        else:
            st.metric("🥇 1º Lugar","-","-")

    with top2:
        if len(ranking_final)>=2:
            st.metric("🥈 2º Lugar",
                ranking_final.iloc[1]['nick'],
                f"{ranking_final.iloc[1][col_score]:.2f} pts")
        else:
            st.metric("🥈 2º Lugar","-","-")

    with top3:
        if len(ranking_final)>=3:
            st.metric("🥉 3º Lugar",
                ranking_final.iloc[2]['nick'],
                f"{ranking_final.iloc[2][col_score]:.2f} pts")
        else:
            st.metric("🥉 3º Lugar","-","-")

    st.markdown(
    f"<div style='background-color:#161b22;padding:12px;border-radius:8px;border-left:5px solid #0078ff;margin-bottom:20px;text-align:left;'>💡 {explicacao}</div>",
    unsafe_allow_html=True)

    st.dataframe(
        ranking_final.style
        .background_gradient(
            cmap='YlGnBu' if col_score!='score' else 'RdYlGn',
            subset=[col_score])
        .apply(highlight_zones,axis=1),
        use_container_width=True,
        height=(len(ranking_final)*35)+80,
        hide_index=True
    )

# =============================
# TABS
# =============================
tab1,tab2,tab3,tab4=st.tabs([
"🔥 PRO Player",
"🤝 TEAM Player",
"🎯 Atirador de Elite",
"🤖 Bot Detector"
])

df_valid=df_bruto[df_bruto['partidas']>0].copy()
df_valid['partidas_calc']=df_valid['partidas'].replace(0,1)

# PRO
with tab1:

    f_pro=(df_valid['kr']*40)+(df_valid['dano_medio']/8)+((df_valid['vitorias']/df_valid['partidas_calc'])*500)

    renderizar_ranking(
        df_valid.copy(),
        'Score_Pro',
        f_pro,
        "Fórmula PRO: Valoriza equilíbrio entre sobrevivência e agressividade. Foca em K/R alto, dano consistente e taxa de vitória"
    )

# TEAM
with tab2:

    f_team=((df_valid['vitorias']/df_valid['partidas_calc'])*1000)+((df_valid['revives']/df_valid['partidas_calc'])*50)+((df_valid['assists']/df_valid['partidas_calc'])*35)

    renderizar_ranking(
        df_valid.copy(),
        'Score_Team',
        f_team,
        "Fórmula TEAM: Foco total no jogo coletivo. Pontua mais quem revive aliados, dá assistências e garante a vitória."
    )

# ELITE
with tab3:

    f_elite=(df_valid['kr']*50)+((df_valid['headshots']/df_valid['partidas_calc'])*60)+(df_valid['dano_medio']/5)

    renderizar_ranking(
        df_valid.copy(),
        'Score_Elite',
        f_elite,
        "Fórmula ELITE: Prioriza K/R, precisão de Headshots e volume de dano."
    )

# BOT
with tab4:

    if not df_bots_raw.empty:

        df_bots=df_bots_raw[df_bots_raw['partidas']>0].copy()

        if not df_bots.empty:

            renderizar_ranking(
                df_bots,
                'score',
                None,
                "Anti-Casual: Jogadores penalizados por matar bots em partidas no modo casual."
            )

        else:
            st.info("Nenhuma penalidade registrada.")

st.markdown("---")

st.markdown(
"<div style='text-align:center;color:gray;padding:20px;'>📊 <b>By Adriano Vieira</b></div>",
unsafe_allow_html=True)
