import os
import time
import requests
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

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

# =============================
# FUNÇÃO DE REQUISIÇÃO COM RETRY
# =============================
def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            print("⏳ Rate limit atingido. Aguardando 30s...")
            time.sleep(30)
            continue
        return res
    return None

print("🚀 Detectando temporada...")

res_season = fazer_requisicao(f"{BASE_URL}/seasons")

if not res_season or res_season.status_code != 200:
    print("❌ Erro ao buscar temporadas.")
    exit()

current_season_id = next(
    (s["id"] for s in res_season.json()["data"]
     if s["attributes"]["isCurrentSeason"]),
    ""
)

if not current_season_id:
    print("❌ Temporada atual não encontrada.")
    exit()

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    for player in players:
        time.sleep(2)

        res_p = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={player}")
        if not res_p or res_p.status_code != 200:
            print(f"⚠️ Não foi possível buscar jogador {player}")
            continue

        p_id = res_p.json()["data"][0]["id"]

        time.sleep(2)
        res_s = fazer_requisicao(f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}")

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

                # =============================
                # HORÁRIO EM BRASÍLIA
                # =============================
                brasilia_tz = ZoneInfo("America/Sao_Paulo")
                atualizado_em = datetime.now(brasilia_tz)

                sql = """
                INSERT INTO ranking_squad (
                    nick, partidas, kr, vitorias, kills, dano_medio,
                    assists, headshots, revives, kill_dist_max, atualizado_em
                ) 
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
                    atualizado_em = EXCLUDED.atualizado_em
                """

                cursor.execute(sql, (
                    player, partidas, kr, vitorias, kills,
                    dano_medio, assists, headshots,
                    revives, dist_max, atualizado_em
                ))

                conn.commit()
                print(f"✅ {player} atualizado às {atualizado_em.strftime('%d/%m/%Y %H:%M:%S')} (Brasília)")

    cursor.close()
    conn.close()
    print("🏁 Atualização concluída com sucesso.")

except Exception as e:
    print(f"💥 Erro: {e}")
