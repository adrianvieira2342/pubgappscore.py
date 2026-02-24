import streamlit as st
import pandas as pd
import psycopg2

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Ranking Squad",
    layout="wide",
    page_icon="🏆"
)

# =============================
# FUNÇÃO PARA CARREGAR RANKING
# =============================
@st.cache_data(ttl=60)
def carregar_ranking():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])

        query = """
        SELECT 
            nick,
            partidas,
            kr,
            vitorias,
            kills,
            dano_medio,
            assists,
            headshots,
            revives,
            kill_dist_max,
            score,
            atualizado_em
        FROM ranking_squad
        ORDER BY score DESC NULLS LAST
        """

        df = pd.read_sql(query, conn)
        conn.close()

        # Substituir NULL por 0 para evitar erro nos cálculos
        df.fillna(0, inplace=True)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


# =============================
# CÁLCULOS DE SCORE
# =============================

def score_pro_player(df):
    return (
        df["vitorias"] * 5 +
        df["kills"] * 3 +
        df["dano_medio"] * 0.05 +
        df["assists"] * 1.5
    )

def score_team_player(df):
    return (
        df["vitorias"] * 5 +
        df["revives"] * 3 +
        df["assists"] * 2 +
        df["kills"] * 1.5 +
        df["dano_medio"] * 0.03
    )

def score_atirador_elite(df):
    return (
        df["kr"] * 10 +
        df["headshots"] * 2 +
        df["dano_medio"] * 0.07 +
        df["kill_dist_max"] * 0.02 +
        df["vitorias"] * 2
    )


# =============================
# INTERFACE
# =============================

st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas atualizadas automaticamente via API Oficial.")

if st.button("🔄 Recarregar Tabela"):
    st.cache_data.clear()

df_ranking = carregar_ranking()

if df_ranking is not None and not df_ranking.empty:

    # =============================
    # CRIANDO ABAS
    # =============================
    tab1, tab2, tab3 = st.tabs([
        "🏆 Pro Player",
        "🤝 Team Player",
        "🎯 Atirador de Elite"
    ])

    # ==========================================================
    # ABA 1 - PRO PLAYER (Equilíbrio Técnico)
    # ==========================================================
    with tab1:

        st.subheader("🏆 Ranking - Pro Player")

        df1 = df_ranking.copy()
        df1["Score Pro Player"] = score_pro_player(df1)
        df1 = df1.sort_values("Score Pro Player", ascending=False)

        # Top 3
        cols = st.columns(3)
        for i in range(min(3, len(df1))):
            cols[i].metric(
                label=f"{i+1}º Lugar",
                value=df1.iloc[i]["nick"],
                delta=f"{df1.iloc[i]['Score Pro Player']:.2f}"
            )

        st.divider()

        st.dataframe(
            df1,
            column_config={
                "Score Pro Player": st.column_config.ProgressColumn(
                    "Score Pro Player",
                    min_value=0,
                    max_value=float(df1["Score Pro Player"].max())
                )
            },
            hide_index=True,
            use_container_width=True
        )

    # ==========================================================
    # ABA 2 - TEAM PLAYER (Foco no Coletivo)
    # ==========================================================
    with tab2:

        st.subheader("🤝 Ranking - Team Player")

        df2 = df_ranking.copy()
        df2["Score Team Player"] = score_team_player(df2)
        df2 = df2.sort_values("Score Team Player", ascending=False)

        cols = st.columns(3)
        for i in range(min(3, len(df2))):
            cols[i].metric(
                label=f"{i+1}º Lugar",
                value=df2.iloc[i]["nick"],
                delta=f"{df2.iloc[i]['Score Team Player']:.2f}"
            )

        st.divider()

        st.dataframe(
            df2,
            column_config={
                "Score Team Player": st.column_config.ProgressColumn(
                    "Score Team Player",
                    min_value=0,
                    max_value=float(df2["Score Team Player"].max())
                )
            },
            hide_index=True,
            use_container_width=True
        )

    # ==========================================================
    # ABA 3 - ATIRADOR DE ELITE (Performance Técnica)
    # ==========================================================
    with tab3:

        st.subheader("🎯 Ranking - Atirador de Elite")

        df3 = df_ranking.copy()
        df3["Score Atirador Elite"] = score_atirador_elite(df3)
        df3 = df3.sort_values("Score Atirador Elite", ascending=False)

        cols = st.columns(3)
        for i in range(min(3, len(df3))):
            cols[i].metric(
                label=f"{i+1}º Lugar",
                value=df3.iloc[i]["nick"],
                delta=f"{df3.iloc[i]['Score Atirador Elite']:.2f}"
            )

        st.divider()

        st.dataframe(
            df3,
            column_config={
                "Score Atirador Elite": st.column_config.ProgressColumn(
                    "Score Atirador Elite",
                    min_value=0,
                    max_value=float(df3["Score Atirador Elite"].max())
                )
            },
            hide_index=True,
            use_container_width=True
        )

else:
    st.warning("Nenhum dado encontrado na tabela ranking_squad.")
