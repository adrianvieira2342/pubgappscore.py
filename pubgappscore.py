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

# Refresh visual a cada 3 minutos
count = st_autorefresh(interval=180000, key="ranking_refresh")

# =========================================================
# 2. MOTOR DE IMPORTAÇÃO (COM SUA FUNÇÃO DE RATE LIMIT)
# =========================================================

def sync_data():
    API_KEY = st.secrets["PUBG_API_KEY"]
    DB_URL = st.secrets["DATABASE_URL"]
    engine = create_engine(DB_URL)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    # SUA FUNÇÃO ORIGINAL DE REQUISIÇÃO
    def fazer_requisicao(url):
        for tentativa in range(3):
            res = requests.get(url, headers=headers)
            if res.status_code == 429:
                st.sidebar.warning(f"⚠️ Rate Limit! Aguardando 30s...")
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
        # 1. Detectar Temporada
        res_season = fazer_requisicao("https://api.pubg.com/shards/steam/seasons")
        if not res_season or res_season.status_code != 200:
            return False
        current_season_id = next(s["id"] for s in res_season.json()["data"] if s["attributes"]["isCurrentSeason"])

        # 2. Limpar Tabela
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM ranking_squad"))

        status_bar = st.sidebar.progress(0)
        
        # 3. Loop de Jogadores
        for i, player in enumerate(players):
            # Log de progresso na barra lateral
            status_bar.progress((i + 1) / len(players))
            st.sidebar.caption(f"Lendo: {player}")

            # Busca ID do Player
            res_p = fazer_requisicao(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player}")
            
            if res_p and res_p.status_code == 200:
                p_data = res_p.json()
                if p_data.get("data"):
                    p_id = p_data["data"][0]["id"]
                    
                    time.sleep(1.5) # Seu sleep original entre chamadas

                    # Busca Stats
                    res_s = fazer_requisicao(f"https://api.pubg.com/shards/steam/players/{p_id}/seasons/{current_season_id}")
                    if res_s and res_s.status_code == 200:
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
            
            time.sleep(2.0) # Seu sleep original entre jogadores
            
        st.sidebar.success("✅ Sincronização Concluída!")
        return True
    except Exception as e:
        st.sidebar.error(f"Erro Crítico: {e}")
        return False

# Dispara a função se for a primeira vez ou se clicar no botão
if count == 0:
    sync_data()

if st.sidebar.button("🔄 Sincronizar Manualmente"):
    sync_data()

# =========================================================
# 3. INTERFACE E LAYOUT ORIGINAL REESTILIZADO
# =========================================================

def get_display_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        return pd.read_sql("SELECT * FROM ranking_squad", engine)
    except: return pd.DataFrame()

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
        elif pos > (total - 3) and total > 5:
            novos_nicks.append(f"💩 {nick_limpo}"); zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}"); zonas.append("Medíocre Zone")

    df_ranking['Pos'] = posicoes
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas
    
    cols = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'headshots', 'revives', 'kill_dist_max', 'dano_medio']
    return df_ranking[cols + [col_score]]

st.markdown("# 🎮 Ranking Squad - Season 40")
df_bruto = get_display_data()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)
        
        # TOP 3 CARDS
        if len(ranking_ordenado) >= 3:
            c1, c2, c3 = st.columns(3)
            c1.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
            c2.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
            c3.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

        st.markdown("---")
        ranking_final = processar_visual(ranking_ordenado, col_score)

        # CORES DAS ZONAS
        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone": return ['background-color: #004d00; color: white; font-weight: bold'] * len(row)
            if row['Classificação'] == "Cocô Zone": return ['background-color: #4d2600; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            ranking_final.style.background_gradient(cmap='YlGnBu', subset=[col_score])
            .apply(highlight_zones, axis=1).format(precision=2),
            use_container_width=True, height=650, hide_index=True
        )

    with tab1: # PRO SCORE
        f = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
        renderizar(df_bruto.copy(), 'Score_PRO', f)
    with tab2: # TEAM SCORE
        f = ((df_bruto['vitorias']/df_bruto['partidas'])*1000) + (df_bruto['revives']*10) + (df_bruto['assists']*5)
        renderizar(df_bruto.copy(), 'Score_TEAM', f)
    with tab3: # ELITE SCORE
        f = (df_bruto['kr']*50) + ((df_bruto['headshots']/df_bruto['partidas'])*60) + (df_bruto['dano_medio']/5)
        renderizar(df_bruto.copy(), 'Score_ELITE', f)

else:
    st.info("📊 Sincronizando dados com a API... Isso levará cerca de 2 minutos para processar todos os jogadores sem travar.")
