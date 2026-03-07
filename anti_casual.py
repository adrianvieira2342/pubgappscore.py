import pandas as pd
import requests
from sqlalchemy import create_engine
import time

DB_URL = "SUA_DATABASE_URL_AQUI"
API_KEY = "SUA_API_KEY_PUBG_AQUI"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/vnd.api+json"}

def get_engine():
    return create_engine(DB_URL)

def carregar_players_ativos():
    engine = get_engine()
    return pd.read_sql("SELECT nick, account_id FROM jogadores_monitorados WHERE status = 'ativo'", engine)

def processar_bots():
    df_players = carregar_players_ativos()
    lista_bots = []

    for _, row in df_players.iterrows():
        nick = row['nick']
        acc_id = row['account_id']
        
        if not acc_id: continue

        print(f"Analisando partidas casuais de: {nick}...")
        
        # Busca as últimas partidas
        url = f"https://api.pubg.com/shards/steam/players/{acc_id}"
        res = requests.get(url, headers=HEADERS)
        
        if res.status_code == 200:
            matches = res.json()['data']['relationships']['matches']['data']
            
            stats_bot = {'nick': nick, 'partidas': 0, 'kills': 0, 'vitorias': 0, 'assists': 0, 'headshots': 0, 'revives': 0}
            
            for m in matches[:10]: # Analisa as últimas 10 partidas para ver se são casuais
                m_id = m['id']
                res_m = requests.get(f"https://api.pubg.com/shards/steam/matches/{m_id}", headers=HEADERS)
                
                if res_m.status_code == 200:
                    m_data = res_m.json()
                    # Verifica se é Casual Mode (Baseado na sua lógica de identificação de bots)
                    if m_data['data']['attributes']['matchType'] == 'aiPlayerMatch':
                        stats_bot['partidas'] += 1
                        # Aqui você extrai os stats do player dentro dessa partida específica
                        # ... (Sua lógica existente de extração de stats da match) ...
            
            # Cálculo de penalidade (Score baixo = alta penalidade)
            stats_bot['score'] = (stats_bot['kills'] * -5) + (stats_bot['vitorias'] * -20)
            lista_bots.append(stats_bot)
        
        time.sleep(1)

    if lista_bots:
        df_bots = pd.DataFrame(lista_bots)
        df_bots.to_sql('ranking_bot', get_engine(), if_exists='replace', index=False)
        print("Tabela de penalidades de bots atualizada!")

if __name__ == "__main__":
    processar_bots()
