import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="PUBG Ranking", layout="wide", page_icon="🎮")

# Estilização da barra verde
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        border-radius: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def get_data():
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        # Forçamos o banco a nos entregar a data como texto puro
        query = "SELECT *, atualizado_em::text as data_texto FROM ranking_squad"
        return conn.query(query, ttl=0)
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df = get_data()

if not df.empty:
    # --- LOGICA DA BARRA ---
    # Pegamos o valor máximo da coluna (o último que o GitHub enviou)
    try:
        horario_raw = df['data_texto'].max()
        # Formata de AAAA-MM-DD para DD/MM/AAAA
        dt_obj = datetime.strptime(horario_raw[:19], '%Y-%m-%d %H:%M:%S')
        data_final = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
    except:
        data_final = "Sincronizando..."

    st.markdown(f'<div class="sync-bar">● Dados Sincronizados (Brasília): {data_final}</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Filtro de jogadores com partidas
    df = df[df['partidas'].fillna(0).astype(int) > 0].copy()
    
    # Exibe um aviso simples para você testar se os dados subiram
    st.write(f"Total de jogadores ativos: {len(df)}")
    st.table(df[['nick', 'partidas', 'kr', 'score']].head(10)) # Mostra os 10 primeiros para teste

else:
    st.warning("O banco de dados está vazio ou desconectado.")
