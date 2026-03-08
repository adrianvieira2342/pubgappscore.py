import streamlit as st
import pandas as pd
import requests
import psycopg2
from datetime import datetime

# =============================
# 1. CONFIGURAÇÃO (SEU LAYOUT ORIGINAL)
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🏆",
    initial_sidebar_state="collapsed"
)

# =============================
# 2. CSS CUSTOM (SEU LAYOUT ORIGINAL)
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
    }
    [data-testid="stMetricLabel"] * { font-size: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 38px !important; }
    div[data-testid="stTabs"] button { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 3. LÓGICA DE ATUALIZAÇÃO AUTOMÁTICA (EXECUÇÃO SILENCIOSA)
# ==========================================================
def rodar_atualizacao_api():
    """Busca dados na API e salva no Postgres sem travar a UI"""
    try:
        api_key = st.secrets["PUBG_API_KEY"]
        db_url = st.secrets["DATABASE_URL"]
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/vnd.api+json"}
        
        # 1. Identifica Temporada Atual
        res_s = requests.get("https://api.pubg.com/shards/steam/seasons", headers=headers, timeout=5).json()
        s_id = next(s["id"] for s in res_s["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Jogadores do Squad
        nicks = ["Adrian-Wan", "Robson_Foz", "SalaminhoKBD", "MironoteuCool", "FabioEspeto", "Mamutag_Komander", "MEIRAA", "EL-LOCORJ", "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy", "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR", "O-CARRASCO"]
        
        mapping = {}
        for i in range(0, len(nicks), 10):
            g = ",".join(nicks[i:i+10])
            r = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={g}", headers=headers, timeout=5)
            if r.status_code == 200:
                for p in r.json()["data"]: mapping[p["id"]] = p["attributes"]["name"]

        # 3. Coleta de Stats
        res_stats = []
        ids = list(mapping.keys())
        for i in range(0, len(ids), 10):
            g_ids = ",".join(ids[i:i+10])
            rb = requests.get(f"https://api.pubg.com/shards/steam/seasons/{s_id}/gameMode/squad/players?filter[playerIds]={g_ids}", headers=headers, timeout=5)
            if rb.status_code == 200:
                for d in rb.json().get("data", []):
                    p_id = d["relationships"]["player"]["data"]["id"]
                    s = d["attributes"]["gameModeStats"]
                    if s.get("roundsPlayed", 0) > 0:
                        res_stats.append((mapping.get(p_id), s["roundsPlayed"], round(s["kills"]/s["roundsPlayed"], 2), s["wins"], s["kills"], int(s["damageDealt"]/s["roundsPlayed"]), s["assists"], s["headshotKills"], s["revives"], s["longestKill"], datetime.utcnow()))

        # 4. Gravação no Banco
        if res_stats:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.executemany("""INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, atualizado_em)
                                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                     ON CONFLICT (nick) DO UPDATE SET partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias, kills=EXCLUDED.kills, dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists, headshots=EXCLUDED.headshots, revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max, atualizado_em=EXCLUDED.atualizado_em""", res_stats)
    except:
        pass

# =============================
# 4. CARREGAMENTO DE DADOS COM GATILHO
# =============================
@st.cache_data(ttl=60) # Atualiza no máximo uma vez por minuto se alguém abrir a página
def carregar_e_atualizar():
    rodar_atualizacao_api()
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        df = conn.query("SELECT * FROM v_ranking_squad_completo", ttl=0)
        df_bots = conn.query("SELECT * FROM ranking_bot", ttl=0)
        return df, df_bots
    except:
        return pd.DataFrame(), pd.DataFrame()

# =============================
# 5. RENDERIZAÇÃO (SEU LAYOUT ORIGINAL)
# =============================
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

# Chamada principal que faz tudo sozinha
df_bruto, df_bots_raw = carregar_e_atualizar()

# ... (MANTENHA AQUI TODO O SEU CÓDIGO DE PROCESSAMENTO, ABAS E TABELAS)
