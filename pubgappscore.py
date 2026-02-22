import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

# =========================================================
# 1. CONFIGURAÇÃO E REFRESH AUTOMÁTICO
# =========================================================
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

# Refresh a cada 3 minutos
count = st_autorefresh(interval=180000, key="ranking_refresh")

# =========================================================
# 2. MOTOR DE IMPORTAÇÃO (SUA LÓGICA DO VS CODE)
# =========================================================
def sync_data():
    try:
        API_KEY = st.secrets["PUBG_API_KEY"]
        DB_URL = st.secrets["DATABASE_URL"]
        engine = create_engine(DB_URL)
        
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

        # 1. Detectar Temporada Atual
        res_season = requests.get("https://api.pubg.com/shards/steam/seasons", headers=headers)
        if res_season.status_code != 200:
            return False
            
        current_season_id = next(s["id"] for s in res_season.json()["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Limpar Tabela para nova carga
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM ranking_squad"))

        # 3. Processar Jogadores (Loop do seu VS Code)
        for player in players:
            # Busca ID do Player
            res_p = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player}", headers=headers)
            if res_p.status_code == 200:
                p_data = res_p.json()
                if p_data.get("data"):
                    p_id = p_data["data"][0]["id"]
                    
                    # Busca Stats do Player
                    res_s = requests.get(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{current_season_id}", headers=headers)
                    if res_s.status_code == 200:
                        all_stats = res_s.json()["data"]["attributes"]["gameModeStats"]
                        stats = all_stats.get("squad", {}) # Mantendo 'squad' como no seu original
                        
                        partidas = stats.get("roundsPlayed", 0)
                        if partidas > 0:
                            # Sua lógica de cálculos original
                            kills = stats.get("kills", 0)
                            vitorias = stats.get("wins", 0)
                            assists = stats.get("assists", 0)
                            headshots = stats.get("headshotKills", 0)
                            revives = stats.get("revives", 0)
                            dano_total = stats.get("damageDealt", 0)
                            dist_max = stats.get("longestKill", 0.0)
                            
                            kr = round(kills / partidas, 2)
                            dano_medio = int(dano_total / partidas)
                            
                            # Salva no Banco
                            with engine.begin() as conn:
                                sql = text("""
                                    INSERT INTO ranking_squad 
                                    (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max) 
                                    VALUES (:nick, :partidas, :kr, :vitorias, :kills, :dano_medio, :assists, :headshots, :revives, :kill_dist_max)
                                """)
                                conn.execute(sql, {
                                    "nick": player, "partidas": partidas, "kr": kr, 
                                    "vitorias": vitorias, "kills": kills, "dano_medio": dano_medio,
                                    "assists": assists, "headshots": headshots, "revives": revives, "kill_dist_max": dist_max
                                })
            time.sleep(1) # Delay para evitar bloqueio da API
        return True
    except Exception as e:
        st.sidebar.error(f"Erro: {e}")
        return False

# Executa o motor do seu VS Code dentro do Streamlit
if count == 0 or st.sidebar.button("🔄 Forçar Atualização"):
    with st.spinner("Sincronizando com API PUBG..."):
        sync_data()

# =========================================================
# 3. INTERFACE (RANKING)
# =========================================================
def get_display_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        return pd.read_sql("SELECT * FROM ranking_squad", engine)
    except:
        return pd.DataFrame()

st.title("🎮 Ranking Squad - Temporada Atual")
df_bruto = get_display_data()

if not df_bruto.empty:
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    # Fórmulas de pontuação que você usa
    def aplicar_layout(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        df_local = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)
        st.dataframe(df_local, use_container_width=True)

    with tab1:
        # F_PRO: Baseada na sua lógica de score
        f = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*100*2)
        aplicar_layout(df_bruto.copy(), 'Score_PRO', f)
    
    with tab2:
        f = (df_bruto['assists']*10) + (df_bruto['revives']*5)
        aplicar_layout(df_bruto.copy(), 'Score_TEAM', f)
        
    with tab3:
        f = (df_bruto['kr']*50) + (df_bruto['headshots']*15)
        aplicar_layout(df_bruto.copy(), 'Score_ELITE', f)
else:
    st.info("Aguardando carregamento dos dados pela primeira vez...")
