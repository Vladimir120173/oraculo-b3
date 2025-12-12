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
        /* 1. Fundo com Degradê Tecnológico Suave */
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
            background-color: #ffffff;
            border-right: 1px solid #ddd;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-top: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        /* 4. Esconder itens padrão */
        .stDeployButton {display:none;}
        header {visibility: hidden;}
        
        /* 5. Tabela Bonita */
        .tabela-bonita {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            background-color: white;
            border-radius: 10px;
            overflow: hidden;
        }
        .tabela-bonita th {
            background-color: #2c3e50;
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
        
        /* 6. AJUSTE DO BOTÃO */
        div.stButton > button {
            margin-top: 28px; 
            background-color: #f1f3f5;
            color: #2c3e50;
            border: 1px solid #ced4da;
            font-weight: 600;
            border-radius: 6px;
            padding-left: 15px;
            padding-right: 15px;
            transition: all 0.3s;
            white-space: nowrap; 
            min-width: 160px;
            width: auto;
        }
        div.stButton > button:hover {
            background-color: #e2e6ea;
            border-color: #adb5bd;
            color: #000;
        }

        /* 7. BORDA NO GRÁFICO */
        [data-testid="stPlotlyChart"] {
            border: 1px solid #ccc;
            border-radius: 8px;
            background-color: white;
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* 8. BORDA NOS CAMPOS DE DATA */
        div[data-baseweb="input"] {
            border: 1px solid #ccc !important;
            border-radius: 6px !important;
            background-color: white !important;
        }
        div[data-testid="stDateInput"] > div {
            border: none !important;
        }

        /* 9. CURSOR DO GRÁFICO (Sem Cruz) */
        .js-plotly-plot .plotly .drag, 
        .js-plotly-plot .plotly .drag:active,
        .js-plotly-plot .plotly .cursor-move,
        .js-plotly-plot .plotly .cursor-crosshair {
            cursor: default !important;
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
    col_logo.image("logo.svg", width=200)
elif os.path.exists("logo.png"):
    col_logo.image("logo.png", width=200)
else:
    st.sidebar.markdown("## 🦅 Ausdauer Tech")

st.sidebar.markdown("---")

st.sidebar.markdown("""
    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #444;">
        🔍 Filtros
    </div>
""", unsafe_allow_html=True)

# 1. Selecione o Ativo
idx = 0
if any("PETR4.SA" in s for s in lista_tickers):
    idx = [i for i, s in enumerate(lista_tickers) if "PETR4.SA" in s][0]

selecao_padrao = st.sidebar.selectbox("Selecione o Ativo:", lista_tickers, index=idx)

# 2. Checkbox manual
usar_manual = st.sidebar.checkbox("Não encontrei meu ativo")

# Lógica de definição do ticker
if usar_manual:
    entrada = st.sidebar.text_input("Digite o código (ex: MGLU3):", "").upper().strip()
    ticker_final = f"{entrada}.SA" if entrada and not entrada.endswith(".SA") and not entrada.startswith("^") else entrada
else:
    ticker_final = selecao_padrao.split(" - ")[0] if selecao_padrao else None

# -----------------------------------------------------------------------------
# 4. CORPO PRINCIPAL
# -----------------------------------------------------------------------------
if ticker_final:
    
    with st.spinner("Carregando..."):
        try:
            # CORREÇÃO 1: auto_adjust=False (Para bater os centavos com o Advfn)
            dados_completos = yf.download(ticker_final, period="5y", progress=False, auto_adjust=False)
            
            if isinstance(dados_completos.columns, pd.MultiIndex): 
                dados_completos.columns = dados_completos.columns.droplevel(1)

            if not dados_completos.empty:
                
                # --- CORREÇÃO 2: VACINA CONTRA DADOS ZERADOS DO YAHOO ---
                # Se a abertura for 0, copiamos o fechamento para Abertura, Máxima e Mínima
                ult_idx = dados_completos.index[-1]
                if dados_completos.at[ult_idx, 'Open'] <= 0.01: # Verifica se é zero ou quase zero
                    preco_corrigido = dados_completos.at[ult_idx, 'Close']
                    dados_completos.at[ult_idx, 'Open'] = preco_corrigido
                    dados_completos.at[ult_idx, 'High'] = preco_corrigido
                    dados_completos.at[ult_idx, 'Low'] = preco_corrigido
                
                # --- CABEÇALHO ---
                col_titulo, col_btn = st.columns([4, 1])
                
                with col_titulo:
                    st.markdown(f"## Análise de: **{ticker_final}**")
                
                with col_btn:
                    if st.button("🔄 Atualizar Cotação", use_container_width=True):
                        st.cache_data.clear()
                        st.rerun()

                atual = dados_completos["Close"].iloc[-1]
                anterior = dados_completos["Close"].iloc[-2]
                var = ((atual - anterior) / anterior) * 100
                cor_var = "green" if var >= 0 else "red"
                seta = "▲" if var >= 0 else "▼"
                
                # Cotação do Dia
                st.markdown(
                    f"""
                    <div style="margin-top: -10px; margin-bottom: 20px;">
                        <span style="font-size: 20px; color: #2c3e50; font-weight: bold; margin-right: 10px;">Cotação do dia:</span>
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
                
                col_d1, col_d2, col_vazia = st.columns([2, 2, 6])
                inicio_padrao = datetime(2022, 1, 1).date()
                fim_padrao = datetime.now().date()
                
                with col_d1:
                    data_ini = st.date_input("Data Inicial", value=inicio_padrao, format="DD/MM/YYYY")
                with col_d2:
                    data_fim = st.date_input("Data Final", value=fim_padrao, format="DD/MM/YYYY")

                if data_fim > datetime.now().date():
                    st.warning("⚠️ Atenção: A data final selecionada ainda não aconteceu. Exibindo dados até o dia de hoje.")

                dados_filtrados = dados_completos.loc[str(data_ini):str(data_fim)]

                # --- GRÁFICO ---
                st.markdown('<div class="titulo-secao">Gráfico de Evolução (Candlestick)</div>', unsafe_allow_html=True)
                
                if not dados_filtrados.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=dados_filtrados.index,
                        open=dados_filtrados['Open'], high=dados_filtrados['High'],
                        low=dados_filtrados['Low'], close=dados_filtrados['Close'],
                        name=ticker_final
                    )])
                    
                    fig.update_xaxes(showspikes=False)
                    fig.update_yaxes(showspikes=False)
                    
                    fig.update_layout(
                        hovermode='x unified', 
                        height=550, 
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis_rangeslider_visible=False,
                        dragmode='pan', 
                        yaxis=dict(fixedrange=False), 
                        xaxis=dict(tickformat="%d/%m/%Y"),
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não há dados para exibir neste intervalo.")

                # --- TABELA DETALHADA ---
                st.markdown("---")
                
                if st.checkbox("Exibir Tabela Detalhada", value=True):
                    st.markdown('<div class="titulo-secao">📋 Últimos Negócios</div>', unsafe_allow_html=True)
                    
                    if not dados_filtrados.empty:
                        df_show = dados_filtrados.tail(5).copy()
                        
                        df_show = df_show[['Open', 'High', 'Low', 'Close', 'Volume']]
                        df_show = df_show.reset_index()
                        df_show.columns = ['Data', 'Abertura', 'Máxima', 'Mínima', 'Fechamento', 'Volume']
                        
                        df_show = df_show.sort_values(by="Data", ascending=False)
                        
                        df_show['Data'] = df_show['Data'].dt.strftime('%d/%m/%Y')
                        
                        def fmt(x): return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        def fmt_vol(x): return f"{x:,.0f}".replace(",", ".")

                        for c in ['Abertura', 'Máxima', 'Mínima', 'Fechamento']:
                            df_show[c] = df_show[c].apply(fmt)
                        df_show['Volume'] = df_show['Volume'].apply(fmt_vol)
                        
                        html_tabela = df_show.to_html(classes="tabela-bonita", border=0, index=False)
                        st.markdown(html_tabela, unsafe_allow_html=True)
                    else:
                        st.info("O intervalo selecionado não possui dados suficientes para a tabela.")

            else:
                st.warning("Dado não encontrado.")
        except Exception as e:
            st.error(f"Erro: {e}")
else:
    st.info("Selecione um ativo.")