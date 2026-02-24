import os
import requests
from datetime import datetime
from supabase import create_client

# ==========================
# CONFIGURAÇÕES
# ==========================

DATABASE_URL = os.environ.get("DATABASE_URL")
PUBG_API_KEY = os.environ.get("PUBG_API_KEY")

if not DATABASE_URL:
    raise Exception("DATABASE_URL não definida")

if not PUBG_API_KEY:
    raise Exception("PUBG_API_KEY não definida")

supabase = create_client(DATABASE_URL, DATABASE_URL)

# ==========================
# LISTA DE JOGADORES
# ==========================

players = {
    "Adrian-Wan": "account.58beb24ada7346408942d42dc64c7901",
    "MironoteuCool": "account.24b0600cbba342eab1546ae2881f50fa",
    "FabioEspeto": "account.d8ccad228a4a417dad9921616d6c6bcd",
    "Mamutag_Komander": "account.64c62d76cce74d0b99857a27975e350e",
    "Robson_Foz": "account.8142e6d837254ee1bca954b719692f38",
    "MEIRAA": "account.c3f37890e7534978abadaf4bae051390",
    "EL-LOCORJ": "account.94ab932726fc4c64a03eb9797429baa3",
    "SalaminhoKBD": "account.de093e200d3441a9b781a9717a017dd3",
    "nelio_ponto_dev": "account.ad39c88ddf754d33a3dfeadc117c47df",
    "CARNEIROOO": "account.8c0313f2148d47b7bffcde634f094445",
    "Kowalski_PR": "account.b25200afe120424a839eb56dd2bc49cb",
    "Zacouteguy": "account.a742bf1d5725467c91140cd0ed83c265",
    "Sidors": "account.60ab21fad4094824a32dc404420b914d",
    "Takato_Matsuki": "account.10d2403139bd4066a95dda1a3eefe1e8",
    "cmm01": "account.80cedebb935242469fdd177454a52e0e",
    "Petrala": "account.aadd1c378ff841219d853b4ad2646286",
    "Fumiga_BR": "account.1fa2a7c08c3e4d4786587b4575a071cb",
}

# ==========================
# CONFIG PUBG
# ==========================

REGION = "steam"
SEASON_ID = "division.bro.official.pc-2018-01"

headers = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

print("🚀 Iniciando atualização de todos os jogadores...")

# ==========================
# LOOP PRINCIPAL
# ==========================

for nick, player_id in players.items():

    print(f"\n🔎 Buscando dados de {nick}")

    url = f"https://api.pubg.com/shards/{REGION}/players/{player_id}/seasons/{SEASON_ID}/ranked"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Erro ao buscar {nick}: {response.status_code}")
        continue

    data = response.json()

    try:
        squad_stats = data["data"]["attributes"]["rankedGameModeStats"]["squad"]
    except KeyError:
        print(f"⚠️ {nick} sem dados de squad")
        continue

    points = squad_stats.get("currentRankPoint", 0)
    wins = squad_stats.get("wins", 0)

    print(f"📊 {nick} | Points: {points} | Wins: {wins}")

    registro = {
        "id": player_id,
        "name": nick,
        "rank": wins,
        "points": points,
        "updated_at": datetime.utcnow().isoformat()
    }

    supabase.table("ranking").upsert(registro).execute()

print("\n✅ Atualização finalizada com sucesso!")
