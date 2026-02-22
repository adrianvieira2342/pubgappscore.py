import streamlit as st
import pandas as pd
import requests
import time
from sqlalchemy import text

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮"
)

# =============================
# CONEXÃO COM BANCO
# =============================
def get_connection():
    return st.connection(
        "postgresql",
        type="sql",
        url=st.secrets["DATABASE_URL"]
    )

def get_data():
    try:
        conn = get_connection()
        df = conn.query("SELECT * FROM ranking_squad", ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# ATUALIZAÇÃO DO RANKING
# =============================
def atualizar_ranking():

    conn = get_connection()
    PUBG_API_KEY = st.secrets["PUBG_API_KEY"]

    df_nicks = conn.query("SELECT nick FROM ranking_squad", ttl=0)

    headers = {
        "Authorization": f"Bearer {PUBG_API_KEY}",
        "Accept": "application/vnd.api+json"
    }

    st.warning("Atualizando ranking automaticamente...")

    for nick in df_nicks["nick"]:

        try:
            url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
            response = requests.get(url, headers=headers)

            if response.status_code == 429:
                st.error(f"429 para {nick} - aguardando 5 segundos...")
                time.sleep(5)
                continue

            if response.status_code != 200:
                st.error(f"Falha ao buscar dados de {nick}: {response.status_code}")
                continue

            data = response.json()

            # =============================
            # AQUI VOCÊ INSERE SEU PROCESSAMENTO ORIGINAL
            # =============================
            # Exemplo fictício (substitua pela sua lógica real):
            stats = data["data"][0]["attributes"]["gameModeStats"]["squad"]

            kr = stats.get("kdr", 0)
            partidas = stats.get("roundsPlayed", 1)
            vitorias = stats.get("wins", 0)
            kills = stats.get("kills", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            kill_dist_max = stats.get("longestKill", 0)
            dano_medio = stats.get("damageDealt", 0) / partidas if partidas > 0 else 0

            # =============================
            # UPDATE NO BANCO (SEM PSYCOPG2)
            # =============================
            conn.session.execute(
                text("""
                    UPDATE ranking_squad
                    SET kr = :kr,
                        partidas = :partidas,
                        vitorias = :vitorias,
                        kills = :kills,
                        assists = :assists,
                        headshots = :headshots,
                        revives = :revives,
                        kill_dist_max = :kill_dist_max,
                        dano_medio = :dano_medio
                    WHERE nick = :nick
                """),
                {
                    "kr": kr,
                    "partidas": partidas,
                    "vitorias": vitorias,
                    "kills": kills,
                    "assists": assists,
                    "headshots": headshots,
                    "revives": revives,
                    "kill_dist_max": kill_dist_max,
                    "dano_medio": dano_medio,
                    "nick": nick
                }
            )

            conn.session.commit()

            time.sleep(1)  # delay original

        except Exception as e:
            st.error(f"Erro ao atualizar {nick}: {e}")

# =============================
# PROCESSAMENTO DO RANKING
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

# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

if st.button("🔄 Atualizar Ranking Agora"):
    atualizar_ranking()
    st.rerun()

df_bruto = get_data()

if not df_bruto.empty:

    df_bruto['partidas'] = df_bruto['partidas'].replace(0, 1)

    tab1, tab2, tab3 = st.tabs([
        "🔥 PRO (Equilibrado)",
        "🤝 TEAM (Suporte)",
        "🎯 ELITE (Skill)"
    ])

    def renderizar_ranking(df_local, col_score, formula):

        df_local[col_score] = formula.round(2)
        ranking_ordenado = df_local.sort_values(
            col_score,
            ascending=False
        ).reset_index(drop=True)

        ranking_final = processar_ranking_completo(
            ranking_ordenado,
            col_score
        )

        st.dataframe(
            ranking_final.style
            .background_gradient(cmap='YlGnBu', subset=[col_score])
            .format(precision=2),
            use_container_width=True,
            height=650,
            hide_index=True
        )

    with tab1:
        f_pro = (
            (df_bruto['kr'] * 40)
            + (df_bruto['dano_medio'] / 8)
            + ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Pro', f_pro)

    with tab2:
        f_team = (
            ((df_bruto['vitorias'] / df_bruto['partidas']) * 100 * 10)
            + ((df_bruto['revives'] / df_bruto['partidas']) * 50)
            + ((df_bruto['assists'] / df_bruto['partidas']) * 35)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Team', f_team)

    with tab3:
        f_elite = (
            (df_bruto['kr'] * 50)
            + ((df_bruto['headshots'] / df_bruto['partidas']) * 60)
            + (df_bruto['dano_medio'] / 5)
        )
        renderizar_ranking(df_bruto.copy(), 'Score_Elite', f_elite)

else:
    st.info("Banco conectado. Aguardando inserção de dados na tabela 'ranking_squad'.")
