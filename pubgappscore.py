import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO DA PÁGINA (WIDE E DARK FIX)
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

# Estilo para forçar o layout original e cards bonitos
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    [data-testid="stDataFrame"] { width: 100% !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=300000, key="f_refresh")

# 2. MOTOR DE IMPORTAÇÃO (ESTRATÉGIA POR LOTES)
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

    def fazer_req(url):
        for _ in range(2):
            res = requests.get(url, headers=headers)
            if res.status_code == 429: time.sleep(30); continue
            return res
        return None

    try:
        res_s = fazer_req("https://api.pubg.com/shards/steam/seasons")
        season_id = next(s["id"] for s in res_s.json()["data"] if s["attributes"]["isCurrentSeason"])

        # BUSCA QUEM JÁ ESTÁ NO BANCO PARA PULAR E NÃO PERDER TEMPO
        df_existente = pd.read_sql("SELECT nick FROM ranking_squad", engine)
        nicks_prontos = df_existente['nick'].tolist()
        
        # FILTRA SÓ QUEM FALTA (LIMITA A 3 POR VEZ PARA NÃO DAR TIMEOUT)
        faltam = [p for p in players if p not in nicks_prontos]
        lote = faltam[:4] # Processa 4 por vez

        if not lote: 
            st.sidebar.success("Todos os 17 nicks já estão no banco!")
            return

        for p_name in lote:
            st.sidebar.write(f"Sincronizando: {p_name}...")
            res_p = fazer_req(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={p_name}")
            if res_p and res_p.status_code == 200:
                p_id = res_p.json()["data"][0]["id"]
                time.sleep(1.5)
                res_stats = fazer_req(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{season_id}")
                if res_stats and res_stats.status_code == 200:
                    s = res_stats.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
                    rd = s.get("roundsPlayed", 0)
                    if rd > 0:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max)
                                VALUES (:n, :p, :kr, :v, :k, :dm, :a, :h, :r, :dist)
                                ON CONFLICT (nick) DO UPDATE SET partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias,
                                kills=EXCLUDED.kills, dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists,
                                headshots=EXCLUDED.headshots, revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max
                            """), {"n": p_name, "p": rd, "kr": round(s.get('kills',0)/rd, 2), "v": s.get('wins',0), "k": s.get('kills',0),
                                   "dm": int(s.get('damageDealt',0)/rd), "a": s.get('assists',0), "h": s.get('headshotKills',0),
                                   "r": s.get('revives',0), "dist": s.get('longestKill',0)})
            time.sleep(2)
        st.sidebar.write("Lote concluído! Clique novamente para carregar mais.")
    except Exception as e: st.sidebar.error(f"Erro: {e}")

# 3. INTERFACE VISUAL
if st.sidebar.button("🔄 Sincronizar Próximos Jogadores"):
    sync_data()

def get_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        return pd.read_sql("SELECT * FROM ranking_squad", engine)
    except: return pd.DataFrame()

df_bruto = get_data()

st.title("🎮 Ranking Squad - Season 40")

if not df_bruto.empty:
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def exibir(df, col_score, formula):
        df[col_score] = formula.round(2)
        df = df.sort_values(col_score, ascending=False).reset_index(drop=True)
        df['Pos'] = range(1, len(df) + 1)
        
        # MANTENDO OS EMOJIS NO NICK
        df['Classificação'] = df['Pos'].apply(lambda x: "Elite Zone" if x <= 3 else ("Cocô Zone" if x > len(df)-3 and len(df) > 5 else "Medíocre Zone"))
        df['nick'] = df.apply(lambda x: f"💀 {x['nick']}" if x['Pos'] <= 3 else (f"💩 {x['nick']}" if x['Pos'] > len(df)-3 and len(df) > 5 else f"👤 {x['nick']}"), axis=1)

        # MÉTRICAS DO TOPO (IDÊNTICO À IMAGEM)
        cols = st.columns(3)
        for i, label in enumerate(["🥇 1º Lugar", "🥈 2º Lugar", "🥉 3º Lugar"]):
            if len(df) > i:
                cols[i].metric(label, df.iloc[i]['nick'], f"{df.iloc[i][col_score]} pts")

        st.markdown("---")
        
        # FILTRO DE COLUNAS PARA NÃO FICAR BAGUNÇADO
        colunas_vistas = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', col_score]
        
        def colorir(row):
            if "Elite" in row.Classificação: return ['background-color: #004d00; color: white'] * len(row)
            if "Cocô" in row.Classificação: return ['background-color: #4d2600; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(df[colunas_vistas].style.apply(colorir, axis=1).format(precision=2), use_container_width=True, hide_index=True)

    with tab1:
        f = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
        exibir(df_bruto.copy(), 'Score_PRO', f)
    with tab2:
        f = (df_bruto['vitorias']*10) + (df_bruto['revives']*10) + (df_bruto['assists']*5)
        exibir(df_bruto.copy(), 'Score_TEAM', f)
    with tab3:
        f = (df_bruto['kr']*50) + (df_bruto['headshots']*5)
        exibir(df_bruto.copy(), 'Score_ELITE', f)
else:
    st.info("Aperte o botão na lateral para começar a carregar os nicks (4 por vez).")
