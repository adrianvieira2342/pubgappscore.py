import os
import time
import requests
import mysql.connector
from dotenv import load_dotenv

# 1. CARREGAR VARIÁVEIS
load_dotenv()

API_KEY = os.getenv("PUBG_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

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

# =========================
# CONEXÃO BANCO DE DADOS
# =========================
try:
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )
    cursor = conn.cursor()
    print("Conexão estabelecida com sucesso.")
except mysql.connector.Error as e:
    print(f"Erro ao conectar: {e}")
    exit()

def fazer_requisicao(url):
    for tentativa in range(3):
        res = requests.get(url, headers=headers)
        if res.status_code == 429:
            print(" ! [Rate Limit] Aguardando 30s...")
            time.sleep(30)
            continue
        return res
    return None

# =========================
# 1. BUSCAR TEMPORADA E IDs (EM LOTE)
# =========================
print("Detectando temporada atual...")
res_season = fazer_requisicao(f"{BASE_URL}/seasons")
current_season_id = next(s["id"] for s in res_season.json()["data"] if s["attributes"]["isCurrentSeason"])

print(f"Buscando IDs de {len(players_list)} jogadores em uma única chamada...")
nicks_str = ",".join(players_list)
res_p = fazer_requisicao(f"{BASE_URL}/players?filter[playerNames]={nicks_str}")

if not res_p or res_p.status_code != 200:
    print("Erro ao buscar IDs dos jogadores.")
    exit()

# Criamos um dicionário { "Nick": "ID_da_API" }
player_map = {p["attributes"]["name"]: p["id"] for p in res_p.json()["data"]}

# =========================
# 2. PROCESSAR E ATUALIZAR (UPSERT)
# =========================
for nick, p_id in player_map.items():
    print(f"\nAtualizando estatísticas: {nick}")
    
    res_s = fazer_requisicao(f"{BASE_URL}/players/{p_id}/seasons/{current_season_id}")
    
    if res_s and res_s.status_code == 200:
        all_stats = res_s.json()["data"]["attributes"]["gameModeStats"]
        stats = all_stats.get("squad", {})
        partidas = stats.get("roundsPlayed", 0)

        if partidas > 0:
            # Recuperando todos os seus dados originais
            kills = stats.get("kills", 0)
            vitorias = stats.get("wins", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            dano_total = stats.get("damageDealt", 0)
            dist_max = stats.get("longestKill", 0.0)

            # Suas fórmulas de cálculo
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

            # SQL COM UPSERT (Evita apagar a tabela toda)
            sql = """
            INSERT INTO ranking_squad 
            (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max, score) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            partidas=%s, kr=%s, vitorias=%s, kills=%s, dano_medio=%s, 
            assists=%s, headshots=%s, revives=%s, kill_dist_max=%s, score=%s
            """
            
            valores = (
                nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, dist_max, score, # Dados para o Insert
                partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, dist_max, score        # Dados para o Update
            )
            
            cursor.execute(sql, valores)
            conn.commit()
            print(f" > [OK] Score: {score}")
        else:
            print(f" > {nick} sem partidas nesta season.")
    
    # Pausa de 6 segundos para manter os 10 RPM da API gratuita
    time.sleep(6)

print("\n--- PROCESSO CONCLUÍDO ---")
cursor.close()
conn.close()
