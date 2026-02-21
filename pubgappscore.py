import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(page_title="PUBG Ranking - Sync", layout="wide")

# =============================
# FUNÇÃO DE BUSCA SEM CACHE (ABRE E FECHA CONEXÃO)
# =============================
def fetch_data_now():
    """
    Esta função não usa st.connection para evitar o cache interno do Streamlit.
    Ela cria um motor de conexão novo a cada clique.
    """
    try:
        # Pega a URL diretamente dos secrets
        db_url = st.secrets["DATABASE_URL"]
        
        # Cria engine com pool_size=0 para não manter conexões abertas com dados velhos
        engine = create_engine(db_url, pool_size=0, pool_recycle=0)
        
        with engine.connect() as conn:
            # Força o banco a finalizar transações pendentes
            conn.execute(text("COMMIT"))
            
            # Query com 'Cache Buster' (um comentário com timestamp)
            # Isso obriga o banco a processar a query do zero
            query = text(f"SELECT * FROM ranking_squad -- refresh_{int(time.time())}")
            df = pd.read_sql(query, conn)
            
        return df
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return pd.DataFrame()

# =============================
# INTERFACE
# =============================
st.title("🎮 Sincronização de Ranking")

# Criamos uma coluna para o botão de atualização
col_btn, col_info = st.columns([1, 3])

with col_btn:
    if st.button("🔄 RODAR ATUALIZAÇÃO AGORA"):
        # 1. Limpa o cache de dados do Streamlit
        st.cache_data.clear()
        # 2. Limpa o cache de recursos (conexões)
        st.cache_resource.clear()
        # 3. Recarrega a página
        st.rerun()

# Busca os dados reais
df = fetch_data_now()

if not df.empty:
    with col_info:
        st.success(f"Dados lidos do banco às {time.strftime('%H:%M:%S')}")
        st.info(f"Total de jogadores encontrados: {len(df)}")

    st.divider()

    # --- VALIDAÇÃO DOS DADOS ---
    st.subheader("📊 Conferência de Dados (Dados Brutos do Banco)")
    st.write("Verifique abaixo se o número de partidas já mudou:")
    
    # Exibimos apenas as colunas principais para conferência rápida
    st.dataframe(df[['nick', 'partidas', 'kr', 'vitorias']].sort_values('partidas', ascending=False), use_container_width=True)

    # --- CÁLCULO DO RANKING ---
    # (Apenas se os dados acima estiverem corretos)
    df['partidas'] = df['partidas'].replace(0, 1)
    
    # Exemplo simples de Score para teste rápido
    df['Score_Teste'] = ((df['vitorias'] / df['partidas']) * 100).round(2)
    
    st.divider()
    st.subheader("🏆 Ranking Processado")
    st.dataframe(df.sort_values('Score_Teste', ascending=False), use_container_width=True)

else:
    st.error("Não foi possível carregar os dados. Verifique sua conexão e a tabela 'ranking_squad'.")
