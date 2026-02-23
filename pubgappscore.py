import os
import time
import requests
import psycopg2
import pandas as pd
import streamlit as st

# ==========================================
# 1. CONFIGURAÇÕES E ESTILO
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
# 2. FUNÇÕES DE BANCO DE DADOS (Lógica que funcionou)
# ==========================================

def carregar_dados_do_banco():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # Buscamos todas as colunas necessárias para os cálculos das abas
        query = "SELECT * FROM ranking_squad"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar banco: {e}")
        return pd.DataFrame()

def sincronizar_api_completo():
    """Lógica de importação API -> Banco"""
    with st.status("🚀 Buscando dados atuais na API PUBG...", expanded=True) as status:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            
            # 1. Temporada
            res_s = requests.get(f"{BASE_URL}/seasons", headers=headers).json()
            current_season = next(s["id"] for s in res_s["data"] if s["attributes"]["isCurrentSeason"])
            
            # 2. IDs dos Jogadores
            nicks_str = ",".join(players_list)
            res_p = requests.get(f"{BASE_URL}/players?filter[playerNames]={nicks_str}", headers=headers).json()
            player_map = {p["attributes"]["name"]: p["id"] for p in res_p["data"]}
            
            # 3. Processar cada jogador
            for nick, p_id in player_map.items():
                st.write(f"Atualizando estatísticas: {nick}")
                r_stats = requests.get(f"{BASE_URL}/players/{p_id}/seasons/{current_season}", headers=headers)
                
                if r_stats.status_code == 200:
                    data = r_stats.json()["data"]["attributes"]["gameModeStats"].get("squad", {})
                    p = data.get("roundsPlayed", 0)
                    
                    if p > 0:
                        sql = """
                        INSERT INTO ranking_squad 
                        (nick, partidas, kr, vitorias, kills, dano_medio, assists, headshots, revives, kill_dist_max)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (nick) DO UPDATE SET
                        partidas=EXCLUDED.partidas, kr=EXCLUDED.kr, vitorias=EXCLUDED.vitorias, kills=EXCLUDED.kills,
                        dano_medio=EXCLUDED.dano_medio, assists=EXCLUDED.assists, headshots=EXCLUDED.headshots,
                        revives=EXCLUDED.revives, kill_dist_max=EXCLUDED.kill_dist_max, atualizado_em=NOW();
                        """
                        cursor.execute(sql, (
                            nick, p, round(data["kills"]/p, 2), data["wins"], data["kills"],
                            int(data["damageDealt"]/p), data["assists"], data["headshotKills"],
                            data["revives"], data["longestKill"]
                        ))
                        conn.commit()
                time.sleep(6) # Respeitar Rate Limit
            
            conn.close()
            status.update(label="✅ Sincronização finalizada!", state="complete")
            st.success("Dados atualizados! Recarregando ranking...")
            time.sleep(2)
            st.rerun() # Força o app a recarregar com dados novos
            
        except Exception as e:
            st.error(f"Erro na sincronização: {e}")

# ==========================================
# 3. LÓGICA DE INTERFACE (Zonas e Emojis)
# ==========================================

def processar_visual(df, col_score):
    df = df.sort_values(col_score, ascending=False).reset_index(drop=True)
    total = len(df)
    
    def aplicar_regras(row):
        pos = row.name + 1
        nick = str(row['nick'])
        for e in ["💀", "💩", "👤"]: nick = nick.replace(e, "").strip()
        
        if pos <= 3: return f"💀 {nick}", "Elite Zone", pos
        if pos > (total - 3): return f"💩 {nick}", "Cocô Zone", pos
        return f"👤 {nick}", "Medíocre Zone", pos

    df[['nick', 'Classificação', 'Pos']] = df.apply(aplicar_regras, axis=1, result_type='expand')
    return df

# ==========================================
# 4. RENDERIZAÇÃO DO APP
# ==========================================

st.title("🎮 PUBG Squad Ranking - Season 40")

# Botão de Sincronização (Mesmo estilo do que funcionou)
if st.button('🔄 Sincronizar API Agora (Importar Dados Atuais)'):
    sincronizar_api_completo()

df_bruto = carregar_dados_do_banco()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)
    
    # Cálculos das 3 Tabelas
    df_bruto['Score_Pro'] = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
    df_bruto['Score_Team'] = ((df_bruto['vitorias']/df_bruto['partidas'])*1000) + ((df_bruto['revives']/df_bruto['partidas'])*50) + ((df_bruto['assists']/df_bruto['partidas'])*35)
    df_bruto['Score_Elite'] = (df_bruto['kr'] * 50) + ((df_bruto['headshots']/df_bruto['partidas'])*60) + (df_bruto['dano_medio']/5)

    tab1, tab2, tab3 = st.tabs(["🔥 PRO (Equilibrado)", "🤝 TEAM (Suporte)", "🎯 ELITE (Skill)"])

    def exibir_tabela(df_aba, col):
        # Processa ranking e zonas
        df_final = processar_visual(df_aba, col)
        
        # Métricas Top 3
        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 1º Lugar", df_final.iloc[0]['nick'], f"{df_final.iloc[0][col]:.2f}")
        c2.metric("🥈 2º Lugar", df_final.iloc[1]['nick'], f"{df_final.iloc[1][col]:.2f}")
        c3.metric("🥉 3º Lugar", df_final.iloc[2]['nick'], f"{df_final.iloc[2][col]:.2f}")
        
        # Tabela Estilizada
        st.dataframe(
            df_final[['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 'kills', 'dano_medio', col]]
            .style.apply(lambda r: [
                'background-color: #004d00; color: white' if r['Classificação'] == "Elite Zone" else 
                'background-color: #4d2600; color: white' if r['Classificação'] == "Cocô Zone" else '' 
                for _ in r], axis=1).format(precision=2),
            use_container_width=True, hide_index=True, height=500
        )

    with tab1: exibir_tabela(df_bruto.copy(), 'Score_Pro')
    with tab2: exibir_tabela(df_bruto.copy(), 'Score_Team')
    with tab3: exibir_tabela(df_bruto.copy(), 'Score_Elite')

    # GRÁFICO DE PERFORMANCE (Igual ao que você solicitou)
    st.divider()
    st.subheader("🎯 Performance: Dano vs Kills")
    st.scatter_chart(df_bruto, x='dano_medio', y='kills', color='nick')
    
    st.caption(f"Última atualização no banco: {df_bruto['atualizado_em'].max()}")

else:
    st.warning("Banco vazio. Clique no botão 'Sincronizar API Agora' para carregar os dados.")
