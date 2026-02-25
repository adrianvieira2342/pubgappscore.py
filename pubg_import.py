import os
import requests
import psycopg2
import time
from datetime import datetime

# ==========================
# CONFIGURAÇÕES E AMBIENTE
# ==========================
DATABASE_URL = os.environ.get("DATABASE_URL")
PUBG_API_KEY = os.environ.get("PUBG_API_KEY")
REGION = "steam"

# Alterado para 'lifetime' para garantir que os dados não venham zerados
SEASON_ID = "lifetime" 

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

def get_stats():
    try:
        # Conexão com o Supabase via DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        headers = {
            "Authorization": f"Bearer {PUBG_API_KEY}", 
            "Accept": "application/vnd.api+json"
        }

        print(f"🚀 Iniciando busca em modo: {SEASON_ID}")

        for nick, p_id in players.items():
            # Delay de 6 segundos para respeitar o limite de 10 requisições/minuto da API
            time.sleep(6) 
            
            # URL específica para o modo lifetime (Squad Normal)
            url = f"https://api.pubg.com/shards/{REGION}/players/{p_id}/seasons/lifetime"
            res = requests.get(url, headers=headers)
            
            if res.status_code != 200:
                print(f"❌ Erro {res.status_code} em {nick}")
                continue

            data = res.json()
            all_modes = data["data"]["attributes"]["gameModeStats"]

            # Busca dados de Squad TPP, se estiver zerado tenta Squad FPP
            stats = all_modes.get("squad", {})
            if stats.get("roundsPlayed", 0) == 0:
                stats = all_modes.get("squad-fpp", {})

            wins = stats.get("wins", 0)
            kills = stats.get("kills", 0)
            
            # Como o modo Normal não tem RankPoints, usamos Kills para popular a coluna 'score'
            score = kills 

            print(f"📊 {nick} -> Wins: {wins}, Kills: {kills} (Partidas Totais: {stats.get('roundsPlayed', 0)})")

            # Comando para inserir ou atualizar baseado no NICK
            cursor.execute("""
                INSERT INTO ranking_squad (nick, vitorias, score, atualizado_em)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (nick)
                DO UPDATE SET
                    vitorias = EXCLUDED.vitorias,
                    score = EXCLUDED.score,
                    atualizado_em = EXCLUDED.atualizado_em
            """, (nick, wins, score, datetime.utcnow()))
            
            conn.commit()

        cursor.close()
        conn.close()
        print("✅ Ranking atualizado com sucesso no Supabase!")

    except Exception as e:
        print(f"💥 Erro fatal: {e}")

if __name__ == "__main__":
    get_stats()
