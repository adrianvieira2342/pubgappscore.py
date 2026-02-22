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
# 2. MOTOR DE IMPORTAÇÃO (LÓGICA FIEL AO SEU VS CODE)
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
        if res_season.status_code != 200: return False
        current_season_id = next(s["id"] for s in res_season.json()["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Limpar Tabela
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM ranking_squad"))

        status_text = st.sidebar.empty()

        # 3. Processar Jogadores com TIME.SLEEP para evitar Rate Limit
        for i, player in enumerate(players):
            status_text.caption(f"Processando {i+1}/{len(players)}: {player}")
            
            res_p = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player}", headers=headers)
            
            if res_p.status_code == 200:
                p_data = res_p.json()
                if p_data.get("data"):
                    p_id = p_data["data"][0]["id"]
                    
                    time.sleep(1.5) # --- SEU TIME.SLEEP ORIGINAL ---
                    
                    res_s = requests.get(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{current_season_id}", headers=headers)
                    if res_s.status_code == 200:
                        all_stats = res_s.json()["data"]["attributes"]["gameModeStats"]
                        stats = all_stats.get("squad", {})
                        
                        partidas = stats.get("roundsPlayed", 0)
                        if partidas > 0:
                            kills = stats.get("kills", 0)
                            vitorias = stats.get("wins", 0)
                            assists = stats.get("assists", 0)
                            headshots = stats.get("headshotKills", 0)
                            revives = stats.get("revives", 0)
                            dano_total = stats.get("damageDealt", 0)
                            dist_max = stats.get("longestKill", 0.0)
                            
                            kr = round(kills / partidas, 2)
                            dano_medio = int(dano_total / partidas)

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
            
            time.sleep(2.0) # --- SEU SEGUNDO TIME.SLEEP ORIGINAL ---
        return True
    except Exception as e:
        st.sidebar.error(f"Erro: {e}")
        return False

# =========================================================
# 3. LÓGICA DE LAYOUT (ZONAS E EMOJIS)
# =========================================================
def processar_visual(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks, zonas, posicoes = [], [], []
    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for emoji in ["💀", "💩", "👤"]: nick_limpo = nick_limpo.replace(emoji, "").strip()

        posicoes.append(pos)
        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}"); zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}"); zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}"); zonas.append("Medíocre Zone")

    df_ranking['Pos'] = posicoes
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas
    
    cols = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'kill_dist_max', 'dano_medio']
    return df_ranking[cols + [col_score]]

# =========================================================
# 4. INTERFACE PRINCIPAL
# =========================================================
st.markdown("# 🎮 Ranking Squad - Season 40")

# Dispara sincronização
if count == 0 or st.sidebar.button("🔄 Sincronizar API"):
    with st.spinner("Buscando dados (isso leva 1 min devido ao Rate Limit)..."):
        sync_data()

def get_display_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        return pd.read_sql("SELECT * FROM ranking_squad", engine)
    except: return pd.DataFrame()

df_bruto = get_display_data()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)
        
        # Top 3 Metrics
        if len(ranking_ordenado) >= 3:
            c1, c2, c3 = st.columns(3)
            c1.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
            c2.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
            c3.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

        st.markdown("---")
        ranking_final = processar_visual(ranking_ordenado, col_score)

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone": return ['background-color: #004d00; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone": return ['background-color: #4d2600; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            ranking_final.style.background_gradient(cmap='YlGnBu', subset=[col_score])
            .apply(highlight_zones, axis=1).format(precision=2),
            use_container_width=True, height=650, hide_index=True
        )

    with tab1:
        f = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*100*5)
        renderizar(df_bruto.copy(), 'Score_PRO', f)
    with tab2:
        f = ((df_bruto['vitorias']/df_bruto['partidas'])*1000) + (df_bruto['revives']*10) + (df_bruto['assists']*5)
        renderizar(df_bruto.copy(), 'Score_TEAM', f)
    with tab3:
        f = (df_bruto['kr']*50) + ((df_bruto['headshots']/df_bruto['partidas'])*60) + (df_bruto['dano_medio']/5)
        renderizar(df_bruto.copy(), 'Score_ELITE', f)
else:
    st.info("Aguardando sincronização completa dos 17 jogadores...")
