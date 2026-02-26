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
# CSS CUSTOMIZADO
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .sync-bar {
        background-color: #1a7f37;
        color: white;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        border-radius: 4px;
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
        # O SEGREDO: Forçamos o banco a enviar a data como TEXTO puro (::text)
        # Isso impede que o Python tente "corrigir" o fuso horário sozinho
        query = "SELECT *, atualizado_em::text as data_texto FROM ranking_squad"
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# =============================
# INTERFACE PRINCIPAL
# =============================
st.markdown("<h1 style='text-align:center;'>🎮 Ranking Squad - Season 40</h1>", unsafe_allow_html=True)

df_bruto = get_data()

if not df_bruto.empty:
    # --- LÓGICA DE SINCRONIZAÇÃO ESTÁTICA ---
    try:
        # Pegamos o valor máximo da coluna de texto (o registro mais recente)
        horario_banco = df_bruto['data_texto'].max()
        
        # Formatamos apenas para exibição visual brasileira
        # Pegamos apenas os primeiros 19 caracteres para ignorar milissegundos
        dt_obj = datetime.strptime(horario_banco[:19], '%Y-%m-%d %H:%M:%S')
        data_exibicao = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
    except:
        data_exibicao = "Aguardando sincronização..."

    # Exibição da barra verde com o horário REAL gravado no banco
    st.markdown(f"""
        <div class="sync-bar">
            ● Última Atualização do Banco: {data_exibicao}
        </div>
    """, unsafe_allow_html=True)

    # (Início do seu processamento de ranking original)
    df_bruto = df_bruto[df_bruto['partidas'].fillna(0).astype(int) > 0].copy()
    
    # ... (Restante do seu código para as abas PRO, TEAM e ELITE)
    st.info("Dados carregados com sucesso. Navegue pelas abas acima.")

else:
    st.warning("Conectado ao banco. Nenhum dado encontrado na tabela 'ranking_squad'.")
