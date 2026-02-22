import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=300000, key="f_refresh")

# 2. MOTOR DE IMPORTAÇÃO (AJUSTADO PARA EVITAR ERRO DE CONSTRAINT)
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

        # BUSCA QUEM JÁ FOI ATUALIZADO HOJE (OPCIONAL) PARA NÃO REPETIR
        # Para simplificar e garantir que todos entrem, vamos processar os que não estão no banco primeiro
        df_existente = pd.read_sql("SELECT nick FROM ranking_squad", engine)
        nicks_no_banco = df_existente['nick'].tolist()
        
        faltam = [p for p in players if p not in nicks_no_banco]
        
        # Se todos já existem, processa os primeiros da lista para atualizar dados
        lote = faltam[:4] if faltam else players[:4]

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
                            # EM VEZ DE ON CONFLICT, APAGAMOS O NICK E INSERIMOS O NOVO
                            conn.execute(text("DELETE FROM ranking_squad WHERE nick = :n"), {"n": p_name})
                            
                            conn.execute(text("""
                                INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max)
                                VALUES (:n, :p, :kr, :v, :k, :dm, :a, :h, :r, :dist)
                            """), {
                                "n": p_name, "p": rd, "kr": round(s.get('kills',0)/rd, 2), 
                                "v": s.get('wins',0), "k": s.get('kills',0),
                                "dm": int(s.get('damageDealt',0)/rd), "a": s.get('assists',0), 
                                "h": s.get('headshotKills',0), "r": s.get('revives',0), 
                                "dist": s.get('longestKill',0)
                            })
            time.sleep(2)
        st.sidebar.success("Lote concluído!")
    except Exception as e: 
        st.sidebar.error(f"Erro: {e}")

# Botão na lateral
if st.sidebar.button("🔄 Sincronizar Próximos Jogadores"):
    sync_data()

# 3. INTERFACE VISUAL (FILTRO DE COLUNAS ADICIONADO)
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
        
        # Lógica de Zonas
        df['Classificação'] = df['Pos'].apply(lambda x: "Elite Zone" if x <= 3 else ("Cocô Zone" if x > len(df)-3 and len(df) > 5 else "Medíocre Zone"))
        
        # Aplicar Emojis nos Nicks para a Tabela e Metrics
        df['nick_display'] = df.apply(lambda x: f"💀 {x['nick']}" if x['Pos'] <= 3 else (f"💩 {x['nick']}" if x['Pos'] > len(df)-3 and len(df) > 5 else f"👤 {x['nick']}"), axis=1)

        # MÉTRICAS DO TOPO
        cols = st.columns(3)
        for i, label in enumerate(["🥇 1º Lugar", "🥈 2º Lugar", "🥉 3º Lugar"]):
            if len(df) > i:
                cols[i].metric(label, df.iloc[i]['nick_display'], f"{df.iloc[i][col_score]} pts")

        st.markdown("---")
        
        # SELEÇÃO E ORDEM DAS COLUNAS (PARA NÃO APARECER ID, ETC)
        colunas_finais = ['Pos', 'Classificação', 'nick_display', 'partidas', 'kr', 'vitorias', 'kills', 'dano_medio', col_score]
        
        df_final = df[colunas_finais].rename(columns={'nick_display': 'nick'})

        def colorir(row):
            if "Elite" in row.Classificação: return ['background-color: #004d00; color: white'] * len(row)
            if "Cocô" in row.Classificação: return ['background-color: #4d2600; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(df_final.style.apply(colorir, axis=1).format(precision=2), use_container_width=True, hide_index=True)

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
    st.info("Aguardando sincronização inicial...")
