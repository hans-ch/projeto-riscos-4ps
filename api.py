from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from analysis_service import (
    get_latest_excel_report,
    get_latest_html_report,
    initialize_database,
    run_analysis,
)


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
