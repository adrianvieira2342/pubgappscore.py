import streamlit as st
import pandas as pd
import psycopg2

# Configuração da página
st.set_page_config(page_title="PUBG Ranking Squad", layout="wide")

# =============================
# MAPEAMENTO NICK -> ACCOUNT ID
# =============================
PLAYER_IDS = {
    "Adrian-Wan": "account.58beb24ada7346408942d42dc64c7901",
    "MironoteuCool": "account.24b0600cbba342eab1546ae2881f50fa",
    "FabioEspeto": "account.d8ccad228a4a417dad9921616d6c6bcd",
    "Mamutag_Komander": "account.64c62d76cce74d0b99857a27975e350e",
    "Robson_Foz": "account.8142e6d837254ee1bca954b719692f38",
    "MEIRAA": "account.c3f37890e7534978abadaf4bae051390",
    "EL-LOCORJ": "account.94ab932726fc4c64a03eb9797429baa3",
    "SalaminhoKBD": "account.de093e200d3441a9b781a9717a017dd3",
    "nelio_ponto_dev": "account.ad39c88ddf754d33a3dfeadc117c47df",
    "CARNEIROOO": "account.8c0313f2148d47b7bffcde634f094445",
    "Kowalski_PR": "account.b25200afe120424a839eb56dd2bc49cb",
    "Zacouteguy": "account.a742bf1d5725467c91140cd0ed83c265",
    "Sidors": "account.60ab21fad4094824a32dc404420b914d",
    "Takato_Matsuki": "account.10d2403139bd4066a95dda1a3eefe1e8",
    "cmm01": "account.80cedebb935242469fdd177454a52e0e",
    "Petrala": "account.aadd1c378ff841219d853b4ad2646286",
    "Fumiga_BR": "account.1fa2a7c08c3e4d4786587b4575a071cb"
}

def carregar_ranking():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        query = """
            SELECT nick, partidas, kr, vitorias, kills, 
                   dano_medio, score, atualizado_em 
            FROM ranking_squad 
            ORDER BY score DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        # Substitui nick pelo account_id
        df["nick"] = df["nick"].map(PLAYER_IDS).fillna(df["nick"])

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


st.title("🏆 Ranking Squad PUBG")
st.markdown("Estatísticas atualizadas automaticamente via API Oficial.")

# Botão para atualizar
if st.button('🔄 Recarregar Tabela'):
    st.cache_data.clear()

df_ranking = carregar_ranking()

if df_ranking is not None:

    # 1. Destaque Top 3
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(df_ranking):
            player = df_ranking.iloc[i]
            col.metric(
                label=f"{i+1}º Lugar",
                value=player['nick'],
                delta=f"Score: {player['score']}"
            )

    st.divider()

    # 2. Tabela
    st.subheader("📊 Classificação Geral")
    st.dataframe(
        df_ranking,
        column_config={
            "nick": "Player ID",
            "partidas": "Partidas",
            "kr": st.column_config.NumberColumn("K/R", format="%.2f"),
            "vitorias": "Vitórias",
            "kills": "Total Kills",
            "dano_medio": "Dano Médio",
            "score": st.column_config.ProgressColumn(
                "Pontuação Final",
                min_value=0,
                max_value=float(df_ranking['score'].max())
            ),
            "atualizado_em": st.column_config.DatetimeColumn(
                "Última Atualização",
                format="DD/MM/YYYY HH:mm"
            )
        },
        hide_index=True,
        use_container_width=True
    )

    # 3. Gráfico
    st.divider()
    st.subheader("🎯 Performance: Dano vs Kills")
    st.scatter_chart(df_ranking, x='dano_medio', y='kills', color='nick')

else:
    st.warning("Nenhum dado encontrado na tabela ranking_squad.")
