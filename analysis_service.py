from __future__ import annotations

import io
import json
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
LOW_EXPOSURE_LIMIT = 50_000
HIGH_EXPOSURE_LIMIT = 200_000
RISK_DIMENSIONS = (
    "Pessoas",
    "Processos",
    "Produtos",
    "Políticas governamentais",
)
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
            CREATE TABLE IF NOT EXISTS risk_dimensions (
                risco_id INTEGER NOT NULL,
                dimension TEXT NOT NULL,
                severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
                probability INTEGER NOT NULL CHECK (probability BETWEEN 1 AND 5),
                assessment_source TEXT NOT NULL DEFAULT 'assessed',
                PRIMARY KEY (risco_id, dimension),
                FOREIGN KEY (risco_id) REFERENCES riscos(id) ON DELETE CASCADE
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
            CREATE TABLE IF NOT EXISTS dimension_results_fair (
                risco_id INTEGER NOT NULL,
                dimension TEXT NOT NULL,
                data_execucao TEXT NOT NULL,
                perda_media_inerente REAL NOT NULL,
                perda_media_residual REAL NOT NULL,
                p95_residual REAL NOT NULL,
                classificacao_fair TEXT NOT NULL,
                PRIMARY KEY (risco_id, dimension),
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
                simulations_per_risk INTEGER NOT NULL,
                dimension_metrics TEXT NOT NULL DEFAULT '{}'
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
        history_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(analysis_history)")
        }
        if "dimension_metrics" not in history_columns:
            connection.execute(
                "ALTER TABLE analysis_history ADD COLUMN dimension_metrics TEXT NOT NULL DEFAULT '{}'"
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
        for dimension in RISK_DIMENSIONS:
            connection.execute(
                """
                INSERT OR IGNORE INTO risk_dimensions
                    (risco_id, dimension, severity, probability, assessment_source)
                SELECT id, ?, severidade, probabilidade, 'inherited'
                FROM riscos WHERE severidade BETWEEN 1 AND 5 AND probabilidade BETWEEN 1 AND 5
                """,
                (dimension,),
            )


def _build_model(
    name: str,
    probability: int,
    severity: int,
    frequency_factor: float = 1.0,
    random_seed: int = 42,
) -> FairModel:
    frequency = FREQUENCY[int(probability)]
    loss = LOSS[int(severity)]
    model = FairModel(
        name=name,
        n_simulations=SIMULATIONS_PER_RISK,
        random_seed=random_seed,
    )
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
    if mean_loss >= HIGH_EXPOSURE_LIMIT:
        return "Alto"
    if mean_loss >= LOW_EXPOSURE_LIMIT:
        return "Médio"
    return "Baixo"


def _format_brl(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _build_risk_verdict(dimensions: list[dict[str, Any]]) -> dict[str, Any]:
    classification_order = {"Baixo": 0, "Médio": 1, "Alto": 2}
    highest_dimension = max(
        dimensions,
        key=lambda item: classification_order[item["classification"]],
    )
    non_low_dimensions = [
        item for item in dimensions if item["classification"] != "Baixo"
    ]
    relevant_dimensions = non_low_dimensions or [
        max(dimensions, key=lambda item: item["residual_loss"])
    ]
    details = "; ".join(
        (
            f'{item["dimension"]}: {item["classification"]}, exposição residual '
            f'média de R$ {_format_brl(item["residual_loss"])}/ano, matriz '
            f'{item["severity"]}×{item["probability"]} e redução por controles '
            f'de {item["control_reduction"]:.0%}'
        )
        for item in relevant_dimensions
    )

    if highest_dimension["classification"] == "Alto":
        justification = (
            "Não favorável: pelo menos uma dimensão apresenta exposição residual "
            f"alta (R$ {_format_brl(HIGH_EXPOSURE_LIMIT)}/ano ou mais). "
            "É necessário tratar os fatores críticos "
            f"antes de aceitar o risco. {details}."
        )
    elif highest_dimension["classification"] == "Médio":
        justification = (
            "Não favorável para aceitação sem revisão: existe exposição residual "
            f"média (de R$ {_format_brl(LOW_EXPOSURE_LIMIT)} a menos de "
            f"R$ {_format_brl(HIGH_EXPOSURE_LIMIT)} por ano), que exige plano "
            f"de mitigação e acompanhamento. {details}."
        )
    else:
        justification = (
            "Favorável pelo critério atual: as quatro dimensões apresentam "
            f"exposição residual média inferior a R$ {_format_brl(LOW_EXPOSURE_LIMIT)} por ano. "
            f"Maior exposição observada: {details}. Isso não significa ausência de risco."
        )

    provisional = any(item["inherited"] for item in dimensions)
    if provisional:
        justification += (
            " Parecer provisório: há pontuações herdadas da avaliação anterior "
            "que ainda precisam de revisão."
        )

    return {
        "status": (
            "Favorável"
            if highest_dimension["classification"] == "Baixo"
            else "Não favorável"
        ),
        "nivel": highest_dimension["classification"],
        "provisorio": provisional,
        "justificativa": justification,
        "dimensoes_relevantes": [
            item["dimension"] for item in relevant_dimensions
        ],
    }


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
        dimensions = connection.execute(
            """
            SELECT risco_id, dimension, severity, probability, assessment_source
            FROM risk_dimensions
            ORDER BY CASE dimension
                WHEN 'Pessoas' THEN 1
                WHEN 'Processos' THEN 2
                WHEN 'Produtos' THEN 3
                WHEN 'Políticas governamentais' THEN 4
            END
            """
        ).fetchall()
    dimensions_by_risk: dict[int, list[dict[str, Any]]] = {}
    for assessment in dimensions:
        dimensions_by_risk.setdefault(assessment["risco_id"], []).append(
            {
                "dimension": assessment["dimension"],
                "severity": assessment["severity"],
                "probability": assessment["probability"],
                "inherited": assessment["assessment_source"] == "inherited",
            }
        )
    return [
        {**dict(risk), "dimensions": dimensions_by_risk.get(risk["id"], [])}
        for risk in risks
    ]


def create_risk(
    title: str,
    description: str | None,
    category: str,
    dimensions: list[dict[str, Any]],
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        severity = max(assessment["severity"] for assessment in dimensions)
        probability = max(assessment["probability"] for assessment in dimensions)
        cursor = connection.execute(
            """
            INSERT INTO riscos (titulo, descricao, categoria, severidade, probabilidade)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, category, severity, probability),
        )
        risk_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO risk_dimensions
                (risco_id, dimension, severity, probability, assessment_source)
            VALUES (?, ?, ?, ?, 'assessed')
            """,
            [
                (
                    risk_id,
                    assessment["dimension"],
                    assessment["severity"],
                    assessment["probability"],
                )
                for assessment in dimensions
            ],
        )

    return {
        "id": risk_id,
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "probability": probability,
        "dimensions": [{**assessment, "inherited": False} for assessment in dimensions],
    }


def update_risk_dimensions(
    risk_id: int,
    dimensions: list[dict[str, Any]],
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any] | None:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        exists = connection.execute(
            "SELECT 1 FROM riscos WHERE id = ?",
            (risk_id,),
        ).fetchone()
        if exists is None:
            return None

        connection.executemany(
            """
            INSERT INTO risk_dimensions
                (risco_id, dimension, severity, probability, assessment_source)
            VALUES (?, ?, ?, ?, 'assessed')
            ON CONFLICT(risco_id, dimension) DO UPDATE SET
                severity = excluded.severity,
                probability = excluded.probability,
                assessment_source = 'assessed'
            """,
            [
                (
                    risk_id,
                    assessment["dimension"],
                    assessment["severity"],
                    assessment["probability"],
                )
                for assessment in dimensions
            ],
        )
        connection.execute(
            """
            UPDATE riscos
            SET severidade = ?, probabilidade = ?
            WHERE id = ?
            """,
            (
                max(assessment["severity"] for assessment in dimensions),
                max(assessment["probability"] for assessment in dimensions),
                risk_id,
            ),
        )

    return next(
        (risk for risk in list_risks(database_path) if risk["id"] == risk_id),
        None,
    )


def update_risk(
    risk_id: int,
    title: str,
    description: str | None,
    category: str,
    dimensions: list[dict[str, Any]],
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any] | None:
    severity = max(assessment["severity"] for assessment in dimensions)
    probability = max(assessment["probability"] for assessment in dimensions)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        cursor = connection.execute(
            """
            UPDATE riscos
            SET titulo = ?, descricao = ?, categoria = ?,
                severidade = ?, probabilidade = ?
            WHERE id = ?
            """,
            (title, description, category, severity, probability, risk_id),
        )
        if cursor.rowcount == 0:
            return None

        connection.executemany(
            """
            INSERT INTO risk_dimensions
                (risco_id, dimension, severity, probability, assessment_source)
            VALUES (?, ?, ?, ?, 'assessed')
            ON CONFLICT(risco_id, dimension) DO UPDATE SET
                severity = excluded.severity,
                probability = excluded.probability,
                assessment_source = 'assessed'
            """,
            [
                (
                    risk_id,
                    assessment["dimension"],
                    assessment["severity"],
                    assessment["probability"],
                )
                for assessment in dimensions
            ],
        )

    return next(
        (risk for risk in list_risks(database_path) if risk["id"] == risk_id),
        None,
    )


def delete_risk(risk_id: int, database_path: Path = DATABASE_PATH) -> bool:
    related_tables = (
        "analises_risco",
        "medidas_controle",
        "resultados_fair",
        "dimension_results_fair",
        "log_ocorrencias",
        "risk_dimensions",
    )
    with closing(sqlite3.connect(database_path)) as connection, connection:
        exists = connection.execute(
            "SELECT 1 FROM riscos WHERE id = ?",
            (risk_id,),
        ).fetchone()
        if exists is None:
            return False

        for table in related_tables:
            connection.execute(f"DELETE FROM {table} WHERE risco_id = ?", (risk_id,))
        connection.execute("DELETE FROM riscos WHERE id = ?", (risk_id,))
    return True


def get_analysis_history(database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        history = connection.execute(
            """
            SELECT id, analyzed_at, inherent_loss, residual_loss, p95_total,
                   control_reduction, risk_count, simulations_per_risk,
                   dimension_metrics
            FROM analysis_history
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    result = []
    for run in reversed(history):
        item = dict(run)
        dimension_metrics = json.loads(item.pop("dimension_metrics"))
        item["dimensions"] = dimension_metrics if isinstance(dimension_metrics, list) else []
        result.append(item)
    return result


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
            "SELECT id, titulo, categoria FROM riscos",
            connection,
        )
        if risks.empty:
            raise ValueError("Não há riscos cadastrados para executar a análise.")

        assessments = pd.read_sql_query(
            """
            SELECT risco_id, dimension, severity, probability, assessment_source
            FROM risk_dimensions
            """,
            connection,
        )
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
        all_inherent_models: list[FairModel] = []
        all_residual_models: list[FairModel] = []
        models_by_dimension: dict[str, dict[str, list[FairModel]]] = {
            dimension: {"inherent": [], "residual": []}
            for dimension in RISK_DIMENSIONS
        }
        legacy_assessments = 0
        for risk in risks.itertuples(index=False):
            risk_assessments = assessments.loc[assessments["risco_id"] == risk.id]
            assessment_by_dimension = {
                item.dimension: item
                for item in risk_assessments.itertuples(index=False)
            }
            missing_dimensions = [
                dimension
                for dimension in RISK_DIMENSIONS
                if dimension not in assessment_by_dimension
            ]
            if missing_dimensions:
                raise ValueError(
                    f"O risco '{risk.titulo}' não tem avaliações para: "
                    f"{', '.join(missing_dimensions)}."
                )

            status_values = controls.loc[
                controls["risco_id"] == risk.id,
                "status_acao",
            ]
            reduction = min(
                sum(CONTROL_REDUCTION.get(status, 0.0) for status in status_values),
                MAX_CONTROL_REDUCTION,
            )
            occurrence = (
                occurrences.loc[occurrences["risco_id"] == risk.id].iloc[0]
                if not occurrences.empty
                and not occurrences.loc[occurrences["risco_id"] == risk.id].empty
                else None
            )
            risk_dimension_rows = []
            risk_inherent_models: list[FairModel] = []
            risk_residual_models: list[FairModel] = []
            for dimension in RISK_DIMENSIONS:
                assessment = assessment_by_dimension[dimension]
                severity = int(assessment.severity)
                probability = int(assessment.probability)
                random_seed = int(risk.id) * len(RISK_DIMENSIONS) + RISK_DIMENSIONS.index(dimension)
                inherent_model = _build_model(
                    f"{risk.id} {dimension} Inerente",
                    probability,
                    severity,
                    random_seed=random_seed,
                )
                residual_model = _build_model(
                    f"{risk.id} {dimension} Residual",
                    probability,
                    severity,
                    frequency_factor=1 - reduction,
                    random_seed=random_seed,
                )
                inherent_values = inherent_model.export_results()["Risk"]
                residual_values = residual_model.export_results()["Risk"]
                matrix_score = severity * probability
                dimension_result = {
                    "dimension": dimension,
                    "severity": severity,
                    "probability": probability,
                    "inherited": assessment.assessment_source == "inherited",
                    "matrix_score": matrix_score,
                    "matrix_classification": _classify_matrix(matrix_score),
                    "inherent_loss": round(float(inherent_values.mean())),
                    "residual_loss": round(float(residual_values.mean())),
                    "p95_residual": round(float(np.percentile(residual_values, 95))),
                    "classification": _classify_fair(float(residual_values.mean())),
                    "control_reduction": reduction,
                }
                risk_dimension_rows.append(dimension_result)
                risk_inherent_models.append(inherent_model)
                risk_residual_models.append(residual_model)
                all_inherent_models.append(inherent_model)
                all_residual_models.append(residual_model)
                models_by_dimension[dimension]["inherent"].append(inherent_model)
                models_by_dimension[dimension]["residual"].append(residual_model)
                if dimension_result["inherited"]:
                    legacy_assessments += 1

            risk_total_model = FairMetaModel(
                name=f"{risk.id} Total das dimensões",
                models=risk_residual_models,
            )
            risk_total_model.calculate_all()
            risk_total = risk_total_model.export_results()["Risk"]
            matrix_assessment = max(
                risk_dimension_rows,
                key=lambda item: item["matrix_score"],
            )
            mean_inherent = sum(
                item["inherent_loss"] for item in risk_dimension_rows
            )
            mean_residual = sum(
                item["residual_loss"] for item in risk_dimension_rows
            )
            verdict = _build_risk_verdict(risk_dimension_rows)
            rows.append(
                {
                    "id": int(risk.id),
                    "risco": risk.titulo,
                    "categoria": risk.categoria,
                    "severidade": matrix_assessment["severity"],
                    "probabilidade": matrix_assessment["probability"],
                    "pessoa_afetada": occurrence["nome"] if occurrence is not None else "Não informado",
                    "data_ocorrencia": occurrence["data_ocorrencia"] if occurrence is not None else "Não informada",
                    "descricao_ocorrencia": occurrence["descricao_ocorrencia"] if occurrence is not None else "Não informada",
                    "resolucao": occurrence["acao"] if occurrence is not None else "Sem ação registrada",
                    "status": occurrence["status_acao"] if occurrence is not None else "Pendente",
                    "matriz": f"{matrix_assessment['matrix_score']} - {matrix_assessment['matrix_classification']}",
                    "reducao_controles": reduction,
                    "perda_inerente": mean_inherent,
                    "perda_residual": mean_residual,
                    "p95_residual": round(float(np.percentile(risk_total, 95))),
                    "classificacao_fair": _classify_fair(mean_residual),
                    "parecer_final": verdict,
                    "dimensoes": risk_dimension_rows,
                }
            )

        rows.sort(key=lambda row: row["perda_residual"], reverse=True)
        inherent_meta = FairMetaModel(
            name="Exposição inerente total 4Ps",
            models=all_inherent_models,
        )
        inherent_meta.calculate_all()
        inherent_total = inherent_meta.export_results()["Risk"]
        residual_meta = FairMetaModel(
            name="Exposição residual total 4Ps",
            models=all_residual_models,
        )
        residual_meta.calculate_all()
        total_risk = residual_meta.export_results()["Risk"]

        dimension_summaries = []
        for dimension in RISK_DIMENSIONS:
            inherent_dimension_meta = FairMetaModel(
                name=f"{dimension} Inerente",
                models=models_by_dimension[dimension]["inherent"],
            )
            inherent_dimension_meta.calculate_all()
            inherent_dimension = inherent_dimension_meta.export_results()["Risk"]
            residual_dimension_meta = FairMetaModel(
                name=f"{dimension} Residual",
                models=models_by_dimension[dimension]["residual"],
            )
            residual_dimension_meta.calculate_all()
            residual_dimension = residual_dimension_meta.export_results()["Risk"]
            inherent_mean = float(inherent_dimension.mean())
            residual_mean = float(residual_dimension.mean())
            dimension_summaries.append(
                {
                    "dimension": dimension,
                    "inherent_loss": round(inherent_mean),
                    "residual_loss": round(residual_mean),
                    "p95_total": round(float(np.percentile(residual_dimension, 95))),
                    "control_reduction": (
                        1 - residual_mean / inherent_mean if inherent_mean > 0 else 0
                    ),
                    "risk_count": len(models_by_dimension[dimension]["residual"]),
                    "classification": _classify_fair(residual_mean),
                }
            )

        inherent_sum = float(inherent_total.mean())
        residual_sum = float(total_risk.mean())
        summary = {
            "perda_inerente": round(inherent_sum),
            "perda_residual": round(residual_sum),
            "p95_total": round(float(np.percentile(total_risk, 95))),
            "reducao_geral": 1 - residual_sum / inherent_sum if inherent_sum > 0 else 0,
            "quantidade_riscos": len(rows),
            "simulacoes_por_risco": SIMULATIONS_PER_RISK,
            "quantidade_dimensoes": len(RISK_DIMENSIONS),
            "dimensoes": dimension_summaries,
            "herdados_pendentes_revisao": legacy_assessments,
            "metodologia_total": (
                "Soma das exposições FAIR das quatro dimensões; "
                "a interpretação depende da ausência de sobreposição entre dimensões."
            ),
        }
        unfavorable_risks = [
            row for row in rows if row["parecer_final"]["status"] != "Favorável"
        ]
        provisional_risks = [
            row for row in rows if row["parecer_final"]["provisorio"]
        ]
        summary["parecer_carteira"] = {
            "status": (
                "Não favorável" if unfavorable_risks else "Favorável"
            ),
            "riscos_nao_favoraveis": len(unfavorable_risks),
            "riscos_provisorios": len(provisional_risks),
            "criterio": (
                "Favorável somente quando cada P tem exposição residual média "
                f"inferior a R$ {_format_brl(LOW_EXPOSURE_LIMIT)}/ano. Médio: de R$ "
                f"{_format_brl(LOW_EXPOSURE_LIMIT)} a menos de "
                f"R$ {_format_brl(HIGH_EXPOSURE_LIMIT)}; "
                f"alto: R$ {_format_brl(HIGH_EXPOSURE_LIMIT)} ou mais."
            ),
            "justificativa": (
                f"{len(unfavorable_risks)} de {len(rows)} riscos não atendem "
                "ao critério de exposição baixa em todas as quatro dimensões. "
                f"{len(provisional_risks)} ainda têm pontuações herdadas e "
                "precisam de revisão."
                if unfavorable_risks or provisional_risks
                else "Todos os riscos estão em nível baixo nas quatro dimensões. "
                "Isso não significa ausência de risco."
            ),
        }

        analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO analysis_history
                (analyzed_at, inherent_loss, residual_loss, p95_total,
                 control_reduction, risk_count, simulations_per_risk,
                 dimension_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analyzed_at,
                summary["perda_inerente"],
                summary["perda_residual"],
                summary["p95_total"],
                summary["reducao_geral"],
                summary["quantidade_riscos"],
                summary["simulacoes_por_risco"],
                json.dumps(dimension_summaries, ensure_ascii=False),
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
        connection.execute("DELETE FROM dimension_results_fair")
        connection.executemany(
            """
            INSERT INTO dimension_results_fair
                (risco_id, dimension, data_execucao, perda_media_inerente,
                 perda_media_residual, p95_residual, classificacao_fair)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    dimension_result["dimension"],
                    date.today().isoformat(),
                    dimension_result["inherent_loss"],
                    dimension_result["residual_loss"],
                    dimension_result["p95_residual"],
                    dimension_result["classification"],
                )
                for row in rows
                for dimension_result in row["dimensoes"]
            ],
        )
        connection.commit()

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            pd.DataFrame(
                [
                    {
                        key: value
                        for key, value in row.items()
                        if key not in ("dimensoes", "parecer_final")
                    }
                    | {
                        "parecer_final": row["parecer_final"]["status"],
                        "nivel_parecer": row["parecer_final"]["nivel"],
                        "justificativa_parecer": row["parecer_final"]["justificativa"],
                    }
                    for row in rows
                ]
            ).to_excel(writer, index=False, sheet_name="Riscos")
            pd.DataFrame(
                [
                    {"risco": row["risco"], **dimension_result}
                    for row in rows
                    for dimension_result in row["dimensoes"]
                ]
            ).to_excel(writer, index=False, sheet_name="Dimensões 4Ps")
        _latest_excel_report = excel_buffer.getvalue()
        _latest_html_report = _build_report(all_residual_models, rows)
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
