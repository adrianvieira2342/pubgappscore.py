import streamlit as st
import pandas as pd
import psycopg2

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Ranking Squad",
    layout="wide",
    page_icon="🎮"
)

# =============================
# FUNÇÃO PARA CARREGAR DADOS
# =============================
@st.cache_data(ttl=300)  # cache por 5 minutos
def carregar_ranking():
    try:
        with psycopg2.connect(st.secrets["DATABASE_URL"]) as conn:
            query = """
                SELECT 
                    nick, 
                    partidas, 
                    kr, 
                    vitorias, 
                    kills, 
                    dano_medio, 
                    score, 
                    atualizado_em 
                FROM ranking_squad 
                ORDER BY score DESC
            """
            df = pd.read_sql(query, conn)
            return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


# =============================
# TÍTULO
# =============================
st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas atualizadas automaticamente via API Oficial.")

# =============================
# BOTÃO DE ATUALIZAÇÃO
# =============================
if st.button("🔄 Recarregar Tabela"):
    st.cache_data.clear()
    st.rerun()


# =============================
# CARREGAR DADOS
# =============================
df_ranking = carregar_ranking()

if df_ranking is not None and not df_ranking.empty:

    # =============================
    # TOP 3
    # =============================
    cols = st.columns(3)

    for i, col in enumerate(cols):
        if i < len(df_ranking):
            player = df_ranking.iloc[i]
            col.metric(
                label=f"{i+1}º Lugar",
                value=player["nick"],
                delta=f"Score: {round(player['score'], 2)}"
            )

    st.divider()

    # =============================
    # TABELA COMPLETA
    # =============================
    st.subheader("📊 Classificação Geral")

    max_score = float(df_ranking["score"].max()) if not df_ranking["score"].empty else 1

    st.dataframe(
        df_ranking,
        column_config={
            "nick": "Jogador",
            "partidas": "Partidas",
            "kr": st.column_config.NumberColumn("K/R", format="%.2f"),
            "vitorias": "Vitórias",
            "kills": "Total Kills",
            "dano_medio": "Dano Médio",
            "score": st.column_config.ProgressColumn(
                "Pontuação Final",
                min_value=0,
                max_value=max_score
            ),
            "atualizado_em": st.column_config.DatetimeColumn(
                "Última Atualização",
                format="DD/MM/YYYY HH:mm"
            )
        },
        hide_index=True,
        use_container_width=True
    )

    # =============================
    # GRÁFICO
    # =============================
    st.divider()
    st.subheader("🎯 Performance: Dano vs Kills")

    st.scatter_chart(
        df_ranking,
        x="dano_medio",
        y="kills",
        color="nick"
    )

else:
    st.warning("Nenhum dado encontrado na tabela ranking_squad.")
