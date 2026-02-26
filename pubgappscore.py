import streamlit as st
import pandas as pd
from datetime import datetime

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮",
    initial_sidebar_state="collapsed"
)

# =============================
# CSS TEMA ESCURO CUSTOM
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
    }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

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
        # Forçamos a coluna a vir como TEXTO puro para o Streamlit não mexer no fuso
        query = "SELECT *, atualizado_em::text as data_estatica FROM ranking_squad"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

# =============================
# INTERFACE
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data()

if not df_bruto.empty:
    # --- BUSCA O HORÁRIO REAL DO BANCO ---
    try:
        # Pega o valor máximo (mais recente) registrado na coluna de texto
        ultima_data_banco = df_bruto['data_estatica'].max()
        
        # Formata para o padrão visual brasileiro
        dt_limpa = datetime.strptime(ultima_data_banco[:19], '%Y-%m-%d %H:%M:%S')
        data_exibicao = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
    except:
        data_exibicao = "Aguardando sincronização..."

    # Barra Verde com o horário FIXO que veio do banco
    st.markdown(f"""
        <div class="sync-bar">
            ● Última Atualização do Banco: {data_exibicao}
        </div>
    """, unsafe_allow_html=True)

    # (Início do Processamento de Ranking)
    df_bruto = df_bruto[df_bruto['partidas'] > 0].copy()
    # ... Resto do seu código de processamento de tabs e ranking ...
    
    st.info("Dados carregados com sucesso. Selecione uma aba acima para ver o ranking.")

else:
    st.warning("Sem dados para exibir.")
