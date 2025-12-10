import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Oráculo B3", page_icon="🦅", layout="wide")

st.markdown("""
    <style>
        /* 1. Fundo com Degradê Tecnológico Suave (Ausdauer Tech Style) */
        .stApp {
            background: linear-gradient(to right, #f8f9fa, #e9ecef);
        }

        /* 2. Ajuste do Topo */
        .block-container {
            padding-top: 3rem; 
            padding-bottom: 2rem;
        }
        
        /* 3. Barra Lateral */
        section[data-testid="stSidebar"] {
            background-color: #ffffff; /* Branco puro para destacar do fundo */
            border-right: 1px solid #ddd;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-top: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        /* 4. Esconder botão de Deploy e Menu (Deixar limpo) */
        .stDeployButton {display:none;}
        header {visibility: hidden;}
        
        /* 5. Tabela HTML */
        .tabela-bonita {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Sombra suave */
            background-color: white;
            border-radius: 10px;
            overflow: hidden;
        }
        .tabela-bonita th {
            background-color: #2c3e50; /* Azul Escuro Executivo */
            color: white;
            font-weight: bold;
            text-align: center !important;
            padding: 12px;
        }
        .tabela-bonita td {
            text-align: center !important;
            padding: 10px;
            border-bottom: 1px solid #eee;
            color: #333;
        }
        .tabela-bonita tr:hover {
            background-color: #f1f1f1;
        }
        
        .titulo-secao {
            font-size: 18px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #2c3e50;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. O ROBÔ (BACKEND)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def carregar_tickers_fundamentus():
    url = "https://www.fundamentus.com.br/detalhes.php"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        tabelas = pd.read_html(response.content)
        df = tabelas[0]
        lista = [f"{row['Papel']}.SA - {row['Nome Comercial']}" for _, row in df.iterrows()]
        lista.append("^BVSP - IBOVESPA")
        return sorted(list(set(lista)))
    except Exception:
        backup = ["ABEV3.SA - AMBEV", "BBAS3.SA - BANCO DO BRASIL", "ITUB4.SA - ITAU", 
                  "PETR4.SA - PETROBRAS", "VALE3.SA - VALE", "^BVSP - IBOVESPA"]
        return sorted(backup)

lista_tickers = carregar_tickers_fundamentus()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL
# -----------------------------------------------------------------------------
col_logo, _ = st.sidebar.columns([1, 0.1])
if os.path.exists("logo.svg"):
    col_logo.image("logo.svg", width=160)
elif os.path.exists("logo.png"):
    col_logo.image("logo.png", width=160)
else:
    st.sidebar.markdown("## 🦅 Ausdauer Tech")

st.sidebar.markdown("---")
st.sidebar.title("🔍 Filtros")

container_input = st.sidebar.empty()
usar_manual = st.sidebar.checkbox("Não encontrei meu ativo (Digitar Manualmente)")

if usar_manual:
    entrada = container_input.text_input("Digite o código:", "").upper().strip()
    ticker_final = f"{entrada}.SA" if entrada and not entrada.endswith(".SA") and not entrada.startswith("^") else entrada
else:
    idx = 0
    if any("PETR4.SA" in s for s in lista_tickers):
        idx = [i for i, s in enumerate(lista_tickers) if "PETR4.SA" in s][0]
    selecao = container_input.selectbox("Selecione o Ativo:", lista_tickers, index=idx)
    ticker_final = selecao.split(" - ")[0] if selecao else None

# -----------------------------------------------------------------------------
# 4. CORPO PRINCIPAL
# -----------------------------------------------------------------------------
if ticker_final:
    
    with st.spinner("Carregando..."):
        try:
            dados_completos = yf.download(ticker_final, period="5y", progress=False)
            if isinstance(dados_completos.columns, pd.MultiIndex): 
                dados_completos.columns = dados_completos.columns.droplevel(1)

            if not dados_completos.empty:
                
                # --- CABEÇALHO ---
                atual = dados_completos["Close"].iloc[-1]
                anterior = dados_completos["Close"].iloc[-2]
                var = ((atual - anterior) / anterior) * 100
                cor_var = "green" if var >= 0 else "red"
                seta = "▲" if var >= 0 else "▼"

                st.markdown(f"## Análise de: **{ticker_final}**")
                
                st.markdown(
                    f"""
                    <div style="margin-top: -10px; margin-bottom: 20px;">
                        <span style="font-size: 28px; font-weight: normal;">R$ {atual:.2f}</span>
                        <span style="color: {cor_var}; font-size: 18px; margin-left: 10px; background-color: #e8f5e9; padding: 5px; border-radius: 5px;">
                            {seta} {var:.2f}%
                        </span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

                # --- SELETOR DE DATAS ---
                st.markdown('<div class="titulo-secao">Período de Análise</div>', unsafe_allow_html=True)
                
                col_d1, col_d2, col_vazia = st.columns([1, 1, 2])
                inicio_padrao = datetime(2022, 1, 1).date()
                fim_padrao = datetime.now().date()
                
                with col_d1:
                    data_ini = st.date_input("Data Inicial", value=inicio_padrao, format="DD/MM/YYYY")
                with col_d2:
                    data_fim = st.date_input("Data Final", value=fim_padrao, format="DD/MM/YYYY")

                dados_filtrados = dados_completos.loc[str(data_ini):str(data_fim)]

                # --- GRÁFICO (MODO PAN + MARGEM NO TOPO) ---
                st.markdown('<div class="titulo-secao">Gráfico de Evolução (Candlestick)</div>', unsafe_allow_html=True)
                
                c_esq, c_centro, c_dir = st.columns([0.5, 6, 0.5])
                with c_centro:
                    fig = go.Figure(data=[go.Candlestick(
                        x=dados_filtrados.index,
                        open=dados_filtrados['Open'], high=dados_filtrados['High'],
                        low=dados_filtrados['Low'], close=dados_filtrados['Close'],
                        name=ticker_final
                    )])
                    
                    fig.update_layout(
                        height=450, 
                        # Aumentei o 't' (top) para 50px. Isso empurra o gráfico pra baixo,
                        # abrindo espaço para os botões do Plotly não ficarem em cima.
                        margin=dict(l=0, r=0, t=50, b=0), 
                        xaxis_rangeslider_visible=False,
                        dragmode='pan', 
                        yaxis=dict(fixedrange=False), 
                        xaxis=dict(tickformat="%d/%m/%Y"),
                        paper_bgcolor='rgba(0,0,0,0)', # Fundo transparente para pegar o degradê
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # --- TABELA (A MORTE DO 'PRICE') ---
                st.markdown("---")
                
                if st.checkbox("Exibir Tabela Detalhada", value=True):
                    st.markdown('<div class="titulo-secao">📋 Últimos Negócios</div>', unsafe_allow_html=True)
                    
                    df_show = dados_completos.tail(5).copy()
                    
                    # 1. Reset Index
                    df_show = df_show.reset_index()
                    
                    # 2. SOBRESCRITA TOTAL DOS NOMES DAS COLUNAS
                    # Não renomeamos. Nós IMPOMOS os nomes pela ordem das colunas.
                    # Isso garante que a primeira coluna seja 'Data', a segunda 'Abertura', etc.
                    # Eliminando qualquer chance de 'Price' sobreviver.
                    df_show.columns = ['Data', 'Abertura', 'Máxima', 'Mínima', 'Fechamento', 'Volume']
                    
                    # 3. Formatação
                    df_show['Data'] = df_show['Data'].dt.strftime('%d/%m/%Y')
                    
                    def fmt(x): return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    def fmt_vol(x): return f"{x:,.0f}".replace(",", ".")

                    for c in ['Abertura', 'Máxima', 'Mínima', 'Fechamento']:
                        df_show[c] = df_show[c].apply(fmt)
                    df_show['Volume'] = df_show['Volume'].apply(fmt_vol)
                    
                    # 4. Renderiza
                    html_tabela = df_show.to_html(classes="tabela-bonita", border=0, index=False)
                    st.markdown(html_tabela, unsafe_allow_html=True)

            else:
                st.warning("Dado não encontrado.")
        except Exception as e:
            st.error(f"Erro: {e}")
else:
    st.info("Selecione um ativo.")