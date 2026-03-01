import requests
import time

API_KEY = "SUA_CHAVE_AQUI"
PLAYER_ID = "account.64c62d76cce74d0b99857a27975e350e"
SHARD = "steam"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

def get(url):
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    print("Erro:", r.status_code)
    return None

print("🔎 Buscando matches do player...")

player_data = get(f"https://api.pubg.com/shards/{SHARD}/players/{PLAYER_ID}")

matches = player_data["data"]["relationships"]["matches"]["data"]

print("Total matches retornadas:", len(matches))

casual_detectado = 0

for m in matches:
    match_id = m["id"]
    match_data = get(f"https://api.pubg.com/shards/{SHARD}/matches/{match_id}")
    if not match_data:
        continue

    attr = match_data["data"]["attributes"]

    participants = [x for x in match_data["included"] if x["type"] == "participant"]

    humanos = sum(
        1 for p in participants
        if p["attributes"]["stats"].get("playerId", "").startswith("account.")
    )

    bots = len(participants) - humanos

    print(f"Match: {match_id}")
    print("Map:", attr["mapName"])
    print("GameMode:", attr["gameMode"])
    print("Humanos:", humanos)
    print("Bots:", bots)
    print("-" * 30)

    if attr["mapName"] == "Baltic_Main" and humanos <= 12:
        casual_detectado += 1

    time.sleep(1)

print("\nTotal Casual detectado:", casual_detectado)
