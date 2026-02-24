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

# Criar conexão Supabase
supabase = create_client(DATABASE_URL, DATABASE_URL)

# ==========================
# CONFIG PUBG
# ==========================

SEASON_ID = "division.bro.official.pc-2018-01"  # ajuste se necessário
REGION = "steam"
PLAYER_ID = "ACCOUNT_ID_DO_JOGADOR_AQUI"  # troque pelo player id real

url = f"https://api.pubg.com/shards/{REGION}/players/{PLAYER_ID}/seasons/{SEASON_ID}/ranked"

headers = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

print("🔎 Buscando dados da PUBG...")

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Erro PUBG API: {response.status_code} - {response.text}")

data = response.json()

print("✅ Dados recebidos da API")

# ==========================
# EXTRAIR DADOS (exemplo squad)
# ==========================

try:
    squad_stats = data["data"]["attributes"]["rankedGameModeStats"]["squad"]
except KeyError:
    raise Exception("Não foi possível encontrar estatísticas de squad")

rank = squad_stats.get("currentRankPoint", 0)
wins = squad_stats.get("wins", 0)

print(f"📊 Rank Points: {rank}")
print(f"🏆 Wins: {wins}")

# ==========================
# SALVAR NO SUPABASE (UPSERT)
# ==========================

registro = {
    "id": PLAYER_ID,
    "name": "NomeDoJogador",
    "rank": wins,
    "points": rank,
    "updated_at": datetime.utcnow().isoformat()
}

print("💾 Salvando no banco...")

result = supabase.table("ranking").upsert(registro).execute()

print("✅ Banco atualizado com sucesso!")
print(result)
