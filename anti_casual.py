import os
import time
import requests
import psycopg2
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("PUBG_API_KEY")
BASE_URL = "https://api.pubg.com/shards/steam"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

players = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala",
    "Fumiga_BR", "O-CARRASCO"
]

# ==================================
# REQUISIÇÃO COM CONTROLE DE RATE
# ==================================

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)

        if res.status_code == 429:
            retry = int(res.headers.get("Retry-After", 10))
            print(f"⏳ Rate limit... aguardando {retry}s")
            time.sleep(retry)
            continue

        return res
    return None

# ==================================
# DETECTAR TEMPORADA ATUAL
# ==================================

print("📅 Detectando temporada...")
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
current_season_id = next(
    s["id"] for s in res_season.json()["data"]
    if s["attributes"]["isCurrentSeason"]
)

print("Temporada:", current_season_id)

# ==================================
# BUSCAR IDS
# ==================================

player_ids = {}

print("🔎 Buscando IDs...")
res = fazer_requisicao(
    f"{BASE_URL}/players?filter[playerNames]={','.join(players)}"
)

for p in res.json()["data"]:
    player_ids[p["attributes"]["name"]] = p["id"]

print("IDs encontrados:", len(player_ids))

# ==================================
# FUNÇÃO PRINCIPAL
# ==================================

def buscar_stats(player, p_id):

    print(f"🔎 {player}")

    res_player = fazer_requisicao(f"{BASE_URL}/players/{p_id}")
    if not res_player:
        return None

    matches = res_player.json()["data"]["relationships"]["matches"]["data"]

    total_kills = 0
    total_wins = 0
    total_assists = 0
    total_headshots = 0
    total_revives = 0
    total_damage = 0
    max_kill_dist = 0
    partidas_validas = 0

    for m in matches:

        match_id = m["id"]
        res_match = fazer_requisicao(f"{BASE_URL}/matches/{match_id}")
        if not res_match:
            continue

        data = res_match.json()
        attr = data["data"]["attributes"]

        # Apenas temporada atual
        if attr.get("seasonId") != current_season_id:
            continue

        # Apenas squad TPP
        if attr.get("gameMode") != "squad":
            continue

        bots = 0
        player_stats = None

        for inc in data["included"]:
            if inc["type"] == "participant":
                stats = inc["attributes"]["stats"]

                # Contar bots
                if stats.get("playerId") == "ai":
                    bots += 1

                # Capturar stats do player
                if stats.get("playerId") == p_id:
                    player_stats = stats

        # 🔥 DETECÇÃO DEFINITIVA DE CASUAL
        if bots >= 80:
            print(f"❌ Casual removido ({bots} bots)")
            continue

        if not player_stats:
            continue

        partidas_validas += 1
        total_kills += player_stats.get("kills", 0)
        total_assists += player_stats.get("assists", 0)
        total_headshots += player_stats.get("headshotKills", 0)
        total_revives += player_stats.get("revives", 0)
        total_damage += player_stats.get("damageDealt", 0)

        if player_stats.get("winPlace") == 1:
            total_wins += 1

        longest = player_stats.get("longestKill", 0)
        if longest > max_kill_dist:
            max_kill_dist = longest

    if partidas_validas == 0:
        return None

    kr = round(total_kills / partidas_validas, 2)
    dano_medio = int(total_damage / partidas_validas)

    print(f"✅ {player} | {partidas_validas} partidas válidas")

    return (
        player,
        partidas_validas,
        kr,
        total_wins,
        total_kills,
        dano_medio,
        total_assists,
        total_headshots,
        total_revives,
        max_kill_dist,
        datetime.utcnow()
    )

# ==================================
# EXECUÇÃO PARALELA
# ==================================

resultados = []

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(buscar_stats, player, p_id)
        for player, p_id in player_ids.items()
    ]

    for future in as_completed(futures):
        r = future.result()
        if r:
            resultados.append(r)

# ==================================
# ATUALIZAR BANCO
# ==================================

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

sql = """
INSERT INTO ranking_squad
(nick, partidas, kr, vitorias, kills, dano_medio,
 assists, headshots, revives, kill_dist_max, atualizado_em)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (nick) DO UPDATE SET
partidas=EXCLUDED.partidas,
kr=EXCLUDED.kr,
vitorias=EXCLUDED.vitorias,
kills=EXCLUDED.kills,
dano_medio=EXCLUDED.dano_medio,
assists=EXCLUDED.assists,
headshots=EXCLUDED.headshots,
revives=EXCLUDED.revives,
kill_dist_max=EXCLUDED.kill_dist_max,
atualizado_em=EXCLUDED.atualizado_em
"""

cursor.executemany(sql, resultados)
conn.commit()

cursor.close()
conn.close()

print("💾 Banco atualizado!")
