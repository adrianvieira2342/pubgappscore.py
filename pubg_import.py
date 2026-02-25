import os
import time
import requests
import psycopg2
from datetime import datetime

# ==========================
# 1. CONFIGURAÇÕES E AMBIENTE
# ==========================
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
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            print(" ! [Rate Limit] API ocupada. Aguardando 30 segundos...")
            time.sleep(30)
            continue
        return res
    return None

# ==========================
# 2. DETECTAR TEMPORADA ATUAL
# ==========================
print("🚀 Detectando temporada atual...")
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
current_season_id = ""

if res_season and res_season.status_code == 200:
    for s in res_season.json()["data"]:
        if s["attributes"]["isCurrentSeason"]:
            current_season_id = s["id"]
            break
else:
    print("❌ Erro crítico: Não foi possível obter a temporada.")
    exit()

print(f"✅ Temporada Ativa: {current_season_id}")

# ==========================
# 3. PROCESSAR JOGADORES
# ==========================
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    for i, player in enumerate(players, 1):
        print(f"\n[{i}/{len(players)}] Analisando: {player}")
        
        # Busca o ID do jogador pelo Nick
        res_p = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={player}")
        
        if not res_p or res_p.status_code != 200:
            print(f" > Pulando {player}: Falha na API")
            continue

        p_data = res_p.json()
        if not p_data.get("data"):
            continue

        p_id = p_data["data"][0]["id"]
        time.sleep(2) # Pausa para evitar 429

        # Busca estatísticas da temporada atual
        res_s = fazer_requisicao(f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}")
        
        if res_s and res_s.status_code == 200:
            all_stats = res_s.json()["data"]["attributes"]["gameModeStats"]
            stats = all_stats.get("squad", {})

            partidas = stats.get("roundsPlayed", 0)

            if partidas > 0:
                kills = stats.get("kills", 0)
                vitorias = stats.get("wins", 0)
                assists = stats.get("assists", 0)
                headshots = stats.get("headshotKills", 0)
                revives = stats.get("revives", 0)
                dano_total = stats.get("damageDealt", 0)
                dist_max = stats.get("longestKill", 0.0)

                # Cálculos de performance (Sua fórmula equilibrada)
                kr = round(kills / partidas, 2)
                dano_medio = int(dano_total / partidas)
                win_rate = (vitorias / partidas) * 100
                assists_pg = (assists / partidas)
                hs_pg = (headshots / partidas)
                revives_pg = (revives / partidas)

                score = round(
                    (kr * 40) + (dano_medio / 8) + (win_rate * 2) + 
                    (hs_pg * 15) + (assists_pg * 10) + (revives_pg * 5)
                , 2)

                # SQL para Supabase (PostgreSQL) com todas as colunas
                sql = """
                INSERT INTO ranking_squad 
                (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, score, atualizado_em) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    atualizado_em = EXCLUDED.atualizado_em
                """
                
                cursor.execute(sql, (
                    player, partidas, kr, vitorias, kills, dano_medio, 
                    assists, headshots, revives, dist_max, score, datetime.utcnow()
                ))
                conn.commit()
                print(f" > [SUCESSO] Score: {score}")
            else:
                print(f" > {player} sem partidas nesta season.")
        
        time.sleep(5) # Delay entre jogadores para garantir estabilidade

    cursor.close()
    conn.close()
    print("\n✅ --- ATUALIZAÇÃO FINALIZADA COM SUCESSO ---")

except Exception as e:
    print(f"💥 Erro fatal: {e}")
