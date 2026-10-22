from __future__ import annotations

import io
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

if not hasattr(pd.DataFrame, "applymap"):
    pd.DataFrame.applymap = pd.DataFrame.map

from pyfair import FairMetaModel, FairModel, FairSimpleReport

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("RISK_DB_PATH", BASE_DIR / "DataBase.db"))
REPORTS_PATH = DATABASE_PATH.parent / "reports"

FREQUENCY = {
    1: (0.01, 0.03, 0.10),
    2: (0.05, 0.15, 0.40),
    3: (0.20, 0.60, 1.50),
    4: (0.80, 2.00, 4.00),
    5: (2.00, 5.00, 12.00),
}

LOSS = {
    1: (1_000, 5_000, 20_000),
    2: (5_000, 25_000, 100_000),
    3: (30_000, 120_000, 500_000),
    4: (150_000, 600_000, 2_500_000),
    5: (500_000, 2_500_000, 10_000_000),
}

CONTROL_REDUCTION = {"Concluída": 0.30, "Em andamento": 0.10, "Pendente": 0.0}
MAX_CONTROL_REDUCTION = 0.70
SIMULATIONS_PER_RISK = 10_000
REPORT_CSS = """
<style>
  :root { color-scheme: light; font-family: Inter, "Segoe UI", sans-serif; color: #183b32; }
  body { margin: 0; padding: 32px; background: #f2f5f1; }
  #main { max-width: 1200px; margin: auto; }
  #band { padding: 28px; color: white; background: #123d34; border-bottom: 5px solid #e47756; }
  #title { font: 36px Georgia, serif; }
  table { width: 100%; border-collapse: collapse; background: white; }
  th, td { padding: 10px; border-bottom: 1px solid #d8e2dc; text-align: left; }
  th { background: #e8f1ed; }
</style>
"""

_latest_html_report: str | None = None
_latest_excel_report: bytes | None = None


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.executescript(
            """
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
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analyzed_at TEXT NOT NULL,
                inherent_loss REAL NOT NULL,
                residual_loss REAL NOT NULL,
                p95_total REAL NOT NULL,
                control_reduction REAL NOT NULL,
                risk_count INTEGER NOT NULL,
                simulations_per_risk INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS benchmark_reference (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                residual_loss REAL,
                p95_total REAL,
                control_reduction REAL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS log_ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risco_id INTEGER,
                pessoa_id INTEGER,
                nome_pessoa TEXT,
                data_ocorrencia TEXT,
                descricao_ocorrencia TEXT,
                status TEXT,
                acao TEXT,
                status_acao TEXT,
                FOREIGN KEY (risco_id) REFERENCES riscos(id),
                FOREIGN KEY (pessoa_id) REFERENCES pessoas(id)
            );
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO benchmark_reference
                (id, name, residual_loss, p95_total, control_reduction, updated_at)
            VALUES (1, 'Referência externa', NULL, NULL, NULL, ?)
            """,
            (datetime.now().astimezone().isoformat(timespec="seconds"),),
        )

        if connection.execute("SELECT COUNT(*) FROM riscos").fetchone()[0] == 0:
            today = date.today().isoformat()
            connection.executemany(
                "INSERT INTO pessoas (nome, cargo, setor) VALUES (?, ?, ?)",
                [
                    ("Ana Souza", "Técnica de Segurança", "SST"),
                    ("Carlos Lima", "Engenheiro", "Manutenção"),
                    ("Marina Alves", "Supervisora", "Produção"),
                    ("João Pereira", "Gerente", "Operações"),
                ],
            )
            connection.executemany(
                """
                INSERT INTO riscos (titulo, descricao, categoria, severidade, probabilidade)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    ("Trabalho em altura > 10 m", "Queda em serviços de fachada e telhado", "Queda", 5, 3),
                    ("Espaço confinado", "Tanque sem ventilação adequada", "Atmosfera", 5, 2),
                    ("Choque elétrico", "Painéis de 440V (NR-10)", "Elétrico", 4, 3),
                    ("Atropelamento empilhadeira", "Tráfego misto pedestres/veículos", "Mecânico", 3, 4),
                    ("Exposição a solventes", "Manuseio sem ventilação local", "Químico", 3, 3),
                    ("Ruído acima de 85 dB", "Setor de prensas sem protetor", "Físico", 2, 4),
                    ("Movimento repetitivo", "Linha de montagem", "Ergonômico", 2, 5),
                    ("Incêndio em depósito", "Armazenamento de inflamáveis", "Incêndio", 5, 1),
                ],
            )
            connection.executemany(
                """
                INSERT INTO analises_risco
                    (risco_id, pessoa_id, data_analise, nivel_risco_calculado, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, 1, today, 15, "Concluída"),
                    (2, 1, today, 10, "Concluída"),
                    (3, 2, today, 12, "Concluída"),
                    (4, 3, today, 12, "Concluída"),
                    (5, 3, today, 9, "Concluída"),
                    (6, 3, today, 8, "Concluída"),
                    (7, 3, today, 10, "Concluída"),
                    (8, 4, today, 5, "Concluída"),
                ],
            )
            connection.executemany(
                """
                INSERT INTO medidas_controle (risco_id, acao, responsavel_id, prazo, status_acao)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, "Instalar linha de vida", 1, "2026-12-01", "Concluída"),
                    (1, "Treinamento NR-35", 1, "2026-11-15", "Em andamento"),
                    (2, "Exaustor e detector de gases", 2, "2026-12-20", "Em andamento"),
                    (3, "Bloqueio e etiquetagem (LOTO)", 2, "2026-10-30", "Concluída"),
                    (4, "Sinalização e faixa de pedestres", 3, "2026-10-20", "Concluída"),
                    (4, "Sensor de proximidade", 3, "2027-01-10", "Pendente"),
                    (5, "Exaustão localizada", 2, "2027-02-01", "Pendente"),
                    (6, "Fornecer protetor auricular", 3, "2026-09-30", "Concluída"),
                    (8, "Sistema de sprinklers", 4, "2027-03-01", "Em andamento"),
                ],
            )
            connection.executemany(
                """
                INSERT INTO log_ocorrencias
                    (risco_id, pessoa_id, nome_pessoa, data_ocorrencia,
                     descricao_ocorrencia, status, acao, status_acao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, 1, "Ana Souza", today, "Queda em serviço em altura", "Concluída", "Instalar linha de vida", "Concluída"),
                    (2, 1, "Ana Souza", today, "Falta de ventilação no espaço confinado", "Concluída", "Exaustor e detector de gases", "Em andamento"),
                    (3, 2, "Carlos Lima", today, "Contato com painel energizado", "Concluída", "Bloqueio e etiquetagem (LOTO)", "Concluída"),
                    (4, 3, "Marina Alves", today, "Acidente com empilhadeira na área de produção", "Concluída", "Sinalização e faixa de pedestres", "Concluída"),
                    (5, 3, "Marina Alves", today, "Exposição a solventes sem ventilação", "Concluída", "Exaustão localizada", "Pendente"),
                    (6, 3, "Marina Alves", today, "Ruído excessivo em linha de prensa", "Concluída", "Fornecer protetor auricular", "Concluída"),
                    (7, 3, "Marina Alves", today, "Lesão por movimento repetitivo", "Concluída", "Ajustes ergonômicos", "Pendente"),
                    (8, 4, "João Pereira", today, "Risco de incêndio em depósito", "Concluída", "Sistema de sprinklers", "Em andamento"),
                ],
            )


def _build_model(
    name: str,
    probability: int,
    severity: int,
    frequency_factor: float = 1.0,
) -> FairModel:
    frequency = FREQUENCY[int(probability)]
    loss = LOSS[int(severity)]
    model = FairModel(name=name, n_simulations=SIMULATIONS_PER_RISK, random_seed=42)
    model.input_data(
        "Loss Event Frequency",
        low=frequency[0] * frequency_factor,
        mode=frequency[1] * frequency_factor,
        high=frequency[2] * frequency_factor,
    )
    model.input_data("Loss Magnitude", low=loss[0], mode=loss[1], high=loss[2])
    model.calculate_all()
    return model


def _classify_fair(mean_loss: float) -> str:
    if mean_loss >= 200_000:
        return "Alto"
    if mean_loss >= 50_000:
        return "Médio"
    return "Baixo"


def _classify_matrix(level: int) -> str:
    if level >= 15:
        return "Alto"
    if level >= 8:
        return "Médio"
    return "Baixo"


def list_risks(database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        risks = connection.execute(
            """
            SELECT id, titulo AS title, descricao AS description,
                   categoria AS category, severidade AS severity,
                   probabilidade AS probability
            FROM riscos
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(risk) for risk in risks]


def create_risk(
    title: str,
    description: str | None,
    category: str,
    severity: int,
    probability: int,
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO riscos (titulo, descricao, categoria, severidade, probabilidade)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, category, severity, probability),
        )
        risk_id = cursor.lastrowid

    return {
        "id": risk_id,
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "probability": probability,
    }


def get_analysis_history(database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        history = connection.execute(
            """
            SELECT id, analyzed_at, inherent_loss, residual_loss, p95_total,
                   control_reduction, risk_count, simulations_per_risk
            FROM analysis_history
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    return [dict(run) for run in reversed(history)]


def get_benchmark_reference(database_path: Path = DATABASE_PATH) -> dict[str, Any]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        reference = connection.execute(
            """
            SELECT name, residual_loss, p95_total, control_reduction, updated_at
            FROM benchmark_reference
            WHERE id = 1
            """
        ).fetchone()
    if reference is None:
        raise RuntimeError("A referência do benchmark não foi inicializada.")
    return dict(reference)


def save_benchmark_reference(
    name: str,
    residual_loss: float | None,
    p95_total: float | None,
    control_reduction: float | None,
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """
            INSERT INTO benchmark_reference
                (id, name, residual_loss, p95_total, control_reduction, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                residual_loss = excluded.residual_loss,
                p95_total = excluded.p95_total,
                control_reduction = excluded.control_reduction,
                updated_at = excluded.updated_at
            """,
            (name, residual_loss, p95_total, control_reduction, updated_at),
        )
    return get_benchmark_reference(database_path)


def _build_report(models: list[FairModel], rows: list[dict[str, Any]]) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "relatorio_fair.html"
        try:
            FairSimpleReport(models).to_html(str(report_path))
            html = report_path.read_text(encoding="utf-8")
        except Exception as error:
            fallback = pd.DataFrame(rows).to_html(index=False, border=1)
            html = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                f"<title>Relatório OpenFAIR</title>{REPORT_CSS}</head>"
                f"<body><main id='main'><header id='band'><span id='title'>"
                f"Relatório OpenFAIR</span></header><p>O relatório detalhado PyFAIR "
                f"não pôde ser gerado: {error}</p>{fallback}</main></body></html>"
            )
        finally:
            plt.close("all")

    if "</head>" in html:
        return html.replace("</head>", f"{REPORT_CSS}</head>", 1)
    return f"<!doctype html><html><head><meta charset='utf-8'>{REPORT_CSS}</head><body>{html}</body></html>"


def run_analysis(database_path: Path = DATABASE_PATH) -> dict[str, Any]:
    global _latest_html_report, _latest_excel_report

    connection = sqlite3.connect(database_path)
    try:
        risks = pd.read_sql_query(
            "SELECT id, titulo, categoria, severidade, probabilidade FROM riscos",
            connection,
        )
        if risks.empty:
            raise ValueError("Não há riscos cadastrados para executar a análise.")

        controls = pd.read_sql_query(
            "SELECT risco_id, status_acao FROM medidas_controle",
            connection,
        )
        people = pd.read_sql_query("SELECT id, nome FROM pessoas", connection)
        occurrences = pd.read_sql_query(
            "SELECT * FROM log_ocorrencias",
            connection,
        )
        if not occurrences.empty:
            occurrences = occurrences.sort_values("data_ocorrencia").drop_duplicates(
                subset="risco_id",
                keep="first",
            )
            occurrences = occurrences.merge(
                people[["id", "nome"]],
                left_on="pessoa_id",
                right_on="id",
                how="left",
            )

        rows: list[dict[str, Any]] = []
        residual_models: list[FairModel] = []
        for risk in risks.itertuples(index=False):
            status_values = controls.loc[
                controls["risco_id"] == risk.id,
                "status_acao",
            ]
            reduction = min(
                sum(CONTROL_REDUCTION.get(status, 0.0) for status in status_values),
                MAX_CONTROL_REDUCTION,
            )
            inherent_model = _build_model(
                f"{risk.id} Inerente",
                risk.probabilidade,
                risk.severidade,
            )
            residual_model = _build_model(
                f"{risk.id} Residual",
                risk.probabilidade,
                risk.severidade,
                frequency_factor=1 - reduction,
            )
            residual_models.append(residual_model)

            inherent_risk = inherent_model.export_results()["Risk"]
            residual_risk = residual_model.export_results()["Risk"]
            matrix_level = int(risk.severidade) * int(risk.probabilidade)
            occurrence = (
                occurrences.loc[occurrences["risco_id"] == risk.id].iloc[0]
                if not occurrences.empty
                and not occurrences.loc[occurrences["risco_id"] == risk.id].empty
                else None
            )
            mean_residual = float(residual_risk.mean())
            rows.append(
                {
                    "id": int(risk.id),
                    "risco": risk.titulo,
                    "categoria": risk.categoria,
                    "severidade": int(risk.severidade),
                    "probabilidade": int(risk.probabilidade),
                    "pessoa_afetada": occurrence["nome"] if occurrence is not None else "Não informado",
                    "data_ocorrencia": occurrence["data_ocorrencia"] if occurrence is not None else "Não informada",
                    "descricao_ocorrencia": occurrence["descricao_ocorrencia"] if occurrence is not None else "Não informada",
                    "resolucao": occurrence["acao"] if occurrence is not None else "Sem ação registrada",
                    "status": occurrence["status_acao"] if occurrence is not None else "Pendente",
                    "matriz": f"{matrix_level} - {_classify_matrix(matrix_level)}",
                    "reducao_controles": reduction,
                    "perda_inerente": round(float(inherent_risk.mean())),
                    "perda_residual": round(mean_residual),
                    "p95_residual": round(float(np.percentile(residual_risk, 95))),
                    "classificacao_fair": _classify_fair(mean_residual),
                }
            )

        rows.sort(key=lambda row: row["perda_residual"], reverse=True)
        meta_model = FairMetaModel(
            name="Risco total residual",
            models=residual_models,
        )
        meta_model.calculate_all()
        total_risk = meta_model.export_results()["Risk"]
        inherent_sum = sum(row["perda_inerente"] for row in rows)
        residual_sum = sum(row["perda_residual"] for row in rows)
        summary = {
            "perda_inerente": inherent_sum,
            "perda_residual": round(float(total_risk.mean())),
            "p95_total": round(float(np.percentile(total_risk, 95))),
            "reducao_geral": 1 - residual_sum / inherent_sum if inherent_sum > 0 else 0,
            "quantidade_riscos": len(rows),
            "simulacoes_por_risco": SIMULATIONS_PER_RISK,
        }

        analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO analysis_history
                (analyzed_at, inherent_loss, residual_loss, p95_total,
                 control_reduction, risk_count, simulations_per_risk)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analyzed_at,
                summary["perda_inerente"],
                summary["perda_residual"],
                summary["p95_total"],
                summary["reducao_geral"],
                summary["quantidade_riscos"],
                summary["simulacoes_por_risco"],
            ),
        )
        connection.execute("DELETE FROM resultados_fair")
        connection.executemany(
            """
            INSERT INTO resultados_fair
                (risco_id, data_execucao, perda_media_inerente,
                 perda_media_residual, p95_residual, classificacao_fair)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    date.today().isoformat(),
                    row["perda_inerente"],
                    row["perda_residual"],
                    row["p95_residual"],
                    row["classificacao_fair"],
                )
                for row in rows
            ],
        )
        connection.commit()

        excel_buffer = io.BytesIO()
        pd.DataFrame(rows).to_excel(excel_buffer, index=False, sheet_name="Riscos FAIR")
        _latest_excel_report = excel_buffer.getvalue()
        _latest_html_report = _build_report(residual_models, rows)
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        (REPORTS_PATH / "relatorio_fair.html").write_text(
            _latest_html_report,
            encoding="utf-8",
        )
        (REPORTS_PATH / "relatorio_fair.xlsx").write_bytes(_latest_excel_report)
        return {"resumo": summary, "riscos": rows}
    finally:
        connection.close()


def get_latest_html_report() -> str | None:
    if _latest_html_report is not None:
        return _latest_html_report
    report_path = REPORTS_PATH / "relatorio_fair.html"
    return report_path.read_text(encoding="utf-8") if report_path.is_file() else None


def get_latest_excel_report() -> bytes | None:
    if _latest_excel_report is not None:
        return _latest_excel_report
    report_path = REPORTS_PATH / "relatorio_fair.xlsx"
    return report_path.read_bytes() if report_path.is_file() else None
