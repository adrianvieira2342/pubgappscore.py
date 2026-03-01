import os
import time
import requests
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed

DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("PUBG_API_KEY")
BASE_URL = "https://api.pubg.com/shards/steam"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

def fazer_requisicao(url):
    for _ in range(3):
        r = requests.get(url, headers=headers)
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 10))
            time.sleep(retry_after)
            continue
        return r
    return None

def jogador_tem_casual(player_name):
    res = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={player_name}")
    if not res or res.status_code != 200:
        return False

    data = res.json()["data"]
    if not data:
        return False

    p_id = data[0]["id"]

    res_player = fazer_requisicao(f"{BASE_URL}/players/{p_id}")
    if not res_player or res_player.status_code != 200:
        return False

    matches = res_player.json()["data"][0]["relationships"]["matches"]["data"]

    for match_ref in matches[:15]:
        match_id = match_ref["id"]
        res_match = fazer_requisicao(f"{BASE_URL}/matches/{match_id}")

        if not res_match or res_match.status_code != 200:
            continue

        included = res_match.json().get("included", [])
        participantes = [i for i in included if i["type"] == "participant"]

        bots = sum(
            1 for p in participantes
            if p["attributes"]["stats"].get("isBot", False)
        )

        if bots >= 70:
            print(f"🚫 Casual detectado: {player_name}")
            return True

    return False

# =========================
# EXECUÇÃO
# =========================

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("SELECT nick FROM ranking_squad")
players = [row[0] for row in cursor.fetchall()]

def processar_player(player):
    if jogador_tem_casual(player):
        cursor.execute("""
            UPDATE ranking_squad
            SET partidas=0,
                kr=0,
                vitorias=0,
                kills=0,
                dano_medio=0,
                assists=0,
                headshots=0,
                revives=0,
                kill_dist_max=0,
                atualizado_em=NOW()
            WHERE nick=%s
        """, (player,))
        conn.commit()
        print(f"❌ {player} zerado.")

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(processar_player, p) for p in players]
    for _ in as_completed(futures):
        pass

cursor.close()
conn.close()

print("✅ Filtro anti-casual finalizado.")
