import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta

# =========================================================
# 1. CONFIGURAÇÃO
# =========================================================
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

# Refresh visual a cada 5 minutos (mais leve)
st_autorefresh(interval=300000, key="ranking_refresh")

# =========================================================
# 2. MOTOR DE IMPORTAÇÃO (ESTRATÉGIA DE CACHE)
# =========================================================

def sync_data():
    """Roda a sincronização pesada apenas quando necessário"""
    API_KEY = st.secrets["PUBG_API_KEY"]
    DB_URL = st.secrets["DATABASE_URL"]
    engine = create_engine(DB_URL)
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/vnd.api+json"}

    def fazer_requisicao(url):
        for _ in range(3):
            res = requests.get(url, headers=headers)
            if res.status_code == 429:
                time.sleep(30)
                continue
            return res
        return None

    players = [
        "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
        "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
        "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
        "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
    ]

    try:
        res_season = fazer_requisicao("https://api.pubg.com/shards/steam/seasons")
        if not res_season: return
        current_season_id = next(s["id"] for s in res_season.json()["data"] if s["attributes"]["isCurrentSeason"])

        # Em vez de DELETE, vamos usar UPDATE/INSERT
        for player in players:
            res_p = fazer_requisicao(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player}")
            if res_p and res_p.status_code == 200:
                p_data = res_p.json()
                if p_data.get("data"):
                    p_id = p_data["data"][0]["id"]
                    time.sleep(1.5)
                    
                    res_s = fazer_requisicao(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{current_season_id}")
                    if res_s and res_s.status_code == 200:
                        stats = res_s.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
                        partidas = stats.get("roundsPlayed", 0)
                        
                        if partidas > 0:
                            # Upsert (Insere ou Atualiza) para o site nunca ficar em branco
                            with engine.begin() as conn:
                                sql = text("""
                                    INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max)
                                    VALUES (:n, :p, :kr, :v, :k, :dm, :a, :h, :r, :dist)
                                    ON CONFLICT (nick) DO UPDATE SET
                                    partidas = EXCLUDED.partidas, kr = EXCLUDED.kr, vitorias = EXCLUDED.vitorias,
                                    kills = EXCLUDED.kills, dano_medio = EXCLUDED.dano_medio, assists = EXCLUDED.assists,
                                    headshots = EXCLUDED.headshots, revives = EXCLUDED.revives, kill_dist_max = EXCLUDED.kill_dist_max
                                """)
                                conn.execute(sql, {
                                    "n": player, "p": partidas, "kr": round(stats.get('kills',0)/partidas, 2),
                                    "v": stats.get('wins',0), "k": stats.get('kills',0),
                                    "dm": int(stats.get('damageDealt',0)/partidas), "a": stats.get('assists',0),
                                    "h": stats.get('headshotKills',0), "r": stats.get('revives',0), "dist": stats.get('longestKill',0)
                                })
            time.sleep(1.5)
        return True
    except Exception as e:
        print(f"Erro: {e}")
        return False

# =========================================================
# 3. INTERFACE E LOGICA VISUAL (RESTAURADA)
# =========================================================

def get_data():
    engine = create_engine(st.secrets["DATABASE_URL"])
    return pd.read_sql("SELECT * FROM ranking_squad", engine)

# Executa o sync apenas se o usuário clicar ou se o banco estiver vazio
if st.sidebar.button("🔄 Atualizar Dados da API"):
    with st.spinner("Sincronizando com PUBG... (Aguarde 1-2 min)"):
        sync_data()
        st.cache_data.clear()

df_bruto = get_data()

st.title("🎮 Ranking Squad - Season 40")

if not df_bruto.empty:
    # --- Fórmulas e Tabs ---
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def processar_v(df, col_score):
        df = df.sort_values(col_score, ascending=False).reset_index(drop=True)
        df['Pos'] = range(1, len(df) + 1)
        
        # Lógica de Emojis e Zonas
        df['Classificação'] = df['Pos'].apply(lambda x: "Elite Zone" if x <= 3 else ("Cocô Zone" if x > len(df)-3 else "Medíocre Zone"))
        df['nick'] = df.apply(lambda x: f"💀 {x['nick']}" if x['Pos'] <= 3 else (f"💩 {x['nick']}" if x['Pos'] > len(df)-3 else f"👤 {x['nick']}"), axis=1)
        
        return df[['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', col_score]]

    with tab1:
        df_bruto['Score_PRO'] = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
        res = processar_v(df_bruto.copy(), 'Score_PRO')
        
        # Cards Top 3
        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 1º", res.iloc[0]['nick'], f"{res.iloc[0]['Score_PRO']} pts")
        if len(res)>1: c2.metric("🥈 2º", res.iloc[1]['nick'], f"{res.iloc[1]['Score_PRO']} pts")
        if len(res)>2: c3.metric("🥉 3º", res.iloc[2]['nick'], f"{res.iloc[2]['Score_PRO']} pts")
        
        st.dataframe(res.style.apply(lambda x: ['background-color: #004d00' if x.Classificação == "Elite Zone" else ('background-color: #4d2600' if x.Classificação == "Cocô Zone" else '') for _ in x], axis=1), use_container_width=True, hide_index=True)

    with tab2:
        df_bruto['Score_TEAM'] = (df_bruto['vitorias']*10) + (df_bruto['revives']*10) + (df_bruto['assists']*5)
        st.dataframe(processar_v(df_bruto.copy(), 'Score_TEAM'), use_container_width=True, hide_index=True)

    with tab3:
        df_bruto['Score_ELITE'] = (df_bruto['kr']*50) + (df_bruto['headshots']*5)
        st.dataframe(processar_v(df_bruto.copy(), 'Score_ELITE'), use_container_width=True, hide_index=True)

else:
    st.warning("Clique no botão lateral para carregar os dados pela primeira vez.")
