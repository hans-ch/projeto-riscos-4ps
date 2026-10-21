import streamlit as st
from pathlib import Path
import sqlite3
from datetime import date
import numpy as np
import pandas as pd
import io

# Compatibilidade: PyFAIR usa applymap, removido no pandas 3.0
if not hasattr(pd.DataFrame, "applymap"):
    pd.DataFrame.applymap = pd.DataFrame.map

from pyfair import FairModel, FairMetaModel, FairSimpleReport

# ==========================================
# CONFIGURAÇÕES INICIAIS STREAMLIT
# ==========================================
st.set_page_config(page_title="Análise FAIR - Riscos", layout="wide")
st.markdown(
    """
    <style>
        :root {
            --pine: #174b40;
            --pine-deep: #10372f;
            --ink: #1c302b;
            --muted: #66756f;
            --paper: #ffffff;
            --canvas: #eef3f0;
            --line: #d8e2dc;
            --coral: #e47756;
            --gold: #d9ad5b;
        }

        [data-testid="stAppViewContainer"] {
            color: var(--ink);
            background: linear-gradient(145deg, #f5f7f4 0%, var(--canvas) 62%, #e8efeb 100%);
        }

        [data-testid="stHeader"] { background: transparent; }

        [data-testid="stMainBlockContainer"] {
            max-width: 1480px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(255, 255, 255, 0.12);
            background: linear-gradient(165deg, #153d35 0%, #102f2a 100%);
        }

        [data-testid="stSidebar"] > div:first-child { background: transparent; }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: #f4f6f1; }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label { color: #c7d5ce; }

        [data-testid="stSidebar"] button[kind="primary"] {
            min-height: 48px;
            border: 0;
            border-radius: 4px;
            background: var(--coral);
            color: white;
            font-weight: 700;
        }

        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background: #d76546;
            color: white;
        }

        .app-masthead {
            position: relative;
            overflow: hidden;
            padding: 30px 36px 32px;
            border-bottom: 5px solid var(--coral);
            border-radius: 6px;
            background: linear-gradient(112deg, #123b33 0%, #1b584b 72%, #276b5d 100%);
            color: white;
        }

        .app-masthead::after {
            position: absolute;
            top: 0;
            right: 10%;
            width: 1px;
            height: 100%;
            background: rgba(255, 255, 255, 0.12);
            content: "";
        }

        .app-kicker {
            margin: 0 0 10px;
            color: #e7bc78;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.4px;
            text-transform: uppercase;
        }

        .app-masthead h1 {
            margin: 0;
            color: #fff;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 38px;
            font-weight: 400;
            line-height: 1.15;
        }

        .app-masthead p:last-child {
            margin: 10px 0 0;
            color: #d5e1db;
            font-size: 14px;
        }

        .app-meta-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 10px 32px;
            padding: 14px 4px 16px;
            border-bottom: 1px solid var(--line);
            color: var(--muted);
            font-size: 12px;
        }

        .app-meta-strip strong {
            margin-left: 6px;
            color: var(--ink);
            font-weight: 650;
        }

        [data-testid="stMetric"] {
            min-height: 112px;
            padding: 17px 18px;
            border: 1px solid var(--line);
            border-top: 3px solid var(--pine);
            border-radius: 4px;
            background: var(--paper);
        }

        [data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-size: 12px;
            font-weight: 650;
        }

        [data-testid="stMetricValue"] {
            color: var(--pine-deep);
            font-family: Georgia, "Times New Roman", serif;
        }

        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 4px;
            background: var(--paper);
        }

        [data-testid="stAlert"] { border-radius: 4px; }

        .empty-state {
            display: flex;
            align-items: center;
            gap: 18px;
            margin-top: 24px;
            padding: 24px;
            border: 1px solid var(--line);
            border-left: 4px solid var(--gold);
            background: rgba(255, 255, 255, 0.75);
        }

        .empty-state-mark {
            color: var(--coral);
            font-family: Georgia, "Times New Roman", serif;
            font-size: 32px;
        }

        .empty-state strong { color: var(--pine-deep); }
        .empty-state p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }

        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 2rem; }
            .app-masthead { padding: 24px 20px; }
            .app-masthead h1 { font-size: 30px; }
            .app-masthead::after { right: 7%; }
            .app-meta-strip { gap: 8px 18px; }
            .empty-state { align-items: flex-start; padding: 18px; }
        }
    </style>

    <div class="app-masthead">
        <p class="app-kicker">Segurança operacional / OpenFAIR</p>
        <h1>Risco em perspectiva</h1>
        <p>Análise quantitativa de exposição, controles e perda residual.</p>
    </div>
    <div class="app-meta-strip">
        <span>MODELO<strong>FAIR</strong></span>
        <span>SIMULAÇÕES<strong>10.000 por risco</strong></span>
        <span>FONTE<strong>Base SQLite local</strong></span>
    </div>
    """,
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
PASTA_DB = BASE_DIR / "DataBase.db"
CSS_RELATORIO = """
<style>
    :root { --forest: #174f45; --ink: #173c35; --mint: #e8f1ed; --line: #dce5df; --coral: #e77b5b; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f2f5f2; color: var(--ink); font: 15px/1.55 "Segoe UI", sans-serif; }
    #main { display: flex; flex-direction: column; gap: 18px; width: min(100% - 40px, 1440px); margin: 24px auto 48px; }
    #band { display: flex; align-items: center; min-height: 130px; padding: 24px 32px; background: #103a34; border-bottom: 5px solid var(--coral); border-radius: 8px; }
    #python_image_container { height: 52px; }
    #python_image_container img { height: 100%; padding-left: 0; }
    #title { color: white; font: 38px Georgia, serif; text-align: left; }
    #metadata_table { align-self: flex-end; padding: 12px 20px; background: white; border: 1px solid var(--line); border-radius: 6px; }
    .fair_metadata_table { margin: 0; color: var(--ink); font-size: 13px; }
    .fair_metadata_table th { padding-right: 16px; color: #64746f; text-align: left; }
    .separator { width: 100%; padding: 10px 18px; background: var(--forest); border-left: 5px solid var(--coral); border-radius: 4px; }
    .separator p { margin: 0; color: white; font: 22px Georgia, serif; }
    .flex_row { display: flex; gap: 18px; width: 100%; padding-bottom: 8px; overflow-x: auto; }
    #main > div:not(#band):not(#metadata_table):not(.separator) { max-width: 100%; overflow-x: auto; }
    table { border-collapse: collapse; background: white; color: var(--ink); font-size: 13px; }
    .fair_table { border: 1px solid var(--line); border-radius: 6px; font-variant-numeric: tabular-nums; }
    .fair_table td, .fair_table th, table.dataframe td, table.dataframe th { padding: 9px 12px; border-bottom: 1px solid var(--line); }
    .fair_table thead th, table.dataframe thead th { background: var(--mint); color: var(--forest); }
    .fair_table th { text-align: left; }
    .fair_table tr:nth-child(even), table.dataframe tr:nth-child(even) { background: #f7f9f7; }
    .fair_table td img, img { max-width: 100%; height: auto; }
    h1 { color: var(--forest); font: 26px Georgia, serif; }
    @media (max-width: 700px) {
        #main { width: calc(100% - 24px); margin: 12px auto 32px; gap: 14px; }
        #band { min-height: 105px; padding: 18px; }
        #title { padding-left: 12px; font-size: 30px; }
    }
</style>
"""

# ---------------------------------------------------------
# PARÂMETROS DA ANÁLISE
# ---------------------------------------------------------
FREQUENCIA = {
    1: (0.01, 0.03, 0.10),
    2: (0.05, 0.15, 0.40),
    3: (0.20, 0.60, 1.50),
    4: (0.80, 2.00, 4.00),
    5: (2.00, 5.00, 12.00),
}

PERDA = {
    1: (1_000,     5_000,    20_000),
    2: (5_000,     25_000,   100_000),
    3: (30_000,    120_000,  500_000),
    4: (150_000,   600_000,  2_500_000),
    5: (500_000,   2_500_000, 10_000_000),
}

REDUCAO_POR_STATUS = {"Concluída": 0.30, "Em andamento": 0.10, "Pendente": 0.0}
REDUCAO_MAXIMA = 0.70
LIMITE_ALTO = 200_000
LIMITE_MEDIO = 50_000
N_SIMULACOES = 10_000

# ---------------------------------------------------------
# FUNÇÕES DE BANCO DE DADOS E LÓGICA
# ---------------------------------------------------------
@st.cache_resource
def init_db():
    conn = sqlite3.connect(PASTA_DB)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT,
            setor TEXT
        );

        CREATE TABLE IF NOT EXISTS riscos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            severidade INTEGER,
            probabilidade INTEGER
        );

        CREATE TABLE IF NOT EXISTS analises_risco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risco_id INTEGER,
            pessoa_id INTEGER,
            data_analise TEXT NOT NULL,
            nivel_risco_calculado INTEGER,
            status TEXT,
            FOREIGN KEY (risco_id) REFERENCES riscos(id),
            FOREIGN KEY (pessoa_id) REFERENCES pessoas(id)
        );

        CREATE TABLE IF NOT EXISTS medidas_controle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risco_id INTEGER,
            acao TEXT NOT NULL,
            responsavel_id INTEGER,
            prazo TEXT,
            status_acao TEXT,
            FOREIGN KEY (risco_id) REFERENCES riscos(id),
            FOREIGN KEY (responsavel_id) REFERENCES pessoas(id)
        );

        CREATE TABLE IF NOT EXISTS resultados_fair (
            risco_id INTEGER PRIMARY KEY,
            data_execucao TEXT,
            perda_media_inerente REAL,
            perda_media_residual REAL,
            p95_residual REAL,
            classificacao_fair TEXT,
            FOREIGN KEY (risco_id) REFERENCES riscos(id)
        );
    """)
    conn.commit()
    
    # Inserir dados fictícios se vazio
    if cursor.execute("SELECT COUNT(*) FROM riscos").fetchone()[0] == 0:
        cursor.executemany("INSERT INTO pessoas (nome, cargo, setor) VALUES (?,?,?)", [
            ("Ana Souza",    "Técnica de Segurança", "SST"),
            ("Carlos Lima",  "Engenheiro",           "Manutenção"),
            ("Marina Alves", "Supervisora",          "Produção"),
            ("João Pereira", "Gerente",              "Operações"),
        ])

        cursor.executemany("INSERT INTO riscos (titulo, descricao, categoria, severidade, probabilidade) VALUES (?,?,?,?,?)", [
            ("Trabalho em altura > 10 m",  "Queda em serviços de fachada e telhado", "Queda",       5, 3),
            ("Espaço confinado",           "Tanque sem ventilação adequada",         "Atmosfera",   5, 2),
            ("Choque elétrico",            "Painéis de 440V (NR-10)",                "Elétrico",    4, 3),
            ("Atropelamento empilhadeira", "Tráfego misto pedestres/veículos",       "Mecânico",    3, 4),
            ("Exposição a solventes",      "Manuseio sem ventilação local",          "Químico",     3, 3),
            ("Ruído acima de 85 dB",       "Setor de prensas sem protetor",          "Físico",      2, 4),
            ("Movimento repetitivo",       "Linha de montagem",                      "Ergonômico",  2, 5),
            ("Incêndio em depósito",       "Armazenamento de inflamáveis",           "Incêndio",    5, 1),
        ])

        hoje = date.today().isoformat()
        cursor.executemany("INSERT INTO analises_risco (risco_id, pessoa_id, data_analise, nivel_risco_calculado, status) VALUES (?,?,?,?,?)", [
            (1, 1, hoje, 15, "Concluída"), (2, 1, hoje, 10, "Concluída"),
            (3, 2, hoje, 12, "Concluída"), (4, 3, hoje, 12, "Concluída"),
            (5, 3, hoje,  9, "Concluída"), (6, 3, hoje,  8, "Concluída"),
            (7, 3, hoje, 10, "Concluída"), (8, 4, hoje,  5, "Concluída"),
        ])

        cursor.executemany("INSERT INTO medidas_controle (risco_id, acao, responsavel_id, prazo, status_acao) VALUES (?,?,?,?,?)", [
            (1, "Instalar linha de vida",        1, "2026-12-01", "Concluída"),
            (1, "Treinamento NR-35",             1, "2026-11-15", "Em andamento"),
            (2, "Exaustor e detector de gases",  2, "2026-12-20", "Em andamento"),
            (3, "Bloqueio e etiquetagem (LOTO)", 2, "2026-10-30", "Concluída"),
            (4, "Sinalização e faixa de pedestres", 3, "2026-10-20", "Concluída"),
            (4, "Sensor de proximidade",         3, "2027-01-10", "Pendente"),
            (5, "Exaustão localizada",           2, "2027-02-01", "Pendente"),
            (6, "Fornecer protetor auricular",   3, "2026-09-30", "Concluída"),
            (8, "Sistema de sprinklers",         4, "2027-03-01", "Em andamento"),
        ])
        conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# INTERFACE STREAMLIT
# ---------------------------------------------------------
st.sidebar.markdown("### Central de análise")
st.sidebar.caption("Carteira de riscos · 4Ps")
st.sidebar.markdown("---")
if st.sidebar.button("Executar simulação", type="primary"):
    
    with st.spinner(f"Processando {N_SIMULACOES} cenários para cada risco..."):
        conn = sqlite3.connect(PASTA_DB)
        riscos = pd.read_sql("SELECT id, titulo, categoria, severidade, probabilidade FROM riscos", conn)
        controles = pd.read_sql("SELECT risco_id, status_acao FROM medidas_controle", conn)

        def reducao_de_frequencia(risco_id):
            status = controles.loc[controles["risco_id"] == risco_id, "status_acao"]
            total = sum(REDUCAO_POR_STATUS.get(s, 0.0) for s in status)
            return min(total, REDUCAO_MAXIMA)

        def construir_modelo(nome, probabilidade, severidade, fator_frequencia=1.0):
            f = FREQUENCIA[int(probabilidade)]
            p = PERDA[int(severidade)]
            m = FairModel(name=nome, n_simulations=N_SIMULACOES, random_seed=42)
            m.input_data("Loss Event Frequency", low=f[0]*fator_frequencia, mode=f[1]*fator_frequencia, high=f[2]*fator_frequencia)
            m.input_data("Loss Magnitude", low=p[0], mode=p[1], high=p[2])
            m.calculate_all()
            return m

        def classificar_fair(perda_media):
            if perda_media >= LIMITE_ALTO: return "Alto"
            if perda_media >= LIMITE_MEDIO: return "Médio"
            return "Baixo"

        def classificar_matriz(nivel):
            if nivel >= 15: return "Alto"
            if nivel >= 8: return "Médio"
            return "Baixo"

        linhas = []
        modelos_residuais = []

        for _, r in riscos.iterrows():
            reducao = reducao_de_frequencia(r["id"])
            inerente = construir_modelo(f"{r['id']} Inerente", r["probabilidade"], r["severidade"])
            residual = construir_modelo(f"{r['id']} Residual", r["probabilidade"], r["severidade"], fator_frequencia=1 - reducao)
            modelos_residuais.append(residual)

            risco_in = inerente.export_results()["Risk"]
            risco_re = residual.export_results()["Risk"]
            nivel_matriz = int(r["severidade"]) * int(r["probabilidade"])

            linhas.append({
                "id": int(r["id"]),
                "Risco": r["titulo"],
                "Categoria": r["categoria"],
                "Matriz (SxP)": f"{nivel_matriz} - {classificar_matriz(nivel_matriz)}",
                "Redução controles": f"{reducao:.0%}",
                "Perda inerente (R$/ano)": round(risco_in.mean()),
                "Perda residual (R$/ano)": round(risco_re.mean()),
                "P95 residual (R$)": round(np.percentile(risco_re, 95)),
                "Classif. FAIR": classificar_fair(risco_re.mean()),
            })

        resultado = pd.DataFrame(linhas).sort_values("Perda residual (R$/ano)", ascending=False).reset_index(drop=True)

        # Risco Total Residual
        meta = FairMetaModel(name="Risco total residual", models=modelos_residuais)
        meta.calculate_all()
        total = meta.export_results()["Risk"]

        soma_inerente = resultado["Perda inerente (R$/ano)"].sum()
        soma_residual = resultado["Perda residual (R$/ano)"].sum()
        p95_total = np.percentile(total, 95)
        reducao_geral = 1 - soma_residual / soma_inerente if soma_inerente > 0 else 0

        # Gravar no Banco de Dados
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resultados_fair")
        cursor.executemany(
            """INSERT INTO resultados_fair (risco_id, data_execucao, perda_media_inerente, perda_media_residual, p95_residual, classificacao_fair)
               VALUES (?,?,?,?,?,?)""",
            [(int(x["id"]), date.today().isoformat(), float(x["Perda inerente (R$/ano)"]), float(x["Perda residual (R$/ano)"]), float(x["P95 residual (R$)"]), x["Classif. FAIR"]) for _, x in resultado.iterrows()]
        )
        conn.commit()
        conn.close()

        # Gerar Relatório HTML
        destino = BASE_DIR / "relatorio_fair.html"
        try:
            FairSimpleReport(modelos_residuais).to_html(str(destino))
            html_msg = "✅ Relatório PyFAIR avançado gerado com sucesso."
        except Exception as e:
            resultado.to_html(str(destino), index=False, border=1)
            html_msg = f"⚠️ Relatório PyFAIR falhou, HTML alternativo gerado ({e})."

        html = destino.read_text(encoding="utf-8")
        if "</head>" in html:
            html = html.replace("</head>", f"{CSS_RELATORIO}</head>", 1)
        else:
            html = f"<!doctype html><html><head><meta charset='utf-8'>{CSS_RELATORIO}</head><body>{html}</body></html>"
        destino.write_text(html, encoding="utf-8")

    # ==========================================
    # APRESENTAÇÃO DOS DADOS NA TELA
    # ==========================================
    st.success("Análise OpenFAIR concluída e salva no banco de dados SQLite!")
    
    st.header("Resumo de exposição")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Perda Inerente (Ano)", f"R$ {soma_inerente:,.0f}".replace(',','.'))
    col2.metric("Perda Residual (Ano)", f"R$ {total.mean():,.0f}".replace(',','.'))
    col3.metric("Pior Cenário (P95)", f"R$ {p95_total:,.0f}".replace(',','.'))
    col4.metric("Redução Pelos Controles", f"{reducao_geral:.1%}")

    st.divider()

    st.header("Riscos priorizados")
    
    # Formatação visual da tabela no Streamlit
    st.dataframe(
        resultado.style.format({
            "Perda inerente (R$/ano)": "R$ {:,.0f}",
            "Perda residual (R$/ano)": "R$ {:,.0f}",
            "P95 residual (R$)": "R$ {:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.info(html_msg)

    excel_buffer = io.BytesIO()
    resultado.to_excel(excel_buffer, index=False, sheet_name="Riscos FAIR")
    excel_buffer.seek(0)

    col_html, col_excel = st.columns(2)
    with col_html:
        with open(destino, "rb") as file:
            st.download_button(
                label="📄 Baixar Relatório HTML Completo",
                data=file,
                file_name="relatorio_fair.html",
                mime="text/html"
            )

    with col_excel:
        st.download_button(
            label="📊 Baixar Excel",
            data=excel_buffer.getvalue(),
            file_name="relatorio_fair.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.markdown(
        """
        <div class="empty-state">
            <span class="empty-state-mark">01</span>
            <div>
                <strong>Carteira pronta para análise</strong>
                <p>Modelo FAIR configurado para 10.000 simulações por risco.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )