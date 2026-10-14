from pathlib import Path
import sqlite3
from datetime import date

import numpy as np
import pandas as pd

# Compatibilidade: PyFAIR usa applymap, removido no pandas 3.0
if not hasattr(pd.DataFrame, "applymap"):
    pd.DataFrame.applymap = pd.DataFrame.map

from pyfair import FairModel, FairMetaModel, FairSimpleReport

BASE_DIR = Path(__file__).resolve().parent
PASTA_DB = BASE_DIR / "DataBase.db"

# ---------------------------------------------------------
# PARÂMETROS DA ANÁLISE (ajuste à realidade da empresa)
# ---------------------------------------------------------
# probabilidade (1-5) -> eventos por ano (mínimo, mais provável, máximo)
FREQUENCIA = {
    1: (0.01, 0.03, 0.10),
    2: (0.05, 0.15, 0.40),
    3: (0.20, 0.60, 1.50),
    4: (0.80, 2.00, 4.00),
    5: (2.00, 5.00, 12.00),
}

# severidade (1-5) -> perda em R$ por evento (mínimo, mais provável, máximo)
PERDA = {
    1: (1_000,     5_000,     20_000),
    2: (5_000,     25_000,    100_000),
    3: (30_000,    120_000,   500_000),
    4: (150_000,   600_000,   2_500_000),
    5: (500_000,   2_500_000, 10_000_000),
}

# Quanto cada medida de controle reduz a frequência, conforme o status
REDUCAO_POR_STATUS = {"Concluída": 0.30, "Em andamento": 0.10, "Pendente": 0.0}
REDUCAO_MAXIMA = 0.70

# Limiares de classificação pela perda anual média (R$/ano)
LIMITE_ALTO = 200_000
LIMITE_MEDIO = 50_000

N_SIMULACOES = 10_000

# ---------------------------------------------------------
# 1) ESTRUTURA DO BANCO (a sua, sem alterações)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 2) DADOS FICTÍCIOS (só se a tabela riscos estiver vazia)
# ---------------------------------------------------------
if cursor.execute("SELECT COUNT(*) FROM riscos").fetchone()[0] == 0:
    cursor.executemany(
        "INSERT INTO pessoas (nome, cargo, setor) VALUES (?,?,?)",
        [
            ("Ana Souza",    "Técnica de Segurança", "SST"),
            ("Carlos Lima",  "Engenheiro",           "Manutenção"),
            ("Marina Alves", "Supervisora",          "Produção"),
            ("João Pereira", "Gerente",              "Operações"),
        ],
    )

    cursor.executemany(
        "INSERT INTO riscos (titulo, descricao, categoria, severidade, probabilidade) VALUES (?,?,?,?,?)",
        [
            ("Trabalho em altura > 10 m",  "Queda em serviços de fachada e telhado", "Queda",       5, 3),
            ("Espaço confinado",           "Tanque sem ventilação adequada",         "Atmosfera",   5, 2),
            ("Choque elétrico",            "Painéis de 440V (NR-10)",                "Elétrico",    4, 3),
            ("Atropelamento empilhadeira", "Tráfego misto pedestres/veículos",       "Mecânico",    3, 4),
            ("Exposição a solventes",      "Manuseio sem ventilação local",          "Químico",     3, 3),
            ("Ruído acima de 85 dB",       "Setor de prensas sem protetor",          "Físico",      2, 4),
            ("Movimento repetitivo",       "Linha de montagem",                      "Ergonômico",  2, 5),
            ("Incêndio em depósito",       "Armazenamento de inflamáveis",           "Incêndio",    5, 1),
        ],
    )

    hoje = date.today().isoformat()
    cursor.executemany(
        "INSERT INTO analises_risco (risco_id, pessoa_id, data_analise, nivel_risco_calculado, status) VALUES (?,?,?,?,?)",
        [
            (1, 1, hoje, 15, "Concluída"), (2, 1, hoje, 10, "Concluída"),
            (3, 2, hoje, 12, "Concluída"), (4, 3, hoje, 12, "Concluída"),
            (5, 3, hoje,  9, "Concluída"), (6, 3, hoje,  8, "Concluída"),
            (7, 3, hoje, 10, "Concluída"), (8, 4, hoje,  5, "Concluída"),
        ],
    )

    cursor.executemany(
        "INSERT INTO medidas_controle (risco_id, acao, responsavel_id, prazo, status_acao) VALUES (?,?,?,?,?)",
        [
            (1, "Instalar linha de vida",        1, "2026-12-01", "Concluída"),
            (1, "Treinamento NR-35",             1, "2026-11-15", "Em andamento"),
            (2, "Exaustor e detector de gases",  2, "2026-12-20", "Em andamento"),
            (3, "Bloqueio e etiquetagem (LOTO)", 2, "2026-10-30", "Concluída"),
            (4, "Sinalização e faixa de pedestres", 3, "2026-10-20", "Concluída"),
            (4, "Sensor de proximidade",         3, "2027-01-10", "Pendente"),
            (5, "Exaustão localizada",           2, "2027-02-01", "Pendente"),
            (6, "Fornecer protetor auricular",   3, "2026-09-30", "Concluída"),
            (8, "Sistema de sprinklers",         4, "2027-03-01", "Em andamento"),
        ],
    )
    conn.commit()
    print("Dados fictícios inseridos.\n")

# ---------------------------------------------------------
# 3) LEITURA DOS DADOS
# ---------------------------------------------------------
riscos = pd.read_sql("SELECT id, titulo, categoria, severidade, probabilidade FROM riscos", conn)
controles = pd.read_sql("SELECT risco_id, status_acao FROM medidas_controle", conn)

def reducao_de_frequencia(risco_id):
    """Soma a redução de cada medida (por status), limitada ao máximo definido."""
    status = controles.loc[controles["risco_id"] == risco_id, "status_acao"]
    total = sum(REDUCAO_POR_STATUS.get(s, 0.0) for s in status)
    return min(total, REDUCAO_MAXIMA)

# ---------------------------------------------------------
# 4) MODELOS FAIR
# ---------------------------------------------------------
def construir_modelo(nome, probabilidade, severidade, fator_frequencia=1.0):
    f = FREQUENCIA[int(probabilidade)]
    p = PERDA[int(severidade)]

    m = FairModel(name=nome, n_simulations=N_SIMULACOES, random_seed=42)
    m.input_data("Loss Event Frequency",
                 low=f[0] * fator_frequencia,
                 mode=f[1] * fator_frequencia,
                 high=f[2] * fator_frequencia)
    m.input_data("Loss Magnitude", low=p[0], mode=p[1], high=p[2])
    m.calculate_all()
    return m

def classificar_fair(perda_media):
    if perda_media >= LIMITE_ALTO:
        return "Alto"
    if perda_media >= LIMITE_MEDIO:
        return "Médio"
    return "Baixo"

def classificar_matriz(nivel):
    """Matriz qualitativa clássica: severidade x probabilidade (1 a 25)."""
    if nivel >= 15:
        return "Alto"
    if nivel >= 8:
        return "Médio"
    return "Baixo"

linhas = []
modelos_residuais = []

for _, r in riscos.iterrows():
    reducao = reducao_de_frequencia(r["id"])

    inerente = construir_modelo(f"{r['id']} Inerente",
                                r["probabilidade"], r["severidade"])
    residual = construir_modelo(f"{r['id']} Residual",
                                r["probabilidade"], r["severidade"],
                                fator_frequencia=1 - reducao)
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

resultado = (pd.DataFrame(linhas)
               .sort_values("Perda residual (R$/ano)", ascending=False)
               .reset_index(drop=True))

print("=== RANKING DE RISCOS (FAIR) ===")
print(resultado.drop(columns="id").to_string(index=False))

# ---------------------------------------------------------
# 5) RISCO TOTAL (residual)
# ---------------------------------------------------------
meta = FairMetaModel(name="Risco total residual", models=modelos_residuais)
meta.calculate_all()
total = meta.export_results()["Risk"]

soma_inerente = resultado["Perda inerente (R$/ano)"].sum()
soma_residual = resultado["Perda residual (R$/ano)"].sum()

print("\n=== RISCO TOTAL ===")
print(f"Perda anual esperada (inerente): R$ {soma_inerente:,.0f}")
print(f"Perda anual esperada (residual): R$ {total.mean():,.0f}")
print(f"Pior cenário residual (P95):     R$ {np.percentile(total, 95):,.0f}")
print(f"Redução proporcionada pelos controles: {1 - soma_residual / soma_inerente:.0%}")

# ---------------------------------------------------------
# 6) GRAVA OS RESULTADOS NO BANCO
# ---------------------------------------------------------
cursor.execute("DELETE FROM resultados_fair")
cursor.executemany(
    """INSERT INTO resultados_fair
       (risco_id, data_execucao, perda_media_inerente, perda_media_residual,
        p95_residual, classificacao_fair)
       VALUES (?,?,?,?,?,?)""",
    [
        (int(x["id"]), date.today().isoformat(),
         float(x["Perda inerente (R$/ano)"]), float(x["Perda residual (R$/ano)"]),
         float(x["P95 residual (R$)"]), x["Classif. FAIR"])
        for _, x in resultado.iterrows()
    ],
)
conn.commit()
conn.close()
print("\nResultados gravados na tabela resultados_fair.")

# ---------------------------------------------------------
# 7) RELATÓRIO HTML (com plano B)
# ---------------------------------------------------------
destino = BASE_DIR / "relatorio_fair.html"
try:
    FairSimpleReport(modelos_residuais).to_html(str(destino))
    print(f"Relatório PyFAIR gerado: {destino}")
except Exception as e:
    print(f"Relatório do PyFAIR falhou ({e}). Gerando HTML alternativo...")
    resultado.to_html(str(destino), index=False, border=1)
    print(f"Relatório alternativo gerado: {destino}")
