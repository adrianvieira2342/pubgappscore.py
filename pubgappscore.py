import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import OperationalError
import datetime

# 1. Configuração da página
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

# --- FUNÇÕES DE DADOS ---

@st.cache_data(ttl=300)
def carregar_ranking():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"], connect_timeout=5)
        # Adicionei um parâmetro aleatório comentado na query para evitar cache do próprio banco
        query = f"SELECT * FROM ranking_squad ORDER BY score DESC -- {datetime.datetime.now()}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao ler banco de dados: {e}")
        return None

def rodar_script_atualizacao():
    """
    Aqui você deve colar ou chamar a função que vai na API do PUBG 
    e faz o 'INSERT' ou 'UPDATE' no seu banco de dados.
    """
    try:
        # EXEMPLO DE LOGICA (Substitua pela sua chamada real da API se necessário)
        # conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        # cursor = conn.cursor()
        # ... logica da API aqui ...
        # conn.commit()
        # conn.close()
        
        # Se o seu script de sincronização for um arquivo separado chamado 'sync.py':
        # import sync
        # sync.main() 
        
        return True
    except Exception as e:
        st.error(f"Falha ao sincronizar com a API do PUBG: {e}")
        return False

# --- INTERFACE ---

st.title("🏆 Ranking Squad PUBG")

# Botão de ação dupla: Atualiza a API e depois limpa o Cache
if st.button('🔄 Sincronizar com API e Atualizar Tabela'):
    with st.spinner('Comunicando com a API do PUBG...'):
        sucesso = rodar_script_atualizacao() # 1. Tenta atualizar o banco
        if sucesso:
            st.cache_data.clear()            # 2. Limpa o cache do Streamlit
            st.toast("Dados atualizados com sucesso!")
            st.rerun()                       # 3. Recarrega a tela

df_ranking = carregar_ranking()

# --- EXIBIÇÃO ---
if df_ranking is not None and not df_ranking.empty:
    # Mostra a data do dado mais recente para você conferir
    ultima_att = df_ranking['atualizado_em'].max()
    st.caption(f"Última atualização detectada no banco: {ultima_att}")
    
    # ... (Restante do seu código de colunas, dataframe e gráfico) ...
    st.dataframe(df_ranking, use_container_width=True)
else:
    st.warning("Nenhum dado encontrado.")
