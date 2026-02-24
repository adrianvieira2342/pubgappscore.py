import os
import requests
import psycopg2
from datetime import datetime

# ==============================
# CONFIGURAÇÕES
# ==============================

DATABASE_URL = os.getenv("DATABASE_URL")
PUBG_API_KEY = os.getenv("PUBG_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

PLAYERS = [
    "Nick1",
    "Nick2",
    "Nick3"
]

# ==============================
# FUNÇÃO PARA BUSCAR DADOS
# ==============================

def buscar_dados_jogador(nick):
    url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Erro ao buscar {nick}: {response.text}")
        return None
    
    data = response.json()
    
    try:
        stats = data["data"][0]["attributes"]["stats"]["all"]["squad"]
        
        partidas = stats.get("roundsPlayed", 0)
        kills = stats.get("kills", 0)
        dano_medio = stats.get("damageDealt", 0) / partidas if partidas > 0 else 0
        vitorias = stats.get("wins", 0)
        kr = kills / partidas if partidas > 0 else 0
        
        score = (kills * 2) + (vitorias * 10) + dano_medio
        
        return {
            "nick": nick,
            "partidas": partidas,
            "kills": kills,
            "dano_medio": round(dano_medio, 2),
            "vitorias": vitorias,
            "kr": round(kr, 2),
            "score": round(score, 2),
            "atualizado_em": datetime.utcnow()
        }
        
    except Exception as e:
        print(f"Erro processando dados de {nick}: {e}")
        return None


# ==============================
# ATUALIZAR BANCO
# ==============================

def atualizar_banco(dados):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    for jogador in dados:
        cur.execute("""
            INSERT INTO ranking_squad 
            (nick, partidas, kr, vitorias, kills, dano_medio, score, atualizado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (nick)
            DO UPDATE SET
                partidas = EXCLUDED.partidas,
                kr = EXCLUDED.kr,
                vitorias = EXCLUDED.vitorias,
                kills = EXCLUDED.kills,
                dano_medio = EXCLUDED.dano_medio,
                score = EXCLUDED.score,
                atualizado_em = EXCLUDED.atualizado_em
        """, (
            jogador["nick"],
            jogador["partidas"],
            jogador["kr"],
            jogador["vitorias"],
            jogador["kills"],
            jogador["dano_medio"],
            jogador["score"],
            jogador["atualizado_em"]
        ))
    
    conn.commit()
    cur.close()
    conn.close()


# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================

if __name__ == "__main__":
    
    print("Iniciando atualização PUBG...")
    
    dados_jogadores = []
    
    for nick in PLAYERS:
        dados = buscar_dados_jogador(nick)
        if dados:
            dados_jogadores.append(dados)
    
    if dados_jogadores:
        atualizar_banco(dados_jogadores)
        print("Atualização concluída com sucesso!")
    else:
        print("Nenhum dado atualizado.")
