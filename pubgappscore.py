import streamlit as st
import pandas as pd
import psycopg2
import requests
import time

# 1. Configuração da página (DEVE SER A PRIMEIRA LINHA)
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

# 2. Configurações e Chaves
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIxMTNkNWFkMC1lYzVhLTAxM2UtNWY0NC02NjA2MjJjNmQwYmIiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzcxMTMyMDEzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii0xY2NmM2YzMC1jYmRlLTQxMzctODM2Yy05ODY3ZDAxOWUwZDEifQ.kjXG3IJlpYJF0ybz9i7VCtGAGgBjCqds_qQuHsyhyu4"

LISTA_JOGADORES = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

# --- FUNÇÕES ---

def buscar_ids_na_api():
    """Busca os IDs dos jogadores na API do PUBG e retorna um dicionário"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }
    mapa_ids = {}
    
    # API permite apenas 10 por vez
    for i in range(0, len(LISTA_JOGADORES), 10):
        grupo = LISTA_JOGADORES[i:i+10]
        nicks_string = ",".join(grupo)
        url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nicks_string}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                dados = response.json()
                for p in dados['data']:
                    mapa_ids[p['attributes']['name']] = p['id']
            time.sleep(1) # Evita bloqueio por excesso de requisições
        except Exception as e:
            st.error(f"Erro na API: {e}")
    return mapa_ids

@st.cache_data(ttl=600)
def carregar_ranking_banco():
    """Lê os dados do seu banco PostgreSQL"""
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"], connect_timeout=5)
        query = "SELECT * FROM ranking_squad ORDER BY score DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro no Banco: {e}")
        return None

# --- INTERFACE ---

st.title("🏆 PUBG Squad Control")

# Criamos abas para não sobrecarregar a página inicial
tab1, tab2 = st.tabs(["📊 Ranking", "⚙️ Gerenciar IDs"])

with tab1:
    if st.button('🔄 Forçar Atualização do Banco'):
        st.cache_data.clear()
        st.rerun()
        
    df = carregar_ranking_banco()
    if df is not None:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aguardando conexão com o banco de dados...")

with tab2:
    st.subheader("Buscar IDs dos Jogadores")
    if st.button('🔍 Obter IDs da API agora'):
        with st.spinner('Consultando API do PUBG...'):
            resultados = buscar_ids_na_api()
            if resultados:
                st.success(f"Encontrados {len(resultados)} IDs!")
                st.json(resultados) # Mostra os IDs na tela
                
                # Opcional: Aqui você pode adicionar o código para salvar no banco
            else:
                st.error("Nenhum ID encontrado. Verifique sua API Key ou os Nicks.")
