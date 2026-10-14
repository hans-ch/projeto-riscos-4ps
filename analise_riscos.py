import sqlite3
import numpy as np
import pandas as pd
from pyfair import FairModel, FairMetaModel, FairSimpleReport

# ---------------------------------------------------------
# 1 BANCO DE DADOS FICTÍCIO (SQLite)
# Frequência = eventos por ano | Perda = R$ por evento
# ---------------------------------------------------------
conn = sqlite3.connect("riscos_trabalho.db")
conn.execute("DROP TABLE IF EXISTS riscos")
conn.execute("""
    CREATE TABLE riscos (
        id INTEGER PRIMARY KEY,
        atividade TEXT,
        condicao TEXT,
        freq_min REAL, freq_prov REAL, freq_max REAL,
        perda_min REAL, perda_prov REAL, perda_max REAL,
        classificacao_inicial TEXT
    )
""")

dados = [
    (1, "Trabalho em altura", "Altura > 10 m",          0.05, 0.20, 0.60,  200_000,   800_000, 3_000_000, "Alto"),
    (2, "Espaço confinado",   "Tanque sem ventilação",  0.02, 0.08, 0.30,  300_000, 1_000_000, 4_000_000, "Alto"),
    (3, "Eletricidade",       "Painel 440V (NR-10)",    0.10, 0.40, 1.00,   50_000,   300_000, 1_500_000, "Alto"),
    (4, "Empilhadeira",       "Tráfego misto",          0.50, 2.00, 5.00,    5_000,    30_000,   200_000, "Médio"),
    (5, "Produtos químicos",  "Manuseio de solventes",  0.20, 1.00, 3.00,   10_000,    60_000,   400_000, "Médio"),
    (6, "Ruído",              "> 85 dB sem protetor",   1.00, 3.00, 8.00,    2_000,     8_000,    40_000, "Baixo"),
    (7, "Ergonomia",          "Movimento repetitivo",   2.00, 6.00, 15.0,    1_000,     5_000,    20_000, "Médio"),
    (8, "Incêndio",           "Depósito inflamáveis",   0.01, 0.05, 0.20,  100_000, 1_500_000, 8_000_000, "Médio"),
]

conn.executemany("INSERT INTO riscos VALUES (?,?,?,?,?,?,?,?,?,?)", dados)
conn.commit()

df = pd.read_sql("SELECT * FROM riscos", conn)
conn.close()

print("=== TABELA DE RISCOS (banco fictício) ===")
print(df[["id", "atividade", "condicao", "classificacao_inicial"]].to_string(index=False))

# ---------------------------------------------------------
# 2 MODELO FAIR PARA CADA RISCO
# ---------------------------------------------------------
modelos = []
for _, r in df.iterrows():
    m = FairModel(name=r["atividade"], n_simulations=10_000, random_seed=42)

    # Frequência de eventos de perda (distribuição PERT: min / mais provável / max)
    m.input_data("Loss Event Frequency",
                 low=r["freq_min"], mode=r["freq_prov"], high=r["freq_max"])

    # Magnitude da perda por evento (R$)
    m.input_data("Loss Magnitude",
                 low=r["perda_min"], mode=r["perda_prov"], high=r["perda_max"])

    m.calculate_all()
    modelos.append(m)

# ---------------------------------------------------------
# 3 ESTATÍSTICAS E CLASSIFICAÇÃO
# ---------------------------------------------------------
def classificar(perda_anual_media):
    if perda_anual_media >= 200_000:
        return "Alto"
    elif perda_anual_media >= 100_000:
        return "Médio"
    return "Baixo"

linhas = []
for m, (_, r) in zip(modelos, df.iterrows()):
    risco = m.export_results()["Risk"]   # perda anual simulada (R$/ano)
    media = risco.mean()
    linhas.append({
        "Atividade": r["atividade"],
        "Condição": r["condicao"],
        "Perda anual média (R$)": round(media),
        "Mediana (R$)": round(risco.median()),
        "P95 (R$)": round(np.percentile(risco, 95)),
        "Classif. inicial": r["classificacao_inicial"],
        "Classif. FAIR": classificar(media),
    })

resultado = (pd.DataFrame(linhas)
               .sort_values("Perda anual média (R$)", ascending=False)
               .reset_index(drop=True))

print("\n=== RANKING DE RISCOS (FAIR) ===")
print(resultado.to_string(index=False))

# ---------------------------------------------------------
# 4 RISCO TOTAL DA ORGANIZAÇÃO (MetaModel)
# ---------------------------------------------------------
meta = FairMetaModel(name="Risco total da planta", models=modelos)
meta.calculate_all()
total = meta.export_results()["Risk"]

print("\n=== RISCO TOTAL ===")
print(f"Perda anual esperada: R$ {total.mean():,.0f}")
print(f"Pior cenário (P95):   R$ {np.percentile(total, 95):,.0f}")

# ---------------------------------------------------------
# 5 RELATÓRIO HTML COM GRÁFICOS
# ---------------------------------------------------------
FairSimpleReport(modelos).to_html("relatorio_riscos.html")
print("\nRelatório gerado: relatorio_riscos.html")