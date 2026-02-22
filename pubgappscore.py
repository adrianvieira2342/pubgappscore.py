import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# =============================
# VARIÁVEL GLOBAL PARA ATUALIZAÇÃO
# =============================
if 'ultima_atualizacao_memoria' not in st.session_state:
    st.session_state['ultima_atualizacao_memoria'] = datetime.min

def precisa_atualizar():
    return (datetime.now() - st.session_state['ultima_atualizacao_memoria']) > timedelta(minutes=5)

def registrar_atualizacao():
    st.session_state['ultima_atualizacao_memoria'] = datetime.now()

# =============================
# CONEXÃO COM BANCO (POSTGRES)
# =============================
def get_conn():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
        return None

# =============================
# FUNÇÃO PARA BUSCAR DADOS DO PUBG
# =============================
def buscar_api_pubg(api_key, player_list):
    """
    Retorna DataFrame com dados de cada jogador
    player_list: lista de nicks para puxar dados
    """
    all_data = []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json"
    }

    for nick in player_list:
        url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # exemplo: extrair stats
                stats = {
                    "nick": nick,
                    "partidas": data.get('data', [{}])[0].get('stats', {}).get('matches', 0),
                    "kr": data.get('data', [{}])[0].get('stats', {}).get('kdRatio', 0),
                    "vitorias": data.get('data', [{}])[0].get('stats', {}).get('wins', 0),
                    "kills": data.get('data', [{}])[0].get('stats', {}).get('kills', 0),
                    "assists": data.get('data', [{}])[0].get('stats', {}).get('assists', 0),
                    "headshots": data.get('data', [{}])[0].get('stats', {}).get('headshots', 0),
                    "revives": data.get('data', [{}])[0].get('stats', {}).get('revives', 0),
                    "kill_dist_max": data.get('data', [{}])[0].get('stats', {}).get('longestKill', 0),
                    "dano_medio": data.get('data', [{}])[0].get('stats', {}).get('damageDealt', 0)
                }
                all_data.append(stats)
            else:
                st.warning(f"Falha ao buscar dados de {nick}: {resp.status_code}")
        except Exception as e:
            st.warning(f"Erro ao buscar dados de {nick}: {e}")

    return pd.DataFrame(all_data)

# =============================
# FUNÇÃO PARA ATUALIZAR BANCO
# =============================
def atualizar_banco(conn, df):
    """
    Atualiza tabela ranking_squad com os dados do DataFrame
    """
    for _, row in df.iterrows():
        # insere ou atualiza pelo nick
        conn.query(f"""
            INSERT INTO ranking_squad (nick, partidas, kr, vitorias, kills, assists, headshots, revives, kill_dist_max, dano_medio)
            VALUES ('{row['nick']}', {row['partidas']}, {row['kr']}, {row['vitorias']}, {row['kills']}, {row['assists']}, {row['headshots']}, {row['revives']}, {row['kill_dist_max']}, {row['dano_medio']})
            ON CONFLICT (nick) DO UPDATE SET
                partidas = EXCLUDED.partidas,
                kr = EXCLUDED.kr,
                vitorias = EXCLUDED.vitorias,
                kills = EXCLUDED.kills,
                assists = EXCLUDED.assists,
                headshots = EXCLUDED.headshots,
                revives = EXCLUDED.revives,
                kill_dist_max = EXCLUDED.kill_dist_max,
                dano_medio = EXCLUDED.dano_medio;
        """)

# =============================
# FUNÇÃO PARA ATUALIZAR RANKING
# =============================
def atualizar_ranking(conn):
    st.info("Atualizando ranking automaticamente...")

    api_key = st.secrets["PUBG_API_KEY"]

    # buscar lista de nicks no banco
    try:
        df_nicks = conn.query("SELECT nick FROM ranking_squad")
        if df_nicks.empty:
            st.info("Nenhum nick encontrado para atualizar.")
            registrar_atualizacao()
            return
        player_list = df_nicks['nick'].tolist()
    except Exception as e:
        st.error(f"Erro ao buscar lista de nicks: {e}")
        return

    # buscar dados da API PUBG
    df_api = buscar_api_pubg(api_key, player_list)

    if not df_api.empty:
        atualizar_banco(conn, df_api)
    registrar_atualizacao()

# =============================
# FUNÇÕES DE PROCESSAMENTO E INTERFACE
# =============================
def processar_ranking_completo(df_ranking, col_score):
    total = len(df_ranking)
    novos_nicks = []
    zonas = []
    posicoes = []

    df_ranking = df_ranking.reset_index(drop=True)

    for i, row in df_ranking.iterrows():
        pos = i + 1
        nick_limpo = str(row['nick'])
        for emoji in ["💀", "💩", "👤", "🏅"]:
            nick_limpo = nick_limpo.replace(emoji, "").strip()

        posicoes.append(pos)
        if pos <= 3:
            novos_nicks.append(f"💀 {nick_limpo}")
            zonas.append("Elite Zone")
        elif pos > (total - 3):
            novos_nicks.append(f"💩 {nick_limpo}")
            zonas.append("Cocô Zone")
        else:
            novos_nicks.append(f"👤 {nick_limpo}")
            zonas.append("Medíocre Zone")

    df_ranking['Pos'] = posicoes
    df_ranking['nick'] = novos_nicks
    df_ranking['Classificação'] = zonas

    cols_base = [
        'Pos', 'Classificação', 'nick',
        'partidas', 'kr', 'vitorias',
        'kills', 'assists', 'headshots',
        'revives', 'kill_dist_max', 'dano_medio'
    ]

    return df_ranking[cols_base + [col_score]]

def renderizar_ranking(df_bruto, col_score, formula):
    df_bruto[col_score] = formula.round(2)
    ranking_ordenado = df_bruto.sort_values(col_score, ascending=False).reset_index(drop=True)

    if len(ranking_ordenado) >= 3:
        top1, top2, top3 = st.columns(3)
        with top1:
            st.metric("🥇 1º Lugar", ranking_ordenado.iloc[0]['nick'], f"{ranking_ordenado.iloc[0][col_score]} pts")
        with top2:
            st.metric("🥈 2º Lugar", ranking_ordenado.iloc[1]['nick'], f"{ranking_ordenado.iloc[1][col_score]} pts")
        with top3:
            st.metric("🥉 3º Lugar", ranking_ordenado.iloc[2]['nick'], f"{ranking_ordenado.iloc[2][col_score]} pts")

    st.markdown("---")

    ranking_final = processar_ranking_completo(ranking_ordenado, col_score)

    def highlight_zones(row):
        if row['Classificação'] == "Elite Zone":
            return ['background-color: #004d00; color: white; font-weight: bold'] * len(row)
        if row['Classificação'] == "Cocô Zone":
            return ['background-color: #4d2600; color: white; font-weight: bold'] * len(row)
        return [''] * len(row)

    st.dataframe(
        ranking_final.style
        .background_gradient(cmap='YlGnBu', subset=[col_score])
        .apply(highlight_zones, axis=1)
        .format(precision=2),
        use_container_width=True,
        height=650,
        hide_index=True
    )

# =============================
# RODAR APP
# =============================
conn = get_conn()
if conn and precisa_atualizar():
    atualizar_ranking(conn)

st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

df_bruto = conn.query("SELECT * FROM ranking_squad") if conn else pd.DataFrame()

if not df_bruto.empty:
    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs([
        "🔥 PRO (Equilibrado)",
        "🤝 TEAM (Suporte)",
        "🎯 ELITE (Skill)"
    ])

    f_pro = (df_bruto['kr'] * 40) + (df_bruto['dano_medio'] / 8) + ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 5)
    renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

    f_team = ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 10) + ((df_bruto['revives'] / df_bruto['partidas']) * 50) + ((df_bruto['assists'] / df_bruto['partidas']) * 35)
    renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

    f_elite = (df_bruto['kr'] * 50) + ((df_bruto['headshots'] / df_bruto['partidas']) * 60) + (df_bruto['dano_medio'] / 5)
    renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; padding: 20px;'>📊 <b>By Adriano Vieira</b></div>", unsafe_allow_html=True)
else:
    st.info("Banco conectado. Aguardando inserção de dados na tabela 'ranking_squad'.")
