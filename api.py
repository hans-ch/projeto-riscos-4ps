from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from analysis_service import (
    RISK_DIMENSIONS,
    create_risk,
    delete_risk,
    get_latest_excel_report,
    get_latest_html_report,
    initialize_database,
    list_risks,
    update_risk_dimensions,
    update_risk,
)
from analysis_service import _classify_matrix
from local_ai import (
    generate_dimension_justification,
    get_local_ai_status,
)
from rating_analysis import get_rating_history, run_rating_analysis


class RiskDimensionInput(BaseModel):
    dimension: Literal[
        "Pessoas",
        "Processos",
        "Produtos",
        "Políticas governamentais",
    ]
    severity: int = Field(ge=1, le=5)
    probability: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=10, max_length=1200)
    justification: str = Field(min_length=10, max_length=1200)

    @field_validator("evidence", "justification")
    @classmethod
    def strip_dimension_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Informe pelo menos 10 caracteres.")
        return value


class DimensionExplanationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    dimension: Literal[
        "Pessoas",
        "Processos",
        "Produtos",
        "Políticas governamentais",
    ]
    severity: int = Field(ge=1, le=5)
    probability: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=10, max_length=1200)

    @field_validator("title", "category", "evidence")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo não pode ficar vazio.")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


def validate_dimensions(
    dimensions: list[RiskDimensionInput],
) -> list[RiskDimensionInput]:
    submitted = [assessment.dimension for assessment in dimensions]
    if len(submitted) != len(RISK_DIMENSIONS) or set(submitted) != set(RISK_DIMENSIONS):
        raise ValueError("Informe uma pontuação para cada uma das quatro dimensões.")
    return dimensions


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    dimensions: list[RiskDimensionInput] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_all_dimensions(self) -> "RiskCreate":
        validate_dimensions(self.dimensions)
        return self

    @field_validator("title", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo não pode ficar vazio.")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RiskDimensionsUpdate(BaseModel):
    dimensions: list[RiskDimensionInput] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_all_dimensions(self) -> "RiskDimensionsUpdate":
        validate_dimensions(self.dimensions)
        return self


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Risco em Perspectiva",
    description="API para análise de riscos por matriz 4Ps e justificativas com IA local.",
    version="1.0.0",
    lifespan=lifespan,
)

_analysis_progress_lock = Lock()
_analysis_active = False
_analysis_progress: dict[str, Any] = {
    "status": "idle",
    "percent": 0,
    "message": "Nenhuma análise em andamento.",
}


def _update_analysis_progress(percent: int, message: str) -> None:
    with _analysis_progress_lock:
        _analysis_progress.update(
            status="running",
            percent=percent,
            message=message,
        )


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/risks")
def get_risks() -> list[dict[str, Any]]:
    return list_risks()


@app.post("/api/risks", status_code=status.HTTP_201_CREATED)
def add_risk(risk: RiskCreate) -> dict[str, Any]:
    payload = risk.model_dump()
    payload["dimensions"] = [
        assessment.model_dump() for assessment in risk.dimensions
    ]
    return create_risk(**payload)


@app.put("/api/risks/{risk_id}")
def put_risk(risk_id: int, risk: RiskCreate) -> dict[str, Any]:
    payload = risk.model_dump()
    payload["dimensions"] = [
        assessment.model_dump() for assessment in risk.dimensions
    ]
    updated = update_risk(risk_id, **payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Risco não encontrado.")
    return updated


@app.delete("/api/risks/{risk_id}", status_code=status.HTTP_200_OK)
def remove_risk(risk_id: int) -> dict[str, int | bool]:
    if not delete_risk(risk_id):
        raise HTTPException(status_code=404, detail="Risco não encontrado.")
    return {"deleted": True, "risk_id": risk_id}


@app.put("/api/risks/{risk_id}/dimensions")
def put_risk_dimensions(
    risk_id: int,
    assessment: RiskDimensionsUpdate,
) -> dict[str, Any]:
    dimensions = [
        item.model_dump() for item in assessment.dimensions
    ]
    updated = update_risk_dimensions(risk_id, dimensions)
    if updated is None:
        raise HTTPException(status_code=404, detail="Risco não encontrado.")
    return updated


@app.get("/api/analysis/history")
def get_history() -> list[dict[str, Any]]:
    return get_rating_history()


@app.get("/api/ai/status")
def local_ai_status() -> dict[str, Any]:
    return get_local_ai_status()


@app.post("/api/ai/dimension-justification")
def generate_risk_dimension_justification(
    request: DimensionExplanationRequest,
) -> dict[str, str]:
    score = request.severity * request.probability
    try:
        explanation = generate_dimension_justification(
            title=request.title,
            category=request.category,
            description=request.description,
            dimension=request.dimension,
            severity=request.severity,
            probability=request.probability,
            evidence=request.evidence,
            classification=_classify_matrix(score),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"justification": explanation}


@app.get("/api/analysis/progress")
def get_analysis_progress() -> dict[str, Any]:
    with _analysis_progress_lock:
        return dict(_analysis_progress)


@app.post("/api/analysis")
def execute_analysis() -> dict[str, Any]:
    global _analysis_active

    with _analysis_progress_lock:
        if _analysis_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma análise em andamento.",
            )
        _analysis_active = True
        _analysis_progress.update(
            status="running",
            percent=0,
            message="Iniciando análise dos riscos.",
        )

    try:
        result = run_rating_analysis(progress_callback=_update_analysis_progress)
    except ValueError as error:
        with _analysis_progress_lock:
            _analysis_progress.update(status="failed", message=str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        with _analysis_progress_lock:
            _analysis_progress.update(
                status="failed",
                message=f"Falha durante a análise: {error}",
            )
        raise
    else:
        with _analysis_progress_lock:
            _analysis_progress.update(
                status="completed",
                percent=100,
                message="Análise concluída.",
            )
        return result
    finally:
        with _analysis_progress_lock:
            _analysis_active = False


@app.get("/api/reports/html", response_class=HTMLResponse)
def download_html_report() -> HTMLResponse:
    report = get_latest_html_report()
    if report is None:
        raise HTTPException(status_code=409, detail="Execute uma análise antes de baixar o relatório.")
    return HTMLResponse(
        content=report,
        headers={"Content-Disposition": 'attachment; filename="relatorio_4ps.html"'},
    )


@app.get("/api/reports/excel")
def download_excel_report() -> Response:
    report = get_latest_excel_report()
    if report is None:
        raise HTTPException(status_code=409, detail="Execute uma análise antes de baixar a planilha.")
    return Response(
        content=report,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="relatorio_4ps.xlsx"'},
    )
