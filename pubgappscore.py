import os
import time
import requests
import psycopg2
import streamlit as st

# ==========================================
# 1. CONFIGURAÇÕES E ACESSO ÀS SECRETS
# ==========================================
try:
    API_KEY = st.secrets["PUBG_API_KEY"]
    DATABASE_URL = st.secrets["DATABASE_URL"]
except KeyError as e:
    st.error(f"Erro: Chave {e} não encontrada no Streamlit Secrets.")
    st.stop()

BASE_URL = "https://api.pubg.com/shards/steam"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

players_list = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

# ==========================================
# 2. CONEXÃO COM O BANCO (POSTGRESQL)
# ==========================================
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    st.success("Conectado ao Supabase com sucesso!")
except Exception as e:
    st.error(f"Erro na conexão: {e}")
    st.stop()

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            st.warning("API em Rate Limit. Aguardando 30s...")
            time.sleep(30)
            continue
        return res
    return None

# ==========================================
# 3. BUSCAR TEMPORADA E IDs
# ==========================================
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
if res_season and res_season.status_code == 200:
    seasons = res_season.json()["data"]
    current_season_id = next(s["id"] for s in seasons if s["attributes"]["isCurrentSeason"])
else:
    st.error("Erro ao obter temporada.")
    st.stop()

nicks_str = ",".join(players_list)
res_p = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={nicks_str}")
if res_p and res_p.status_code == 200:
    player_map = {p["attributes"]["name"]: p["id"] for p in res_p.json()["data"]}
else:
    st.error("Erro ao mapear jogadores.")
    st.stop()

# ==========================================
# 4. LOOP DE ATUALIZAÇÃO (UPSERT CORRIGIDO)
# ==========================================
st.info(f"Sincronizando {len(player_map)} jogadores...")
progress_bar = st.progress(0)

for i, (nick, p_id) in enumerate(player_map.items()):
    url_stats = f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}"
    res_s = fazer_requisicao(url_stats)
    
    if res_s and res_s.status_code == 200:
        stats = res_s.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
        partidas = stats.get("roundsPlayed", 0)

        if partidas > 0:
            kills = stats.get("kills", 0)
            vitorias = stats.get("wins", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            dano_total = stats.get("damageDealt", 0)
            dist_max = stats.get("longestKill", 0.0)

            kr = round(kills / partidas, 2)
            dano_medio = int(dano_total / partidas)
            win_rate = (vitorias / partidas) * 100
            
            # Cálculo do Score
            score = round((kr * 40) + (dano_medio / 8) + (win_rate * 2) + 
                          ((headshots/partidas) * 15) + ((assists/partidas) * 10), 2)

            # SQL AJUSTADO: Removido a coluna atualizado_em do VALUES para deixar o Postgres gerenciar
            # mas mantendo-a no UPDATE para marcar a nova hora.
            sql = """
            INSERT INTO ranking_squad 
            (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, score) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (nick) DO UPDATE SET 
            partidas = EXCLUDED.partidas,
            kr = EXCLUDED.kr,
            vitorias = EXCLUDED.vitorias,
            kills = EXCLUDED.kills,
            dano_medio = EXCLUDED.dano_medio,
            assists = EXCLUDED.assists,
            headshots = EXCLUDED.headshots,
            revives = EXCLUDED.revives,
            kill_dist_max = EXCLUDED.kill_dist_max,
            score = EXCLUDED.score,
            atualizado_em = NOW();
            """
            
            # Tupla com EXATAMENTE 11 valores para as 11 colunas do INSERT
            valores = (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, dist_max, score)
            
            try:
                cursor.execute(sql, valores)
                conn.commit()
                st.write(f"✔️ {nick} atualizado.")
            except Exception as e:
                st.error(f"Erro ao inserir {nick}: {e}")
                conn.rollback()
        else:
            st.write(f"⚪ {nick} sem partidas.")

    progress_bar.progress((i + 1) / len(player_map))
    time.sleep(6)

st.success("Sincronização Finalizada!")
cursor.close()
conn.close()
