from __future__ import annotations

import io
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from analysis_service import (
    DATABASE_PATH,
    REPORTS_PATH,
    RISK_DIMENSIONS,
    _build_risk_verdict,
    _classify_matrix,
)


def run_rating_analysis(
    database_path: Path = DATABASE_PATH,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    with closing(sqlite3.connect(database_path)) as connection:
        risks = connection.execute(
            "SELECT id, titulo, descricao, categoria FROM riscos ORDER BY id"
        ).fetchall()
        if not risks:
            raise ValueError("Não há riscos cadastrados para executar a análise.")
        assessments = connection.execute(
            """
            SELECT risco_id, dimension, severity, probability, evidence,
                   justification, assessment_source
            FROM risk_dimensions
            """
        ).fetchall()

    assessments_by_risk: dict[int, dict[str, dict[str, Any]]] = {}
    for row in assessments:
        assessments_by_risk.setdefault(row[0], {})[row[1]] = {
            "severity": row[2],
            "probability": row[3],
            "evidence": row[4],
            "justification": row[5],
            "inherited": row[6] == "inherited",
        }

    if progress_callback:
        progress_callback(0, f"Preparando as notas dos quatro P’s para {len(risks)} riscos.")

    results = []
    dimensions_summary = {
        dimension: {"Baixo": 0, "Médio": 0, "Alto": 0, "notas": []}
        for dimension in RISK_DIMENSIONS
    }
    total_assessments = len(risks) * len(RISK_DIMENSIONS)
    completed_assessments = 0
    inherited_count = 0
    missing_justification_count = 0

    for risk_index, (risk_id, title, description, category) in enumerate(risks, start=1):
        risk_dimensions = assessments_by_risk.get(risk_id, {})
        missing_dimensions = [
            dimension for dimension in RISK_DIMENSIONS
            if dimension not in risk_dimensions
        ]
        if missing_dimensions:
            raise ValueError(
                f"O risco '{title}' não tem avaliações para: "
                f"{', '.join(missing_dimensions)}."
            )

        dimension_results = []
        for dimension in RISK_DIMENSIONS:
            assessment = risk_dimensions[dimension]
            severity = int(assessment["severity"])
            probability = int(assessment["probability"])
            score = severity * probability
            classification = _classify_matrix(score)
            result = {
                "dimension": dimension,
                "severity": severity,
                "probability": probability,
                "matrix_score": score,
                "classification": classification,
                "evidence": assessment["evidence"],
                "justification": assessment["justification"],
                "inherited": assessment["inherited"],
            }
            dimension_results.append(result)
            dimensions_summary[dimension][classification] += 1
            dimensions_summary[dimension]["notas"].append(score)
            inherited_count += int(assessment["inherited"])
            missing_justification_count += int(not assessment["justification"].strip())
            completed_assessments += 1
            if progress_callback:
                progress_callback(
                    round(80 * completed_assessments / total_assessments),
                    (
                        f"Risco {risk_index}/{len(risks)}: {title} · {dimension} "
                        f"· nota {score}/25 ({classification})"
                    ),
                )

        verdict = _build_risk_verdict(dimension_results)
        results.append(
            {
                "id": risk_id,
                "risco": title,
                "descricao": description or "",
                "categoria": category or "",
                "dimensoes": dimension_results,
                "parecer_final": verdict,
            }
        )

    favorable = sum(
        row["parecer_final"]["status"] == "Favorável" for row in results
    )
    unfavorable = len(results) - favorable
    dimension_metrics = [
        {
            "dimension": dimension,
            "low_count": values["Baixo"],
            "medium_count": values["Médio"],
            "high_count": values["Alto"],
            "average_score": round(sum(values["notas"]) / len(values["notas"]), 1),
            "risk_count": len(values["notas"]),
        }
        for dimension, values in dimensions_summary.items()
    ]
    portfolio_decision = {
        "status": "Não favorável" if unfavorable else "Favorável",
        "riscos_favoraveis": favorable,
        "riscos_nao_favoraveis": unfavorable,
        "riscos_provisorios": inherited_count,
        "justificativas_pendentes": missing_justification_count,
        "criterio": (
            "Nota de cada P = severidade × probabilidade. Baixo: 1–7; "
            "médio: 8–14; alto: 15–25. A carteira é favorável somente "
            "quando todos os quatro P’s de cada risco ficam na faixa baixa."
        ),
        "justificativa": (
            f"{favorable} riscos favoráveis e {unfavorable} não favoráveis, "
            f"considerando as notas dos quatro P’s. "
            f"{inherited_count} avaliações são herdadas e "
            f"{missing_justification_count} justificativas ainda precisam ser preenchidas."
        ),
    }
    summary = {
        "quantidade_riscos": len(results),
        "quantidade_notas": total_assessments,
        "riscos_favoraveis": favorable,
        "riscos_nao_favoraveis": unfavorable,
        "herdados_pendentes_revisao": inherited_count,
        "justificativas_pendentes": missing_justification_count,
        "dimensoes": dimension_metrics,
        "parecer_carteira": portfolio_decision,
    }

    if progress_callback:
        progress_callback(88, "Consolidando classificações e justificativas dos quatro P’s.")

    analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    rating_metrics = {
        "summary": summary,
        "risks": results,
    }
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """
            INSERT INTO analysis_history
                (analyzed_at, inherent_loss, residual_loss, p95_total,
                 control_reduction, risk_count, simulations_per_risk,
                 dimension_metrics, rating_metrics)
            VALUES (?, 0, 0, 0, 0, ?, 0, ?, ?)
            """,
            (
                analyzed_at,
                len(results),
                json.dumps(dimension_metrics, ensure_ascii=False),
                json.dumps(rating_metrics, ensure_ascii=False),
            ),
        )
        connection.execute("DELETE FROM dimension_results_matrix")
        connection.executemany(
            """
            INSERT INTO dimension_results_matrix
                (risco_id, dimension, data_execucao, severity, probability,
                 matrix_score, classification, evidence, justification)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    risk["id"],
                    dimension["dimension"],
                    date.today().isoformat(),
                    dimension["severity"],
                    dimension["probability"],
                    dimension["matrix_score"],
                    dimension["classification"],
                    dimension["evidence"],
                    dimension["justification"],
                )
                for risk in results
                for dimension in risk["dimensoes"]
            ],
        )
        connection.commit()

    if progress_callback:
        progress_callback(94, "Notas, classificações e justificativas salvas.")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "risco": risk["risco"],
                    "categoria": risk["categoria"],
                    "parecer": risk["parecer_final"]["status"],
                    "justificativa_do_parecer": risk["parecer_final"]["justificativa"],
                }
                for risk in results
            ]
        ).to_excel(writer, index=False, sheet_name="Pareceres")
        pd.DataFrame(
            [
                {"risco": risk["risco"], **dimension}
                for risk in results
                for dimension in risk["dimensoes"]
            ]
        ).to_excel(writer, index=False, sheet_name="Notas 4Ps")
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_PATH / "relatorio_4ps.xlsx"
    report_path.write_bytes(excel_buffer.getvalue())

    report = pd.DataFrame(
        [
            {
                "Risco": risk["risco"],
                "Categoria": risk["categoria"],
                "Parecer final": risk["parecer_final"]["status"],
                "Justificativa": risk["parecer_final"]["justificativa"],
                "Dimensão": dimension["dimension"],
                "Severidade": dimension["severity"],
                "Probabilidade": dimension["probability"],
                "Nota (1–25)": dimension["matrix_score"],
                "Classificação": dimension["classification"],
                "Evidências": dimension["evidence"],
                "Por que recebeu essa nota": dimension["justification"],
            }
            for risk in results
            for dimension in risk["dimensoes"]
        ]
    )
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<title>Análise de risco 4Ps</title>"
        "<style>body{font:14px Segoe UI,Arial,sans-serif;color:#183b32;margin:32px}"
        "h1{color:#174b40}table{border-collapse:collapse;width:100%}"
        "th,td{padding:8px;border-bottom:1px solid #d8e2dc;text-align:left}"
        "th{background:#e8f1ed}</style></head><body><h1>Análise de risco 4Ps</h1>"
        f"<p>{portfolio_decision['justificativa']}</p>"
        f"{report.to_html(index=False, escape=True)}</body></html>"
    )
    (REPORTS_PATH / "relatorio_4ps.html").write_text(html, encoding="utf-8")

    if progress_callback:
        progress_callback(98, "Relatórios de notas e justificativas gerados.")
    return {"resumo": summary, "riscos": results}


def get_rating_history(
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        runs = connection.execute(
            """
            SELECT id, analyzed_at, rating_metrics
            FROM analysis_history
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    history = []
    for run_id, analyzed_at, rating_metrics in reversed(runs):
        metrics = json.loads(rating_metrics or "{}")
        if not metrics:
            continue
        history.append(
            {
                "id": run_id,
                "analyzed_at": analyzed_at,
                **metrics.get("summary", {}),
            }
        )
    return history
