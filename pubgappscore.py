import os
import time
import requests
import psycopg2
import pandas as pd
import streamlit as st

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="PUBG Squad Ranking", layout="wide", page_icon="🎮")

API_KEY = st.secrets["PUBG_API_KEY"]
DATABASE_URL = st.secrets["DATABASE_URL"]
BASE_URL = "https://api.pubg.com/shards/steam"
headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/vnd.api+json"}

players_list = [
    "Adrian-Wan", "MironoteuCool", "FabioEspeto", "Mamutag_Komander",
    "Robson_Foz", "MEIRAA", "EL-LOCORJ", "SalaminhoKBD",
    "nelio_ponto_dev", "CARNEIROOO", "Kowalski_PR", "Zacouteguy",
    "Sidors", "Takato_Matsuki", "cmm01", "Petrala", "Fumiga_BR"
]

# ==========================================
# 2. FUNÇÕES DE DADOS (API & BANCO)
# ==========================================

def carregar_do_banco():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        df = pd.read_sql("SELECT * FROM ranking_squad", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao ler banco: {e}")
        return pd.DataFrame()

def sincronizar_api():
    """Busca dados atuais na API e salva no Supabase"""
    with st.status("🚀 Sincronizando com API oficial do PUBG...", expanded=True) as status:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Pegar Temporada
        res_s = requests.get(f"{BASE_URL}/seasons", headers=headers).json()
        current_season = next(s["id"] for s in res_s["data"] if s["attributes"]["isCurrentSeason"])
        
        # 2. Pegar IDs
        nicks_str = ",".join(players_list)
        res_p = requests.get(f"{BASE_URL}/players?filter[playerNames]={nicks_str}", headers=headers).json()
        player_map = {p["attributes"]["name"]: p["id"] for p in res_p["data"]}
        
        # 3. Loop de Atualização
        for nick, p_id in player_map.items():
            st.write(f"Atualizando: {nick}")
            res_stats = requests.get(f"{BASE_URL}/players/{p_id}/seasons/{current_season}", headers=headers).json()
            stats = res_stats["data"]["attributes"]["gameModeStats"].get("squad", {})
            
            if stats.get("roundsPlayed", 0) > 0:
                p = stats["roundsPlayed"]
                # SQL UPSERT
                sql = """
                INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (nick) DO UPDATE SET
                partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias, kills=EXCLUDED.kills,
                dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists, headshots=EXCLUDED.headshots,
                revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max, atualizado_em=NOW();
                """
                cursor.execute(sql, (
                    nick, p, round(stats["kills"]/p, 2), stats["wins"], stats["kills"],
                    int(stats["damageDealt"]/p), stats["assists"], stats["headshotKills"],
                    stats["revives"], stats["longestKill"]
                ))
                conn.commit()
            time.sleep(6) # Rate Limit
        
        conn.close()
        status.update(label="✅ Sincronização concluída!", state="complete", expanded=False)

# ==========================================
# 3. LÓGICA DE INTERFACE E ZONAS
# ==========================================

def processar_visual(df, col_score):
    df = df.sort_values(col_score, ascending=False).reset_index(drop=True)
    total = len(df)
    
    def formatar_nick_zona(row):
        pos = row.name + 1
        nick = str(row['nick'])
        for e in ["💀", "💩", "👤"]: nick = nick.replace(e, "").strip()
        
        if pos <= 3: return f"💀 {nick}", "Elite Zone", pos
        if pos > (total - 3): return f"💩 {nick}", "Cocô Zone", pos
        return f"👤 {nick}", "Medíocre Zone", pos

    df[['nick', 'Classificação', 'Pos']] = df.apply(formatar_nick_zona, axis=1, result_type='expand')
    cols = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'assists', 'dano_medio', col_score]
    return df[cols]

# ==========================================
# 4. RENDERIZAÇÃO DO APP
# ==========================================

st.title("🎮 PUBG Squad Ranking - Live Stats")

if st.sidebar.button("🔄 Sincronizar API Agora"):
    sincronizar_api()
    st.cache_data.clear()

df_raw = carregar_do_banco()

if not df_raw.empty:
    df_raw['partidas'] = df_raw['partidas'].replace(0, 1)
    
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    # Fórmulas
    df_raw['Score_Pro'] = (df_raw['kr'] * 40) + (df_raw['dano_medio'] / 8) + ((df_raw['vitorias']/df_raw['partidas'])*500)
    df_raw['Score_Team'] = ((df_raw['vitorias']/df_raw['partidas'])*1000) + ((df_raw['revives']/df_raw['partidas'])*50) + ((df_raw['assists']/df_raw['partidas'])*35)
    df_raw['Score_Elite'] = (df_raw['kr'] * 50) + ((df_raw['headshots']/df_raw['partidas'])*60) + (df_raw['dano_medio']/5)

    def mostrar_tab(df_aba, col):
        res = processar_visual(df_aba, col)
        
        # Métricas Top 3
        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 1º Lugar", res.iloc[0]['nick'], f"{res.iloc[0][col]:.2f}")
        c2.metric("🥈 2º Lugar", res.iloc[1]['nick'], f"{res.iloc[1][col]:.2f}")
        c3.metric("🥉 3º Lugar", res.iloc[2]['nick'], f"{res.iloc[2][col]:.2f}")
        
        # Tabela Colorida
        st.dataframe(res.style.apply(lambda r: [
            'background-color: #004d00' if r['Classificação'] == "Elite Zone" else 
            'background-color: #4d2600' if r['Classificação'] == "Cocô Zone" else '' 
            for _ in r], axis=1).format(precision=2), use_container_width=True, hide_index=True)

    with tab1: mostrar_tab(df_raw.copy(), 'Score_Pro')
    with tab2: mostrar_tab(df_raw.copy(), 'Score_Team')
    with tab3: mostrar_tab(df_raw.copy(), 'Score_Elite')

    # DE VOLTA O GRÁFICO QUE VOCÊ QUERIA
    st.divider()
    st.subheader("🎯 Performance: Dano VS Kills")
    st.scatter_chart(df_raw, x='dano_medio', y='kills', color='nick', size='kr')
    
else:
    st.warning("Sem dados. Clique em 'Sincronizar API Agora' na barra lateral.")
