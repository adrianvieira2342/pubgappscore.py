import streamlit as st
import pandas as pd
import psycopg2

# Configuração da página
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

def carregar_ranking():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        # Query para buscar os dados ordenados pelo Score
        query = "SELECT nick, partidas, kr, vitorias, kills, dano_medio, score, atualizado_em FROM ranking_squad ORDER BY score DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas atualizadas automaticamente via API Oficial.")

# Botão para atualizar (opcional, já que você tem o script de sincronização)
if st.button('🔄 Recarregar Tabela'):
    st.cache_data.clear()

df_ranking = carregar_ranking()

if df_ranking is not None:
    # 1. Destaque para o Top 3 (Métricas)
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(df_ranking):
            player = df_ranking.iloc[i]
            col.metric(label=f"{i+1}º Lugar", value=player['nick'], delta=f"Score: {player['score']}")

    st.divider()

    # 2. Tabela de Dados Formatada
    st.subheader("📊 Classificação Geral")
    st.dataframe(
        df_ranking,
        column_config={
            "nick": "Jogador",
            "partidas": "Partidas",
            "kr": st.column_config.NumberColumn("K/R", format="%.2f"),
            "vitorias": "Vitórias",
            "kills": "Total Kills",
            "dano_medio": "Dano Médio",
            "score": st.column_config.ProgressColumn("Pontuação Final", min_value=0, max_value=float(df_ranking['score'].max())),
            "atualizado_em": st.column_config.DatetimeColumn("Última Atualização", format="DD/MM/YYYY HH:mm")
        },
        hide_index=True,
        use_container_width=True
    )

    # 3. Gráfico de Comparação de Dano vs Kills
    st.divider()
    st.subheader("🎯 Performance: Dano vs Kills")
    st.scatter_chart(df_ranking, x='dano_medio', y='kills', color='nick')

else:
    st.warning("Nenhum dado encontrado na tabela ranking_squad.")
