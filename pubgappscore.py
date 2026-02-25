import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
# AUTO REFRESH A CADA 30s
# =============================
st.markdown(
    """
    <meta http-equiv="refresh" content="30">
    """,
    unsafe_allow_html=True
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
    .status-box {
        text-align:center;
        background-color:#161b22;
        padding:12px;
        border-radius:12px;
        border:1px solid #30363d;
        margin-bottom:15px;
        font-size:16px;
    }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
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
def get_data():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        query = "SELECT * FROM ranking_squad"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# HEADER
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)
st.markdown("---")

df_bruto = get_data()

# =============================
# STATUS PROFISSIONAL
# =============================
if not df_bruto.empty and "updated_at" in df_bruto.columns:

    df_bruto["updated_at"] = pd.to_datetime(df_bruto["updated_at"], errors="coerce")
    ultima = df_bruto["updated_at"].max()

    if pd.notnull(ultima):

        agora = datetime.utcnow()
        proxima_execucao = ultima + timedelta(minutes=10)
        tempo_restante = proxima_execucao - agora

        if tempo_restante.total_seconds() > 0:
            minutos = int(tempo_restante.total_seconds() // 60)
            segundos = int(tempo_restante.total_seconds() % 60)

            if minutos <= 2:
                status_cor = "#665c00"
                status_icon = "🟡"
                status_texto = "Atualização iminente"
            else:
                status_cor = "#003300"
                status_icon = "🟢"
                status_texto = "Atualizado"

            st.markdown(
                f"""
                <div class="status-box" style="border:1px solid {status_cor};">
                    {status_icon} <b>{status_texto}</b><br>
                    ⏳ Próxima atualização em: <b>{minutos:02d}:{segundos:02d}</b><br>
                    🕒 Última atualização: {ultima.strftime("%d/%m/%Y %H:%M:%S")} UTC
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="status-box" style="border:1px solid #4d0000;">
                    🔴 <b>Atualização atrasada</b><br>
                    O GitHub Actions ainda não executou.<br>
                    🕒 Última atualização: {ultima.strftime("%d/%m/%Y %H:%M:%S")} UTC
                </div>
                """,
                unsafe_allow_html=True
            )

st.markdown("---")

# =============================
# PROCESSAMENTO
# =============================
if not df_bruto.empty:

    cols_inteiras = ['partidas', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'dano_medio']
    for col in cols_inteiras:
        df_bruto[col] = pd.to_numeric(df_bruto[col], errors='coerce').fillna(0).astype(int)

    df_bruto = df_bruto[df_bruto['partidas'] > 0].copy()

    if df_bruto.empty:
        st.info("Nenhum jogador possui partidas registradas nesta temporada.")
    else:
        df_bruto['partidas_calc'] = df_bruto['partidas'].replace(0, 1)

        tab1, tab2, tab3 = st.tabs([
            "🔥 PRO (Equilibrado)", 
            "🤝 TEAM (Suporte)", 
            "🎯 ELITE (Skill)"
        ])

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone":
                return ['background-color: #003300; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone":
                return ['background-color: #4d0000; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        def processar(df_ranking, col_score):
            total = len(df_ranking)
            df_ranking = df_ranking.sort_values(by=col_score, ascending=False).reset_index(drop=True)

            zonas = []
            nicks = []

            for i, row in df_ranking.iterrows():
                pos = i + 1
                nick = str(row['nick']).replace("💀","").replace("💩","").replace("👤","").strip()

                if pos <= 3:
                    zonas.append("Elite Zone")
                    nicks.append(f"💀 {nick}")
                elif pos > total - 3:
                    zonas.append("Cocô Zone")
                    nicks.append(f"💩 {nick}")
                else:
                    zonas.append("Medíocre Zone")
                    nicks.append(f"👤 {nick}")

            df_ranking['Pos'] = range(1, total+1)
            df_ranking['nick'] = nicks
            df_ranking['Classificação'] = zonas

            return df_ranking

        def renderizar(df_local, col_score, formula):
            df_local[col_score] = formula.round(2)
            ranking = processar(df_local, col_score)

            top1, top2, top3 = st.columns(3)

            for i, col in enumerate([top1, top2, top3]):
                with col:
                    if len(ranking) > i:
                        st.metric(
                            f"{['🥇','🥈','🥉'][i]} {i+1}º Lugar",
                            ranking.iloc[i]['nick'],
                            f"{ranking.iloc[i][col_score]} pts"
                        )

            st.dataframe(
                ranking.style
                .background_gradient(cmap='YlGnBu', subset=[col_score])
                .apply(highlight_zones, axis=1),
                use_container_width=True,
                hide_index=True
            )

        with tab1:
            f_pro = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas_calc']) * 500)
            renderizar(df_bruto.copy(), 'Score_Pro', f_pro)

        with tab2:
            f_team = ((df_bruto['vitorias'] / df_bruto['partidas_calc']) * 1000) + ((df_bruto['revives'] / df_bruto['partidas_calc']) * 50) + ((df_bruto['assists'] / df_bruto['partidas_calc']) * 35)
            renderizar(df_bruto.copy(), 'Score_Team', f_team)

        with tab3:
            f_elite = (df_bruto['kr'] * 50) + ((df_bruto['headshots'] / df_bruto['partidas_calc']) * 60) + (df_bruto['dano_medio'] / 5)
            renderizar(df_bruto.copy(), 'Score_Elite', f_elite)

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)

else:
    st.warning("Conectado ao banco. Aguardando dados...")
