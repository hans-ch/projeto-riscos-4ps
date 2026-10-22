from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from analysis_service import (
    create_risk,
    get_analysis_history,
    get_benchmark_reference,
    get_latest_excel_report,
    get_latest_html_report,
    initialize_database,
    list_risks,
    run_analysis,
    save_benchmark_reference,
)


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    severity: int = Field(ge=1, le=5)
    probability: int = Field(ge=1, le=5)

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
    return create_risk(**risk.model_dump())


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
