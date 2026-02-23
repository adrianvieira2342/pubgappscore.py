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

# Sua lista original de jogadores
players_list = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

# ==========================================
# 2. CONEXÃO COM O BANCO
# ==========================================
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    st.success("Conectado ao Supabase!")
except Exception as e:
    st.error(f"Erro na conexão com o banco: {e}")
    st.stop()

def fazer_requisicao(url):
    """Lida com requests e Rate Limit da API oficial"""
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            st.warning("Limite da API atingido. Aguardando 30 segundos...")
            time.sleep(30)
            continue
        return res
    return None

# ==========================================
# 3. BUSCAR TEMPORADA E IDs (BATCH)
# ==========================================
st.write("Sincronizando com a API do PUBG...")

# Busca Temporada
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
if res_season and res_season.status_code == 200:
    seasons = res_season.json()["data"]
    current_season_id = next(s["id"] for s in seasons if s["attributes"]["isCurrentSeason"])
else:
    st.error("Erro ao obter temporada.")
    st.stop()

# Busca IDs em lote (1 única chamada para todos os nomes)
nicks_str = ",".join(players_list)
res_p = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={nicks_str}")
if res_p and res_p.status_code == 200:
    player_map = {p["attributes"]["name"]: p["id"] for p in res_p.json()["data"]}
else:
    st.error("Erro ao mapear jogadores.")
    st.stop()

# ==========================================
# 4. ATUALIZAÇÃO DO RANKING (UPSERT)
# ==========================================
st.info(f"Processando {len(player_map)} jogadores...")
progress_bar = st.progress(0)

for i, (nick, p_id) in enumerate(player_map.items()):
    url_stats = f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}"
    res_s = fazer_requisicao(url_stats)
    
    if res_s and res_s.status_code == 200:
        game_data = res_s.json()["data"]["attributes"]["gameModeStats"]
        stats = game_data.get("squad", {})
        partidas = stats.get("roundsPlayed", 0)

        if partidas > 0:
            # Captura de dados brutos
            kills = stats.get("kills", 0)
            vits = stats.get("wins", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            dmg = stats.get("damageDealt", 0)
            dist_max = stats.get("longestKill", 0.0)

            # Suas Fórmulas
            kr = round(kills / partidas, 2)
            dano_medio = int(dmg / partidas)
            win_rate = (vits / partidas) * 100
            
            score = round(
                (kr * 40) + (dano_medio / 8) + (win_rate * 2) + 
                ((headshots/partidas) * 15) + ((assists/partidas) * 10) + ((revives/partidas) * 5)
            , 2)

            # SQL INTEGRADO COM SUA TABELA
            # nick deve ser UNIQUE no banco para o ON CONFLICT funcionar
            sql = """
            INSERT INTO ranking_squad 
            (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, score, atualizado_em) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
            
            try:
                valores = (nick, partidas, kr, vits, kills, dano_medio, assists, headshots, revives, dist_max, score)
                cursor.execute(sql, valores)
                conn.commit()
                st.write(f"✔️ {nick} atualizado.")
            except Exception as e:
                conn.rollback()
                st.error(f"Erro em {nick}: {e}")
        else:
            st.write(f"⚪ {nick} sem jogos.")

    progress_bar.progress((i + 1) / len(player_map))
    time.sleep(6) # Mantém os 10 RPM (Requests por Minuto)

st.success("Ranking atualizado com sucesso!")
cursor.close()
conn.close()
