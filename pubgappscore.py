import requests
import time

# 1. Sua API Key e Lista de Jogadores
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIxMTNkNWFkMC1lYzVhLTAxM2UtNWY0NC02NjA2MjJjNmQwYmIiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzcxMTMyMDEzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii0xY2NmM2YzMC1jYmRlLTQxMzctODM2Yy05ODY3ZDAxOWUwZDEifQ.kjXG3IJlpYJF0ybz9i7VCtGAGgBjCqds_qQuHsyhyu4"

jogadores = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

def buscar_todos_os_ids(lista_nicks, api_key):
    plataforma = "steam" # Altere para 'psn' ou 'xbox' se necessário
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json"
    }
    
    mapa_ids = {}
    
    # Dividir a lista em grupos de 10 (limite da API do PUBG)
    for i in range(0, len(lista_nicks), 10):
        grupo = lista_nicks[i:i+10]
        nicks_string = ",".join(grupo)
        
        url = f"https://api.pubg.com/shards/{plataforma}/players?filter[playerNames]={nicks_string}"
        
        print(f"Buscando grupo: {grupo}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            dados = response.json()
            for player in dados['data']:
                nick = player['attributes']['name']
                id_conta = player['id']
                mapa_ids[nick] = id_conta
        elif response.status_code == 429:
            print("Erro: Limite de requisições atingido. Aguardando 10 segundos...")
            time.sleep(10)
        else:
            print(f"Erro ao buscar nicks {grupo}: {response.status_code}")
            print(response.text)
            
    return mapa_ids

# --- EXECUÇÃO ---
resultados = buscar_todos_os_ids(jogadores, API_KEY)

print("\n" + "="*30)
print("IDs ENCONTRADOS:")
print("="*30)
for nick, id_conta in resultados.items():
    print(f"'{nick}': '{id_conta}',")
print("="*30)

# Verificação de quem faltou (caso o nick esteja escrito errado)
faltantes = set(jogadores) - set(resultados.keys())
if faltantes:
    print(f"\n⚠️ Não foi possível encontrar IDs para: {faltantes}")
    print("Verifique se o Nick está digitado exatamente como no jogo.")
