import streamlit as st
import pandas as pd
import psycopg2

# 1. Configuração da página (Deve ser a primeira linha de comando Streamlit)
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

# 2. Função de carregamento com CACHE
# O 'ttl' define que, mesmo sem clicar no botão, os dados expiram em 10 minutos
@st.cache_data(ttl=600)
def carregar_ranking():
    try:
        # Conexão usando st.secrets (Certifique-se de que está configurado no Streamlit Cloud ou .streamlit/secrets.toml)
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        
        # Query para buscar os dados
        query = "SELECT nick, partidas, kr, vitorias, kills, dano_medio, score, atualizado_em FROM ranking_squad ORDER BY score DESC"
        
        # Lê os dados para um DataFrame
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return None

# --- INTERFACE ---

st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas vindas do banco de dados (sincronizado com API Oficial).")

# 3. Lógica do Botão de Atualização
# Ao clicar, limpamos o cache e recarregamos a página inteira
if st.button('🔄 Recarregar e Limpar Cache'):
    st.cache_data.clear()
    st.toast("Limpando cache e buscando novos dados...")
    st.rerun()

# Chamada da função (se estiver no cache, é instantâneo; se limpou, ele consulta o banco)
df_ranking = carregar_ranking()

if df_ranking is not None and not df_ranking.empty:
    
    # 4. Destaque para o Top 3 (Métricas)
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(df_ranking):
            player = df_ranking.iloc[i]
            col.metric(
                label=f"{i+1}º Lugar", 
                value=player['nick'], 
                delta=f"Score: {player['score']:.0f}"
            )

    st.divider()

    # 5. Tabela de Dados Formatada
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
            "score": st.column_config.ProgressColumn(
                "Pontuação Final", 
                min_value=0, 
                max_value=float(df_ranking['score'].max())
            ),
            "atualizado_em": st.column_config.DatetimeColumn(
                "Última Atualização", 
                format="DD/MM/YYYY HH:mm"
            )
        },
        hide_index=True,
        use_container_width=True
    )

    # 6. Gráfico de Comparação de Dano vs Kills
    st.divider()
    st.subheader("🎯 Performance: Dano vs Kills")
    st.scatter_chart(
        df_ranking, 
        x='dano_medio', 
        y='kills', 
        color='nick'
    )

else:
    st.warning("Aguardando dados ou tabela ranking_squad vazia no banco de dados.")
