import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import OperationalError

# 1. Configuração Inicial (Sempre a primeira linha do Streamlit)
st.set_page_config(
    page_title="PUBG Ranking Squad", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. Função de carregamento com Cache e Timeout
# O ttl=300 faz com que os dados expirem sozinhos a cada 5 minutos
@st.cache_data(ttl=300, show_spinner="Buscando dados no Banco...")
def carregar_ranking():
    try:
        # Adicionamos connect_timeout=5 para a página não travar se o banco cair
        conn = psycopg2.connect(
            st.secrets["DATABASE_URL"], 
            connect_timeout=5
        )
        
        query = """
            SELECT nick, partidas, kr, vitorias, kills, dano_medio, score, atualizado_em 
            FROM ranking_squad 
            ORDER BY score DESC
        """
        
        # Lê os dados
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    except OperationalError:
        st.error("🔌 **Erro de Conexão:** O Streamlit não conseguiu alcançar seu banco de dados.")
        st.info("Verifique se o IP do Streamlit Cloud está liberado no firewall do seu banco (ex: Supabase, Render, AWS).")
        return None
    except Exception as e:
        st.error(f"❌ **Erro Crítico:** {e}")
        return None

# --- INTERFACE DO USUÁRIO ---

st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas sincronizadas via API Oficial.")

# 3. Botão de Recarregar (Lógica Corrigida)
# Colocamos o botão em uma coluna para melhor visual visual
col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button('🔄 Atualizar Agora'):
        st.cache_data.clear()  # Limpa o cache da função carregar_ranking
        st.toast("Limpando cache...")
        st.rerun()  # Força o script a rodar de novo e buscar dados novos

st.divider()

# 4. Execução da busca de dados
df_ranking = carregar_ranking()

# 5. Renderização Condicional (Só mostra se houver dados)
if df_ranking is not None and not df_ranking.empty:
    
    # Bloco Top 3
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(df_ranking):
            player = df_ranking.iloc[i]
            col.metric(
                label=f"{i+1}º Lugar", 
                value=player['nick'], 
                delta=f"{player['score']:.0f} pts"
            )

    st.divider()

    # Tabela Formatada
    st.subheader("📊 Classificação Geral")
    st.dataframe(
        df_ranking,
        column_config={
            "nick": "Jogador",
            "kr": st.column_config.NumberColumn("K/R", format="%.2f"),
            "score": st.column_config.ProgressColumn(
                "Pontuação", 
                min_value=0, 
                max_value=float(df_ranking['score'].max())
            ),
            "atualizado_em": st.column_config.DatetimeColumn(
                "Sincronizado em", 
                format="DD/MM/YYYY HH:mm"
            )
        },
        hide_index=True,
        use_container_width=True
    )

    # Gráfico
    st.divider()
    st.subheader("🎯 Performance: Dano Médio vs Total Kills")
    st.scatter_chart(df_ranking, x='dano_medio', y='kills', color='nick')

elif df_ranking is not None and df_ranking.empty:
    st.warning("Conexão estabelecida, mas nenhum dado foi encontrado na tabela 'ranking_squad'.")

# Rodapé simples
st.caption("Desenvolvido para acompanhamento de estatísticas PUBG.")
