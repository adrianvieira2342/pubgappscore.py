import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

# =========================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

# Refresh visual a cada 5 minutos
st_autorefresh(interval=300000, key="ranking_refresh")

# Estilização CSS para ajustar o layout
st.markdown("""
    <style>
    .main > div { padding-top: 2rem; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. MOTOR DE IMPORTAÇÃO (LÓGICA VS CODE + RATE LIMIT)
# =========================================================
def sync_data():
    API_KEY = st.secrets["PUBG_API_KEY"]
    DB_URL = st.secrets["DATABASE_URL"]
    engine = create_engine(DB_URL)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/vnd.api+json"}

    players = [
        "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
        "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
        "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
        "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
    ]

    def fazer_requisicao(url):
        for _ in range(3):
            res = requests.get(url, headers=headers)
            if res.status_code == 429:
                time.sleep(30)
                continue
            return res
        return None

    try:
        # 1. Buscar Temporada
        res_s = fazer_requisicao("https://api.pubg.com/shards/steam/seasons")
        season_id = next(s["id"] for s in res_s.json()["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Loop de Jogadores (Sem apagar o banco antes!)
        progresso = st.sidebar.progress(0)
        for i, p_name in enumerate(players):
            progresso.progress((i + 1) / len(players))
            
            res_p = fazer_requisicao(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={p_name}")
            if res_p and res_p.status_code == 200:
                p_id = res_p.json()["data"][0]["id"]
                time.sleep(1.5)
                
                res_stats = fazer_requisicao(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{season_id}")
                if res_stats and res_stats.status_code == 200:
                    stats = res_stats.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
                    rounds = stats.get("roundsPlayed", 0)
                    
                    if rounds > 0:
                        # UPSERT: Atualiza se já existir o nick, senão insere
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
                                "n": p_name, "p": rounds, "kr": round(stats.get('kills',0)/rounds, 2),
                                "v": stats.get('wins',0), "k": stats.get('kills',0),
                                "dm": int(stats.get('damageDealt',0)/rounds), "a": stats.get('assists',0),
                                "h": stats.get('headshotKills',0), "r": stats.get('revives',0), "dist": stats.get('longestKill',0)
                            })
            time.sleep(2.0)
        return True
    except Exception as e:
        st.sidebar.error(f"Erro: {e}")
        return False

# Botão de Sincronização
if st.sidebar.button("🔄 Atualizar Dados da API"):
    with st.spinner("Sincronizando com a API... Isso leva ~2 min."):
        sync_data()
        st.rerun()

# =========================================================
# 3. INTERFACE VISUAL (LAYOUT CORRIGIDO)
# =========================================================
def get_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        return pd.read_sql("SELECT * FROM ranking_squad", engine)
    except: return pd.DataFrame()

df_bruto = get_data()

st.title("🎮 Ranking Squad - Season 40")
st.markdown("---")

if not df_bruto.empty:
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def exibir_ranking(df, col_score, formula):
        df[col_score] = formula.round(2)
        df = df.sort_values(col_score, ascending=False).reset_index(drop=True)
        
        # Rankings e Emojis
        df['Pos'] = range(1, len(df) + 1)
        df['Classificação'] = df['Pos'].apply(lambda x: "Elite Zone" if x <= 3 else ("Cocô Zone" if x > len(df)-3 else "Medíocre Zone"))
        df['nick'] = df.apply(lambda x: f"💀 {x['nick']}" if x['Pos'] <= 3 else (f"💩 {x['nick']}" if x['Pos'] > len(df)-3 else f"👤 {x['nick']}"), axis=1)

        # TOP 3 CARDS
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("🥇 1º Lugar", df.iloc[0]['nick'], f"{df.iloc[0][col_score]} pts")
        if len(df) > 1:
            with c2: st.metric("🥈 2º Lugar", df.iloc[1]['nick'], f"{df.iloc[1][col_score]} pts")
        if len(df) > 2:
            with c3: st.metric("🥉 3º Lugar", df.iloc[2]['nick'], f"{df.iloc[2][col_score]} pts")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # TABELA COM CORES FIXAS
        def style_row(row):
            if "Elite" in row.Classificação: return ['background-color: #004d00; color: white'] * len(row)
            if "Cocô" in row.Classificação: return ['background-color: #4d2600; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(df.style.apply(style_row, axis=1).format(precision=2), use_container_width=True, hide_index=True)

    with tab1:
        f_pro = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
        exibir_ranking(df_bruto.copy(), 'Score_PRO', f_pro)
    with tab2:
        f_team = (df_bruto['vitorias']*10) + (df_bruto['revives']*10) + (df_bruto['assists']*5)
        exibir_ranking(df_bruto.copy(), 'Score_TEAM', f_team)
    with tab3:
        f_elite = (df_bruto['kr']*50) + (df_bruto['headshots']*5)
        exibir_ranking(df_bruto.copy(), 'Score_ELITE', f_elite)

else:
    st.info("O banco de dados está vazio. Clique no botão lateral para carregar os 17 jogadores.")
