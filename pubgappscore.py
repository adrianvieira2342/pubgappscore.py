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
# ATUALIZAÇÃO AUTOMÁTICA
# =============================
def atualizar_dados_supabase():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )

        api_key = st.secrets["PUBG_API_KEY"]

        jogadores = conn.query("SELECT nick FROM ranking_squad", ttl=0)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.api+json"
        }

        for _, row in jogadores.iterrows():
            nick = row["nick"]

            # 🔹 BUSCAR PLAYER
            player_url = f"https://api.pubg.com/shards/steam/players?filter[playerNames]={nick}"
            r_player = requests.get(player_url, headers=headers)

            if r_player.status_code != 200:
                continue

            player_data = r_player.json()["data"][0]
            player_id = player_data["id"]

            # 🔹 BUSCAR STATS
            stats_url = f"https://api.pubg.com/shards/steam/players/{player_id}/seasons/lifetime"
            r_stats = requests.get(stats_url, headers=headers)

            if r_stats.status_code != 200:
                continue

            stats = r_stats.json()["data"]["attributes"]["gameModeStats"]["squad"]

            partidas = stats.get("roundsPlayed", 0)
            kills = stats.get("kills", 0)
            assists = stats.get("assists", 0)
            headshots = stats.get("headshotKills", 0)
            revives = stats.get("revives", 0)
            vitorias = stats.get("wins", 0)
            dano_total = stats.get("damageDealt", 0)
            kill_dist_max = stats.get("longestKill", 0)

            kr = kills / partidas if partidas > 0 else 0
            dano_medio = dano_total / partidas if partidas > 0 else 0

            update_sql = text("""
                UPDATE ranking_squad
                SET partidas = :partidas,
                    kills = :kills,
                    assists = :assists,
                    headshots = :headshots,
                    revives = :revives,
                    vitorias = :vitorias,
                    kr = :kr,
                    dano_medio = :dano_medio,
                    kill_dist_max = :kill_dist_max
                WHERE nick = :nick
            """)

            with conn.session as session:
                session.execute(update_sql, {
                    "partidas": partidas,
                    "kills": kills,
                    "assists": assists,
                    "headshots": headshots,
                    "revives": revives,
                    "vitorias": vitorias,
                    "kr": kr,
                    "dano_medio": dano_medio,
                    "kill_dist_max": kill_dist_max,
                    "nick": nick
                })
                session.commit()

            time.sleep(1)

    except Exception as e:
        st.error(f"Erro ao atualizar dados: {e}")


# =============================
# CONEXÃO COM BANCO
# =============================
def get_data():
    try:
        conn = st.connection(
            "postgresql",
            type="sql",
            url=st.secrets["DATABASE_URL"]
        )

        df = conn.query("SELECT * FROM ranking_squad", ttl=0)
        return df

    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()


# =============================
# INTERFACE
# =============================
st.markdown("# 🎮 Ranking Squad - Season 40")
st.markdown("---")

st.cache_data.clear()

# 🔥 ATUALIZA SEMPRE AO CARREGAR
atualizar_dados_supabase()

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

        ranking = df_local.sort_values(
            col_score,
            ascending=False
        ).reset_index(drop=True)

        st.dataframe(
            ranking,
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
    st.info("Banco conectado. Aguardando inserção de dados.")
