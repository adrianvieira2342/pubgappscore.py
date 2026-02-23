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

# =============================
# CONEXÃO COM BANCO (SUPABASE)
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
# PROCESSAMENTO DO RANKING
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    posicoes = []

    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])

        for emoji in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

        posicoes.append(pos)

        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = posicoes
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
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

df_bruto = get_data()

if not df_bruto.empty:

    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs([
        "🔥 PRO (Equilibrado)",
        "🤝 TEAM (Suporte)",
        "🎯 ELITE (Skill)"
    ])

    def renderizar_ranking(df_local, col_score, formula):

        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(
            col_score,
            ascending=False
        ).reset_index(drop=True)

        if len(ranking_ordenado) >= 3:
            top1, top2, top3 = st.columns(3)

            with top1:
                st.metric(
                    "🥇 1º Lugar",
                    ranking_ordenado.iloc[0]['nick'],
                    f"{ranking_ordenado.iloc[0][col_score]} pts"
                )

            with top2:
                st.metric(
                    "🥈 2º Lugar",
                    ranking_ordenado.iloc[1]['nick'],
                    f"{ranking_ordenado.iloc[1][col_score]} pts"
                )

            with top3:
                st.metric(
                    "🥉 3º Lugar",
                    ranking_ordenado.iloc[2]['nick'],
                    f"{ranking_ordenado.iloc[2][col_score]} pts"
                )

        st.markdown("---")

        ranking_final = processar_ranking_completo(
            ranking_ordenado,
            col_score
        )

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone":
                return ['background-color: #004d00; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone":
                return ['background-color: #4d2600; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            ranking_final.style
            .background_gradient(cmap='YlGnBu', subset=[col_score])
            .apply(highlight_zones, axis=1)
            .format(precision=2),
            use_container_width=True,
            height=650,
            hide_index=True
        )

    with tab1:
        f_pro = (
            (df_bruto['kr'] * 40)
            + (df_bruto['dano_medio'] / 8)
            + ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

    with tab2:
        f_team = (
            ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 10)
            + ((df_bruto['revives'] / df_bruto['partidas']) * 50)
            + ((df_bruto['assists'] / df_bruto['partidas']) * 35)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

    with tab3:
        f_elite = (
            (df_bruto['kr'] * 50)
            + ((df_bruto['headshots'] / df_bruto['partidas']) * 60)
            + (df_bruto['dano_medio'] / 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>",
        unsafe_allow_html=True
    )

else:
    st.info("Banco conectado. Aguardando inserção de dados na tabela 'ranking_squad'.")
