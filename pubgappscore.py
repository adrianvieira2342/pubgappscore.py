import streamlit as st
import pandas as pd

# =============================
# CONFIGURAÇÃO E CSS
# =============================
st.set_page_config(page_title="PUBG Ranking", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# BUSCA DE DADOS
# =============================
def get_data():
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        # Buscamos a coluna como texto para o Streamlit não tentar converter fuso
        query = "SELECT *, atualizado_em::text as data_fixa FROM ranking_squad"
        return conn.query(query, ttl=0)
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

# =============================
# INTERFACE
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df = get_data()

if not df.empty:
    # PEGA O HORÁRIO MAIS RECENTE DA COLUNA QUE CRIAMOS
    # Como salvamos como texto no passo 1, aqui ele virá exato.
    data_exibicao = df['data_fixa'].max()
    
    # Se o formato no banco for ISO (AAAA-MM-DD), ajustamos apenas a ordem visual
    if "-" in data_exibicao:
        try:
            # Converte AAAA-MM-DD HH:MM:SS para DD/MM/AAAA HH:MM:SS
            partes = data_exibicao.split(" ")
            data_br = "/".join(partes[0].split("-")[::-1])
            data_exibicao = f"{data_br} {partes[1][:8]}"
        except:
            pass

    st.markdown(f'<div class="sync-bar">● Dados Sincronizados (Brasília): {data_exibicao}</div>', unsafe_allow_html=True)

    # --- RESTO DO SEU CÓDIGO DE RANKING ---
    # (Aba PRO, TEAM, ELITE etc)
    st.success("Ranking carregado com sucesso!")
else:
    st.warning("Aguardando dados do banco...")
