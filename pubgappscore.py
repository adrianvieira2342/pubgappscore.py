import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh # Agora vamos usar isso!

# =========================================================
# CONFIGURAÇÃO DE CONTROLE
# =========================================================
INTERVALO_WORKFLOW = 10 

# Faz a página resetar o relógio sozinha a cada 30 segundos
st_autorefresh(interval=30 * 1000, key="datarefresh")

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="PUBG Squad Ranking",
    layout="wide",
    page_icon="🎮",
    initial_sidebar_state="collapsed"
)

# Estilos CSS
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
    .timer-text {
        text-align: center;
        color: #ff4b4b; /* Cor em destaque para facilitar o teste */
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# FUNÇÃO DO CRONÔMETRO (SINCRO)
# =============================
def exibir_timer_atualizacao():
    # Forçamos o UTC pois o Cron do GitHub é sempre UTC
    agora = datetime.now(pytz.utc)
    
    minuto_atual = agora.minute
    segundo_atual = agora.second
    
    # Cálculo matemático puro: 
    # Se agora é :42, o resto de 42/10 é 2. 
    # 9 - 2 = 7 minutos restantes.
    minutos_restantes = (INTERVALO_WORKFLOW - 1) - (minuto_atual % INTERVALO_WORKFLOW)
    segundos_restantes = 59 - segundo_atual
    
    st.markdown(
        f"<div class='timer-text'>⏳ Próxima janela de atualização (GitHub): {minutos_restantes:02d}:{segundos_restantes:02d}</div>", 
        unsafe_allow_html=True
    )

# =============================
# INTERFACE E DADOS
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

exibir_timer_atualizacao()

st.markdown("---")

# Função de busca de dados (Mantendo seu padrão)
def get_data():
    try:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        return conn.query("SELECT * FROM ranking_squad", ttl=0)
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

df_bruto = get_data()

if not df_bruto.empty:
    # Processamento e Rankings (Igual ao seu código anterior)
    # ... [O restante do seu código de tabs e tabelas continua aqui] ...
    st.success("Dados carregados com sucesso!") # Apenas para confirmar o load
else:
    st.warning("Aguardando dados...")
