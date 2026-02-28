import os
import time
import requests
import psycopg2
from datetime import datetime

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

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            print("⏳ Rate limit atingido, aguardando 10s...")
            time.sleep(10)
            continue
        return res
    return None

def dividir_lista(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]

print("🚀 Detectando temporada...")
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
current_season_id = next(
    (s["id"] for s in res_season.json()["data"]
     if s["attributes"]["isCurrentSeason"]),
    ""
)

print(f"📅 Temporada atual: {current_season_id}")

# ===============================
# BUSCAR IDS EM LOTE
# ===============================
print("🔎 Buscando IDs em lote...")

player_ids = {}

for grupo in dividir_lista(players, 10):
    nomes = ",".join(grupo)
    res = fazer_requisicao(
        f"{BASE_URL}/players?filter[playerNames]={nomes}"
    )
    if res and res.status_code == 200:
        for p in res.json()["data"]:
            player_ids[p["attributes"]["name"]] = p["id"]

print(f"✅ {len(player_ids)} IDs encontrados.")

# ===============================
# BUSCAR ESTATÍSTICAS
# ===============================

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    for player, p_id in player_ids.items():

        res_s = fazer_requisicao(
            f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}"
        )

        if not res_s or res_s.status_code != 200:
            continue

        stats = res_s.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
        partidas = stats.get("roundsPlayed", 0)

        if partidas == 0:
            continue

        kills = stats.get("kills", 0)
        vitorias = stats.get("wins", 0)
        assists = stats.get("assists", 0)
        headshots = stats.get("headshotKills", 0)
        revives = stats.get("revives", 0)
        dano_total = stats.get("damageDealt", 0)
        dist_max = stats.get("longestKill", 0.0)

        kr = round(kills / partidas, 2)
        dano_medio = int(dano_total / partidas)

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

        cursor.execute(sql, (
            player, partidas, kr, vitorias, kills,
            dano_medio, assists, headshots,
            revives, dist_max, datetime.utcnow()
        ))

        conn.commit()
        print(f"✅ {player} atualizado.")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"💥 Erro: {e}")
