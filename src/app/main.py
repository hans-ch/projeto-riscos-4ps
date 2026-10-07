import streamlit as st
import time

# Configuração da página
st.set_page_config(
    page_title="Análise de Riscos - 4P's",
    page_icon="🛡️",
    layout="wide"
)

# Título principal
st.title("🛡️ Ferramenta de Análise de Riscos - 4P's")
st.markdown("Interface web modular para coleta de parâmetros de risco integrados ao motor **PyFAIR**.")

# Configurações globais na barra lateral
st.sidebar.header("Parâmetros do Modelo FAIR")
simulacoes = st.sidebar.slider(
    "Número de Simulações (Monte Carlo)", 
    min_value=100, 
    max_value=10000, 
    value=1000, 
    step=100
)

st.sidebar.info("Ajuste os parâmetros nos 4 pilares abaixo e clique em executar para simular o risco.")

# Organização dos 4 P's em Abas
tab1, tab2, tab3, tab4 = st.tabs(["👥 Pessoas", "⚙️ Processos", "💻 Plataformas", "📦 Produtos"])

with tab1:
    st.subheader("Pessoas (Fator Humano)")
    col1, col2 = st.columns(2)
    with col1:
        p_frequencia = st.slider("Frequência estimada de eventos de erro/ameaça (Anual)", 1, 365, 12)
    with col2:
        p_vulnerabilidade = st.slider("Taxa de vulnerabilidade humana (%)", 0, 100, 25)

with tab2:
    st.subheader("Processos (Governança e Operações)")
    col1, col2 = st.columns(2)
    with col1:
        proc_controles = st.selectbox("Eficácia dos Controles Atuais", ["Baixa", "Média", "Alta"])
    with col2:
        proc_impacto = st.number_input("Impacto Operacional Estimado (R$)", min_value=0.0, value=50000.0, step=5000.0)

with tab3:
    st.subheader("Plataformas (Tecnologia e Infraestrutura)")
    col1, col2, col3 = st.columns(3)
    with col1:
        plat_criticidade = st.selectbox("Criticidade do Ativo", ["Baixa", "Média", "Alta", "Crítica"])
    with col2:
        plat_min = st.number_input("Perda Mínima (Magnitude)", min_value=0.0, value=5000.0)
    with col3:
        plat_max = st.number_input("Perda Máxima (Magnitude)", min_value=0.0, value=200000.0)

with tab4:
    st.subheader("Produtos (Negócio e Mercado)")
    col1, col2 = st.columns(2)
    with col1:
        prod_exposicao = st.slider("Grau de Exposição ao Mercado", 1, 5, 3)
    with col2:
        prod_sensivel = st.checkbox("O produto manipula dados sensíveis (LGPD/PII)?")

st.markdown("---")

# Botão de Execução
if st.button("🚀 Executar Análise de Risco (PyFAIR)", type="primary"):
    
    # Estruturando os dados consolidados para repassar ao motor pyfair
    dados_pyfair = {
        "configuracoes": {
            "simulacoes": simulacoes
        },
        "pilares_4ps": {
            "pessoas": {
                "frequencia_ameaca": p_frequencia,
                "vulnerabilidade": p_vulnerabilidade
            },
            "processos": {
                "eficacia_controles": proc_controles,
                "impacto_financeiro": proc_impacto
            },
            "plataformas": {
                "criticidade": plat_criticidade,
                "perda_minima": plat_min,
                "perda_maxima": plat_max
            },
            "produtos": {
                "exposicao": prod_exposicao,
                "dados_sensiveis": prod_sensivel
            }
        }
    }
    
    # Feedback visual de processamento
    with st.spinner("Repassando dados e executando motor PyFAIR..."):
        time.sleep(1.5) # Simulação de processamento do motor
        
    st.success("Análise concluída com sucesso pelo motor!")
    
    # Exemplo de exibição de resultados simulados
    st.subheader("Resultados Preliminares da Análise de Risco")
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Risco Anual Esperado (ALE)", "R$ 112.450,00", "-8.2%")
    res_col2.metric("Frequência de Perda (LEF)", "1.8 / ano", "Estável")
    res_col3.metric("Magnitude de Perda (LM)", "R$ 62.000,00", "+2.5%")
    
    # Seção para debug ou verificação do payload enviado ao PyFAIR
    with st.expander("🔍 Ver Payload JSON enviado ao PyFAIR"):
        st.json(dados_pyfair)