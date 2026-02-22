import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine
from streamlit_autorefresh import st_autorefresh

# =========================================================
# 1. CONFIGURAÇÃO E REFRESH
# =========================================================
st.set_page_config(page_title="PUBG DEBUG MODE", layout="wide", page_icon="🎮")

# Atualiza a página a cada 3 minutos
count = st_autorefresh(interval=180000, key="ranking_refresh")

# =========================================================
# 2. MOTOR DE IMPORTAÇÃO (MODO DEBUG)
# =========================================================
def sync_api_to_supabase():
    st.sidebar.header("🔍 Diagnóstico API")
    try:
        # Verifica Secrets
        if "PUBG_API_KEY" not in st.secrets or "DATABASE_URL" not in st.secrets:
            st.sidebar.error("❌ Erro: Secrets não encontradas no Streamlit Cloud!")
            return False

        api_key = st.secrets["PUBG_API_KEY"]
        db_url = st.secrets["DATABASE_URL"]
        
        # URL - ATENÇÃO: SUBSTITUA 'SEUS_IDS_AQUI' OU NADA SERÁ ATUALIZADO
        url = "https://api.pubg.com/shards/steam/seasons/division.as.officials.pc-2024-40/gameMode/squad-fpp/players?filter[playerIds]=SEUS_IDS_AQUI"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.api+json"
        }

        st.sidebar.info("⏳ Chamando API do PUBG...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            raw_data = response.json()
            jogadores = []

            data_list = raw_data.get('data', [])
            if not data_list:
                st.sidebar.warning("⚠️ API conectou, mas a lista de jogadores veio vazia!")
                return False

            for item in data_list:
                attr = item.get('attributes', {})
                stats = attr.get('gameModeStats', {}).get('squad-fpp', {})
                rounds = stats.get('roundsPlayed', 0)
                
                if rounds > 0:
                    jogadores.append({
                        'nick': attr.get('name', 'Unknown'),
                        'partidas': rounds,
                        'kr': round(stats.get('kills', 0) / max(stats.get('deaths', 1), 1), 2),
                        'vitorias': stats.get('wins', 0),
                        'kills': stats.get('kills', 0),
                        'assists': stats.get('assists', 0),
                        'headshots': stats.get('headshotKills', 0),
                        'revives': stats.get('revives', 0),
                        'kill_dist_max': round(stats.get('longestKill', 0), 2),
                        'dano_medio': round(stats.get('damageDealt', 0) / rounds, 2)
                    })

            if jogadores:
                df_novo = pd.DataFrame(jogadores)
                st.sidebar.info(f"✅ {len(jogadores)} jogadores processados.")
                
                # Teste de Conexão com Banco
                engine = create_engine(db_url)
                df_novo.to_sql('ranking_squad', engine, if_exists='replace', index=False)
                st.sidebar.success("🚀 Banco de dados atualizado!")
                return True
            else:
                st.sidebar.error("❌ Os jogadores listados não jogaram nesta season.")
        else:
            st.sidebar.error(f"❌ Erro na API: Status {response.status_code}")
            st.sidebar.write(response.text) # Mostra o erro bruto da API
            
        return False
    except Exception as e:
        st.sidebar.error(f"💥 Falha Crítica: {str(e)}")
        return False

# Executa a sincronização
sync_api_to_supabase()

# =========================================================
# 3. LEITURA DE DADOS
# =========================================================
def get_data():
    try:
        engine = create_engine(st.secrets["DATABASE_URL"])
        df = pd.read_sql("SELECT * FROM ranking_squad", engine)
        return df
    except Exception as e:
        st.sidebar.error(f"Erro ao ler banco: {e}")
        return pd.DataFrame()

# =========================================================
# 4. PROCESSAMENTO E LAYOUT (ORIGINAL)
# =========================================================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks, zonas, posicoes = [], [], []
    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for emoji in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

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

    cols = ['Pos', 'Classificação', 'nick', 'partidas', 'kr', 'vitorias', 
            'kills', 'assists', 'headshots', 'revives', 'kill_dist_max', 'dano_medio']
    return df_ranking[cols + [col_score]]

# =========================================================
# 5. INTERFACE PRINCIPAL
# =========================================================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.caption(f"Refresh ID: {count}")

df_bruto = get_data()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)
    tab1, tab2, tab3 = st.tabs(["🔥 PRO", "🤝 TEAM", "🎯 ELITE"])

    def renderizar_ranking(df_local, col_score, formula):
        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(col_score, ascending=False).reset_index(drop=True)
        
        if len(ranking_ordenado) >= 3:
            c1, c2, c3 = st.columns(3)
            c1.metric("🥇 1º", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
            c2.metric("🥈 2º", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
            c3.metric("🥉 3º", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

        st.markdown("---")
        ranking_final = processar_ranking_completo(ranking_ordenado, col_score)

        def highlight_zones(row):
            if row['Classificação'] == "Elite Zone": return ['background-color: #004d00; color: white'] * len(row)
            if row['Classificação'] == "Cocô Zone": return ['background-color: #4d2600; color: white'] * len(row)
            return [''] * len(row)

        st.dataframe(
            ranking_final.style.background_gradient(cmap='YlGnBu', subset=[col_score])
            .apply(highlight_zones, axis=1).format(precision=2),
            use_container_width=True, height=650, hide_index=True
        )

    with tab1:
        f = (df_bruto['kr']*40) + (df_bruto['dano_medio']/8) + ((df_bruto['vitorias']/df_bruto['partidas'])*500)
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f)
    with tab2:
        f = ((df_bruto['vitorias']/df_bruto['partidas'])*1000) + ((df_bruto['revives']/df_bruto['partidas'])*50)
        renderizar_ranking(df_bruto.copy(), 'Score_Team', f)
    with tab3:
        f = (df_bruto['kr']*50) + ((df_bruto['headshots']/df_bruto['partidas'])*60) + (df_bruto['dano_medio']/5)
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', f)
else:
    st.warning("⚠️ Banco de dados ainda não sincronizado. Verifique o diagnóstico na barra lateral.")
