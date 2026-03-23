# pubg_import.py
import os
import time
import requests
import psycopg2
from datetime import datetime, date, timedelta
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

def get_segunda_feira():
    hoje = date.today()
    return hoje - timedelta(days=hoje.weekday())

inicio_total = time.time()
print("🚀 Detectando temporada...")

res_season = fazer_requisicao(f"{BASE_URL}/seasons")
current_season_id = next(
    (s["id"] for s in res_season.json()["data"]
     if s["attributes"]["isCurrentSeason"]),
    ""
)

print(f"📅 Temporada atual: {current_season_id}")

print("🔎 Buscando IDs e última partida em lote...")
player_ids = {}
player_last_match = {}

for grupo in dividir_lista(players, 10):
    nomes = ",".join(grupo)
    res = fazer_requisicao(
        f"{BASE_URL}/players?filter[playerNames]={nomes}"
    )
    if res and res.status_code == 200:
        for p in res.json()["data"]:
            nick = p["attributes"]["name"]
            player_ids[nick] = p["id"]
            matches = p["relationships"]["matches"]["data"]
            if matches:
                player_last_match[nick] = matches[0]["id"]

print(f"✅ {len(player_ids)} IDs encontrados.")

print("📅 Buscando data da última partida...")
player_updated_at = {}

def buscar_data_partida(nick, match_id):
    res = fazer_requisicao(f"{BASE_URL}/matches/{match_id}")
    if not res or res.status_code != 200:
        return nick, None
    try:
        created_at = res.json()["data"]["attributes"]["createdAt"]
        return nick, datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return nick, None

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(buscar_data_partida, nick, match_id)
        for nick, match_id in player_last_match.items()
    ]
    for future in as_completed(futures):
        nick, data = future.result()
        player_updated_at[nick] = data
        print(f"📅 {nick} | última partida: {data}")

def buscar_stats(player, p_id):
    url = f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}"
    res = fazer_requisicao(url)

    if not res or res.status_code != 200:
        return None

    stats = res.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
    partidas = stats.get("roundsPlayed", 0)

    if partidas == 0:
        return None

    kills = stats.get("kills", 0)
    vitorias = stats.get("wins", 0)
    assists = stats.get("assists", 0)
    headshots = stats.get("headshotKills", 0)
    revives = stats.get("revives", 0)
    dano_total = stats.get("damageDealt", 0)
    dist_max = stats.get("longestKill", 0.0)
    top10 = stats.get("top10s", 0)

    kr = round(kills / partidas, 2)
    dano_medio = int(dano_total / partidas)

    ultima_partida = player_updated_at.get(player, None)

    print(f"⚡ {player} processado")

    return (
        player, partidas, kr, vitorias, kills,
        dano_medio, assists, headshots,
        revives, dist_max, top10, datetime.utcnow(), ultima_partida
    )

print("⚡ Buscando estatísticas em paralelo...")

resultados = []

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(buscar_stats, player, p_id)
        for player, p_id in player_ids.items()
    ]

    for future in as_completed(futures):
        resultado = future.result()
        if resultado:
            resultados.append(resultado)

print(f"✅ {len(resultados)} jogadores com stats válidas.")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # ===============================
    # UPDATE RANKING_SQUAD
    # ===============================
    sql = """
    INSERT INTO ranking_squad
    (nick, partidas, kr, vitorias, kills, dano_medio,
     assists, headshots, revives, kill_dist_max, top10, atualizado_em, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    top10=EXCLUDED.top10,
    atualizado_em=EXCLUDED.atualizado_em,
    updated_at=EXCLUDED.updated_at
    """
    cursor.executemany(sql, resultados)

    # ===============================
    # SNAPSHOT SEMANAL (delta)
    # ===============================
    semana_atual = get_segunda_feira()
    semana_anterior = semana_atual - timedelta(weeks=1)
    print(f"📊 Salvando snapshot semanal para semana de {semana_atual}...")

    # Busca snapshot da semana anterior para calcular delta
    cursor.execute(
        "SELECT nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, top10 FROM ranking_semanal WHERE semana = %s",
        (semana_anterior,)
    )
    rows_anteriores = cursor.fetchall()
    snapshot_anterior = {
        row[0]: row[1:] for row in rows_anteriores
    }

    cols_delta = ["partidas", "vitorias", "kills", "assists", "headshots", "revives", "top10"]
    idx = {"partidas": 0, "kr": 1, "vitorias": 2, "kills": 3, "dano_medio": 4,
           "assists": 5, "headshots": 6, "revives": 7, "kill_dist_max": 8, "top10": 9}

    sql_semanal = """
    INSERT INTO ranking_semanal
    (nick, semana, partidas, kr, vitorias, kills, dano_medio,
     assists, headshots, revives, kill_dist_max, top10, atualizado_em)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (nick, semana) DO UPDATE SET
    partidas=EXCLUDED.partidas,
    kr=EXCLUDED.kr,
    vitorias=EXCLUDED.vitorias,
    kills=EXCLUDED.kills,
    dano_medio=EXCLUDED.dano_medio,
    assists=EXCLUDED.assists,
    headshots=EXCLUDED.headshots,
    revives=EXCLUDED.revives,
    kill_dist_max=EXCLUDED.kill_dist_max,
    top10=EXCLUDED.top10,
    atualizado_em=EXCLUDED.atualizado_em
    """

    resultados_semanal = []
    for r in resultados:
        nick = r[0]
        ant = snapshot_anterior.get(nick)
        if ant:
            # Salva apenas o delta em relação à semana anterior
            partidas  = max(0, r[1]  - ant[idx["partidas"]])
            vitorias  = max(0, r[3]  - ant[idx["vitorias"]])
            kills     = max(0, r[4]  - ant[idx["kills"]])
            assists   = max(0, r[6]  - ant[idx["assists"]])
            headshots = max(0, r[7]  - ant[idx["headshots"]])
            revives   = max(0, r[8]  - ant[idx["revives"]])
            top10     = max(0, r[10] - ant[idx["top10"]])
            dano_medio = r[5]
            kr         = round(kills / partidas, 2) if partidas > 0 else 0.0
            kill_dist_max = r[9]
        else:
            # Primeira semana: salva zerado para não distorcer
            partidas, kr, vitorias, kills = 0, 0.0, 0, 0
            dano_medio, assists, headshots = 0, 0, 0
            revives, kill_dist_max, top10 = 0, 0.0, 0

        resultados_semanal.append((
            nick, semana_atual, partidas, kr, vitorias, kills,
            dano_medio, assists, headshots, revives, kill_dist_max, top10, r[11]
        ))

    cursor.executemany(sql_semanal, resultados_semanal)
    conn.commit()

    cursor.close()
    conn.close()

    print("💾 Banco atualizado com sucesso!")

except Exception as e:
    print(f"💥 Erro no banco: {e}")

fim_total = time.time()
print(f"⏱ Tempo total: {round(fim_total - inicio_total, 2)} segundos")
