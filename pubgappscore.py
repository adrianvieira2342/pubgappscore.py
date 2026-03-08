import streamlit as st
import pandas as pd
import requests
import psycopg2
import os
from datetime import datetime

# =============================
# CONFIGURAÇÃO DA PÁGINA (ORIGINAL)
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# [MANTIDO: SEU CSS CUSTOMIZADO...]
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; padding: 15px; border-radius: 12px; border: 1px solid #30363d; text-align: center; }
    [data-testid="stMetricLabel"] * { font-size: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 38px !important; }
    div[data-testid="stTabs"] button { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# LÓGICA DE ATUALIZAÇÃO AUTOMÁTICA (NOVO/INTERNO)
# ==========================================================

def atualizar_dados_pubg_api():
    """Lógica que era do GitHub Actions, agora interna e silenciosa"""
    try:
        API_KEY = st.secrets["PUBG_API_KEY"]
        DATABASE_URL = st.secrets["DATABASE_URL"]
        BASE_URL = "https://api.pubg.com/shards/steam"
        headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/vnd.api+json"}

        # 1. Detectar Temporada
        res_season = requests.get(f"{BASE_URL}/seasons", headers=headers).json()
        current_season_id = next(s["id"] for s in res_season["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Mapeamento de IDs (Seus 18 nicks)
        players_names = [
            "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
            "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
            "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
            "Sidors", "Takato_Matsuki", "cmm01", "Petrala",
            "Fumiga_BR", "O-CARRASCO"
        ]
        
        mapping_id_name = {}
        for i in range(0, len(players_names), 10):
            grupo = ",".join(players_names[i:i+10])
            res = requests.get(f"{BASE_URL}/players?filter[playerNames]={grupo}", headers=headers)
            if res.status_code == 200:
                for p in res.json()["data"]:
                    mapping_id_name[p["id"]] = p["attributes"]["name"]

        # 3. Buscar Stats em Lote (Batch)
        resultados = []
        ids_list = list(mapping_id_name.keys())
        for i in range(0, len(ids_list), 10):
            grupo_ids = ",".join(ids_list[i:i+10])
            url_stats = f"{BASE_URL}/seasons/{current_season_id}/gameMode/squad/players?filter[playerIds]={grupo_ids}"
            res = requests.get(url_stats, headers=headers)
            if res.status_code == 200:
                for p_data in res.json().get("data", []):
                    p_id = p_data["relationships"]["player"]["data"]["id"]
                    stats = p_data["attributes"]["gameModeStats"]
                    partidas = stats.get("roundsPlayed", 0)
                    if partidas > 0:
                        resultados.append((
                            mapping_id_name.get(p_id), partidas, round(stats.get("kills", 0)/partidas, 2),
                            stats.get("wins", 0), stats.get("kills", 0), int(stats.get("damageDealt", 0)/partidas),
                            stats.get("assists", 0), stats.get("headshotKills", 0), stats.get("revives", 0),
                            stats.get("longestKill", 0.0), datetime.utcnow()
                        ))

        # 4. Gravar no Banco
        if resultados:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            sql = """
                INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (nick) DO UPDATE SET 
                partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias, kills=EXCLUDED.kills, 
                dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists, headshots=EXCLUDED.headshots, 
                revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max, atualizado_em=EXCLUDED.atualizado_em
            """
            cur.executemany(sql, resultados)
            conn.commit()
            cur.close()
            conn.close()
    except Exception as e:
        print(f"Erro na atualização silenciosa: {e}")

# =============================
# CONEXÃO COM BANCO (COM CACHE AUTOMÁTICO)
# =============================
@st.cache_data(ttl=300) # Define a atualização a cada 5 minutos
def get_cached_data(table_name):
    # Antes de ler, ele tenta atualizar os dados na API do PUBG
    atualizar_dados_pubg_api()
    
    # Agora lê os dados atualizados
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        df = conn.query(f"SELECT * FROM {table_name}", ttl=0)
        return df
    except:
        return pd.DataFrame()

# Substituindo a chamada original pela função com cache
def get_data(table_name="v_ranking_squad_completo"):
    return get_cached_data(table_name)

# [TODO O RESTANTE DO SEU CÓDIGO DE PROCESSAMENTO E INTERFACE PERMANECE IGUAL...]
# =============================
# PROCESSAMENTO DO RANKING (ORIGINAL)
# =============================
def processar_ranking_completo(df_ranking, col_score):
    # ... (Seu código original aqui)
    pass # Remova o pass ao colar

# ... (Continue com seu código original de renderização, Tabs, etc)
