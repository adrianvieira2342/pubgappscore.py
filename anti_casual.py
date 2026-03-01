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

# ===============================
# REQUISIÇÃO COM CONTROLE
# ===============================

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)

        if res.status_code == 429:
            retry_after = int(res.headers.get("Retry-After", 10))
            print(f"⏳ Rate limit. Aguardando {retry_after}s...")
            time.sleep(retry_after)
            continue

        return res

    return None

def dividir_lista(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]

# ===============================
# INÍCIO
# ===============================

inicio_total = time.time()
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
# FUNÇÃO PRINCIPAL
# ===============================

def buscar_stats(player, p_id):
    print(f"🔎 Processando {player}")

    res_player = fazer_requisicao(f"{BASE_URL}/players/{p_id}")
    if not res_player or res_player.status_code != 200:
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

    for match in matches:

        match_id = match["id"]
        res_match = fazer_requisicao(f"{BASE_URL}/matches/{match_id}")
        if not res_match or res_match.status_code != 200:
            continue

        data = res_match.json()
        attributes = data["data"]["attributes"]

        # Ignorar fora da temporada
        if attributes.get("seasonId") != current_season_id:
            continue

        # Ignorar se não for squad
        if attributes.get("gameMode") != "squad":
            continue

        bots = 0
        humanos = 0
        stats_player = None

        for included in data["included"]:
            if included["type"] == "participant":
                stats = included["attributes"]["stats"]

                if stats.get("playerId") == "ai":
                    bots += 1
                else:
                    humanos += 1

                if stats.get("playerId") == p_id:
                    stats_player = stats

        # 🔥 Detectar Casual (80+ bots)
        if bots >= 80:
            print(f"❌ Casual detectado ({bots} bots) - ignorado")
            continue

        if not stats_player:
            continue

        partidas_validas += 1
        total_kills += stats_player.get("kills", 0)
        total_assists += stats_player.get("assists", 0)
        total_headshots += stats_player.get("headshotKills", 0)
        total_revives += stats_player.get("revives", 0)
        total_damage += stats_player.get("damageDealt", 0)

        if stats_player.get("winPlace", 100) == 1:
            total_wins += 1

        longest = stats_player.get("longestKill", 0)
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

# ===============================
# EXECUÇÃO PARALELA
# ===============================

print("⚡ Buscando estatísticas em paralelo...")

resultados = []

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(buscar_stats, player, p_id)
        for player, p_id in player_ids.items()
    ]

    for future in as_completed(futures):
        resultado = future.result()
        if resultado:
            resultados.append(resultado)

print(f"✅ {len(resultados)} jogadores com stats válidas.")

# ===============================
# ATUALIZA BANCO
# ===============================

try:
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

    print("💾 Banco atualizado com sucesso!")

except Exception as e:
    print(f"💥 Erro no banco: {e}")

fim_total = time.time()
print(f"⏱ Tempo total: {round(fim_total - inicio_total, 2)} segundos")
