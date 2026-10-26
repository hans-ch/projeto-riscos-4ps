from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from analysis_service import (
    RISK_DIMENSIONS,
    create_risk,
    delete_risk,
    get_analysis_history,
    get_benchmark_reference,
    get_latest_excel_report,
    get_latest_html_report,
    initialize_database,
    list_risks,
    run_analysis,
    save_benchmark_reference,
    update_risk_dimensions,
    update_risk,
)


class RiskDimensionInput(BaseModel):
    dimension: Literal[
        "Pessoas",
        "Processos",
        "Produtos",
        "Políticas governamentais",
    ]
    severity: int = Field(ge=1, le=5)
    probability: int = Field(ge=1, le=5)


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


class BenchmarkReference(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    residual_loss: float | None = Field(default=None, ge=0)
    p95_total: float | None = Field(default=None, ge=0)
    control_reduction: float | None = Field(default=None, ge=0, le=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome da referência.")
        return value

    @model_validator(mode="after")
    def require_one_metric(self) -> "BenchmarkReference":
        if all(
            value is None
            for value in (self.residual_loss, self.p95_total, self.control_reduction)
        ):
            raise ValueError("Informe ao menos uma métrica de referência.")
        return self


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Risco em Perspectiva",
    description="API para análise quantitativa de riscos com o modelo FAIR.",
    version="1.0.0",
    lifespan=lifespan,
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
    return get_analysis_history()


@app.get("/api/benchmark")
def get_benchmark() -> dict[str, Any]:
    return get_benchmark_reference()


@app.put("/api/benchmark")
def put_benchmark(reference: BenchmarkReference) -> dict[str, Any]:
    return save_benchmark_reference(**reference.model_dump())


@app.post("/api/analysis")
def execute_analysis() -> dict[str, Any]:
    try:
        return run_analysis()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/reports/html", response_class=HTMLResponse)
def download_html_report() -> HTMLResponse:
    report = get_latest_html_report()
    if report is None:
        raise HTTPException(status_code=409, detail="Execute uma análise antes de baixar o relatório.")
    return HTMLResponse(
        content=report,
        headers={"Content-Disposition": 'attachment; filename="relatorio_fair.html"'},
    )


@app.get("/api/reports/excel")
def download_excel_report() -> Response:
    report = get_latest_excel_report()
    if report is None:
        raise HTTPException(status_code=409, detail="Execute uma análise antes de baixar a planilha.")
    return Response(
        content=report,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="relatorio_fair.xlsx"'},
    )
