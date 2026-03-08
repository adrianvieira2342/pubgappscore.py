import streamlit as st
import pandas as pd
import requests
import psycopg2
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

# ==========================================================
# LÓGICA DE ATUALIZAÇÃO (PROTEGIDA)
# ==========================================================
def realizar_update_silencioso():
    """Executa a atualização de 10 em 10 sem travar a interface"""
    try:
        # Puxa credenciais das Secrets de forma segura
        api_key = st.secrets.get("PUBG_API_KEY")
        db_url = st.secrets.get("DATABASE_URL")
        if not api_key or not db_url: return

        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/vnd.api+json"}
        base_url = "https://api.pubg.com/shards/steam"

        # 1. Temporada atual
        res_s = requests.get(f"{base_url}/seasons", headers=headers, timeout=10).json()
        s_id = next(s["id"] for s in res_s["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Lista de Jogadores
        nicks = ["Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander", "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD", "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy", "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR", "O-CARRASCO"]
        
        mapping = {}
        for i in range(0, len(nicks), 10):
            g = ",".join(nicks[i:i+10])
            r = requests.get(f"{base_url}/players?filter[playerNames]={g}", headers=headers, timeout=10)
            if r.status_code == 200:
                for p in r.json()["data"]: mapping[p["id"]] = p["attributes"]["name"]

        # 3. Stats em Lote
        res_stats = []
        ids = list(mapping.keys())
        for i in range(0, len(ids), 10):
            g_ids = ",".join(ids[i:i+10])
            url_batch = f"{base_url}/seasons/{s_id}/gameMode/squad/players?filter[playerIds]={g_ids}"
            rb = requests.get(url_batch, headers=headers, timeout=10)
            if rb.status_code == 200:
                for d in rb.json().get("data", []):
                    p_id = d["relationships"]["player"]["data"]["id"]
                    s = d["attributes"]["gameModeStats"]
                    if s.get("roundsPlayed", 0) > 0:
                        res_stats.append((mapping.get(p_id), s["roundsPlayed"], round(s["kills"]/s["roundsPlayed"], 2), s["wins"], s["kills"], int(s["damageDealt"]/s["roundsPlayed"]), s["assists"], s["headshotKills"], s["revives"], s["longestKill"], datetime.utcnow()))

        # 4. Update no Banco com psycopg2 (Conexão direta)
        if res_stats:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            sql = """INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, atualizado_em)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                     ON CONFLICT (nick) DO UPDATE SET partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias, kills=EXCLUDED.kills, dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists, headshots=EXCLUDED.headshots, revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max, atualizado_em=EXCLUDED.atualizado_em"""
            cur.executemany(sql, res_stats)
            conn.commit()
            cur.close()
            conn.close()
    except:
        pass # Garante que o app não pare se a API falhar

# Decorador para atualizar apenas a cada 5 minutos sem travar o carregamento
@st.cache_data(ttl=300)
def check_update():
    realizar_update_silencioso()
    return True

# Chama a verificação (se estiver no tempo, ele atualiza; se não, passa direto)
check_update()

# =============================
# CSS TEMA ESCURO (ORIGINAL)
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; padding: 15px; border-radius: 12px; border: 1px solid #30363d; text-align: center; }
    [data-testid="stMetricLabel"] * { font-size: 40px !important; }
    [data-testid="stMetricValue"] { font-size: 38px !important; }
    div[data-testid="stTabs"] button { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =============================
# CONEXÃO COM BANCO (ORIGINAL)
# =============================
def get_data(table_name="v_ranking_squad_completo"):
    try:
        # Usa o conector nativo do Streamlit para leitura rápida
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        return conn.query(f"SELECT * FROM {table_name}", ttl=0)
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# DAQUI PARA BAIXO: SEU LAYOUT ORIGINAL COMPLETO
# =============================
st.markdown("<h1 style='text-align:left;'>🏆 PUBG Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

# ... (MANTENHA TODO O RESTANTE DO SEU CÓDIGO EXATAMENTE COMO ESTAVA)
