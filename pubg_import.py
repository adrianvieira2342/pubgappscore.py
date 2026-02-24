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
SEASON_ID = "division.bro.official.pc-40"
REGION = "steam"

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

def atualizar_ranking():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        headers = {"Authorization": f"Bearer {PUBG_API_KEY}", "Accept": "application/vnd.api+json"}

        for nick, player_id in players.items():
            print(f"🔎 Buscando {nick}...")
            url = f"https://api.pubg.com/shards/{REGION}/players/{player_id}/seasons/{SEASON_ID}"
            
            # Pausa obrigatória de 6 segundos entre cada player para evitar o erro 429 (limite de 10 por minuto)
            time.sleep(6) 
            
            res = requests.get(url, headers=headers)
            
            if res.status_code != 200:
                print(f"❌ Erro {res.status_code} em {nick}")
                continue

            data = res.json()
            try:
                # Tenta buscar Squad TPP Normal
                stats = data["data"]["attributes"]["gameModeStats"].get("squad", {})
                
                wins = stats.get("wins", 0)
                kills = stats.get("kills", 0)
                damage = stats.get("damageDealt", 0)
                
                # Para o ranking não ficar com score 0, vamos usar Kills ou uma soma de performance
                # Se quiser manter o 'score' no banco, vamos usar o Damage ou Kills como base:
                score_fake = kills  

                print(f"📊 {nick} -> Wins: {wins} | Kills: {kills} | Damage: {int(damage)}")

                cursor.execute("""
                    INSERT INTO ranking_squad (nick, vitorias, score, atualizado_em)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (nick)
                    DO UPDATE SET
                        vitorias = EXCLUDED.vitorias,
                        score = EXCLUDED.score,
                        atualizado_em = EXCLUDED.atualizado_em
                """, (nick, wins, score_fake, datetime.utcnow()))
                
                conn.commit()

            except KeyError:
                print(f"⚠️ {nick} sem dados nesta temporada.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"💥 Erro: {e}")

if __name__ == "__main__":
    atualizar_ranking()
