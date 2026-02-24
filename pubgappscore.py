import streamlit as st
import pandas as pd
import psycopg2
import requests
from datetime import datetime

# 1. Configuração da Página
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

# 2. Dicionário de IDs (Mapeamento oficial)
MAPA_JOGADORES = {
    "Adrian-Wan": "account.58beb24ada7346408942d42dc64c7901",
    "MironoteuCool": "account.24b0600cbba342eab1546ae2881f50fa",
    "FabioEspeto": "account.d8ccad228a4a417dad9921616d6c6bcd",
    "Mamutag_Komander": "account.64c62d76cce74d0b99857a27975e350e",
    "Robson_Foz": "account.8142e6d837254ee1bca954b719692f38",
    "MEIRAA": "account.c3f37890e7534978abadaf4bae051390",
    "EL-LOCORJ": "account.94ab932726fc4c64a03eb9797429baa3",
    "SalaminhoKBD": "account.de093e200d3441a9b781a9717a017dd3",
    "nelio_ponto_dev": "account.ad39c88ddf754d33a3dfeadc117c47df",
    "CARNEIROOO": "account.8c0313f2148d47b7bffcde634f094445",
    "Kowalski_PR": "account.b25200afe120424a839eb56dd2bc49cb",
    "Zacouteguy": "account.a742bf1d5725467c91140cd0ed83c265",
    "Sidors": "account.60ab21fad4094824a32dc404420b914d",
    "Takato_Matsuki": "account.10d2403139bd4066a95dda1a3eefe1e8",
    "cmm01": "account.80cedebb935242469fdd177454a52e0e",
    "Petrala": "account.aadd1c378ff841219d853b4ad2646286",
    "Fumiga_BR": "account.1fa2a7c08c3e4d4786587b4575a071cb"
}

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIxMTNkNWFkMC1lYzVhLTAxM2UtNWY0NC02NjA2MjJjNmQwYmIiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzcxMTMyMDEzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii0xY2NmM2YzMC1jYmRlLTQxMzctODM2Yy05ODY3ZDAxOWUwZDEifQ.kjXG3IJlpYJF0ybz9i7VCtGAGgBjCqds_qQuHsyhyu4"

# --- FUNÇÕES DE LÓGICA ---

def sincronizar_api_com_banco():
    """Busca dados na API por ID e salva no banco de dados"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }
    
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        cur = conn.cursor()
        
        for nick, account_id in MAPA_JOGADORES.items():
            # Exemplo: Buscando stats da temporada atual (shards/steam/players/ID/seasons/division.bro.official.pc-2024-31)
            # Nota: O ID da season muda. Aqui usamos o endpoint geral de lifetime ou season atual
            url = f"https://api.pubg.com/shards/steam/players/{account_id}/seasons/lifetime"
            res = requests.get(url, headers=headers)
            
            if res.status_code == 200:
                stats = res.json()['data']['attributes']['gameModeStats']['squad-fpp']
                
                # Cálculos simples
                kills = stats.get('kills', 0)
                partidas = stats.get('roundsPlayed', 0)
                vitorias = stats.get('wins', 0)
                dano = stats.get('damageDealt', 0)
                dano_medio = dano / partidas if partidas > 0 else 0
                kr = kills / partidas if partidas > 0 else 0
                score = (vitorias * 100) + kills + (dano / 10) # Exemplo de fórmula
                
                # Atualiza o banco de dados
                query = """
                    INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, score, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (nick) DO UPDATE SET
                    partidas = EXCLUDED.partidas, kr = EXCLUDED.kr, vitorias = EXCLUDED.vitorias,
                    kills = EXCLUDED.kills, dano_medio = EXCLUDED.dano_medio, 
                    score = EXCLUDED.score, atualizado_em = EXCLUDED.atualizado_em
                """
                cur.execute(query, (nick, partidas, kr, vitorias, kills, dano_medio, score, datetime.now()))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro na sincronização: {e}")
        return False

@st.cache_data(ttl=300)
def carregar_dados():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        df = pd.read_sql("SELECT * FROM ranking_squad ORDER BY score DESC", conn)
        conn.close()
        return df
    except:
        return None

# --- INTERFACE ---

st.title("🏆 Ranking Squad PUBG")

if st.button('🔄 Sincronizar Agora (API -> Banco)'):
    with st.spinner('Acessando API do PUBG e atualizando banco de dados...'):
        if sincronizar_api_com_banco():
            st.cache_data.clear()
            st.success("Dados atualizados!")
            st.rerun()

df = carregar_dados()

if df is not None and not df.empty:
    st.info(f"Última atualização geral: {df['atualizado_em'].max()}")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.warning("Clique no botão acima para carregar os dados pela primeira vez.")
