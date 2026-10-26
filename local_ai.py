from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener
from typing import Any

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")


def _validate_local_url() -> None:
    hostname = urlparse(OLLAMA_BASE_URL).hostname
    if hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("A IA deve usar um servidor Ollama local neste computador.")


def _request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _validate_local_url()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{OLLAMA_BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(request, timeout=90 if payload is not None else 3) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"Ollama respondeu com erro HTTP {error.code}.") from error
    except (TimeoutError, URLError) as error:
        raise RuntimeError(
            "Não foi possível conectar à IA local. Inicie o Ollama e confirme que o modelo está instalado."
        ) from error
    try:
        result = json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError("A IA local retornou uma resposta inválida.") from error
    if not isinstance(result, dict):
        raise RuntimeError("A IA local retornou um formato de resposta inválido.")
    return result


def _installed_models(response: dict[str, Any]) -> list[str]:
    models = response.get("models", [])
    if not isinstance(models, list):
        return []
    return [
        name
        for model in models
        if isinstance(model, dict)
        and isinstance(name := model.get("name") or model.get("model"), str)
        and name
    ]


def _select_installed_model(installed_models: list[str]) -> str | None:
    if OLLAMA_MODEL in installed_models:
        return OLLAMA_MODEL
    family = OLLAMA_MODEL.split(":", maxsplit=1)[0]
    return next(
        (name for name in installed_models if name.startswith(f"{family}:")),
        None,
    )


def _get_installed_model() -> str:
    installed_models = _installed_models(_request("/api/tags"))
    selected_model = _select_installed_model(installed_models)
    if selected_model is None:
        family = OLLAMA_MODEL.split(":", maxsplit=1)[0]
        raise RuntimeError(
            f"Nenhuma versão local de {family} foi encontrada. "
            f"Instale uma versão com `ollama pull {family}:<tag>`."
        )
    return selected_model


def get_local_ai_status() -> dict[str, Any]:
    try:
        model = _get_installed_model()
    except RuntimeError as error:
        return {
            "available": False,
            "model": OLLAMA_MODEL,
            "message": str(error),
        }
    return {
        "available": True,
        "model": model,
        "message": f"IA local pronta ({model}).",
    }


def generate_dimension_justification(
    *,
    title: str,
    category: str,
    description: str | None,
    dimension: str,
    severity: int,
    probability: int,
    evidence: str,
    classification: str,
) -> str:
    if not evidence.strip():
        raise ValueError("Informe as evidências observadas antes de solicitar a justificativa.")

    model = _get_installed_model()
    prompt = f"""
Você auxilia na documentação de uma avaliação de risco ocupacional em português.
Redija uma justificativa curta (1 a 3 frases) para as notas informadas.
Use somente os fatos fornecidos. Não invente causas, controles, consequências ou dados.
Explique como as evidências se relacionam com a severidade, a probabilidade e a nota.
Se as evidências não sustentarem a nota, diga que a pessoa deve revisá-la; não altere a nota.
Não estime dinheiro nem valores financeiros.

Risco: {title}
Categoria: {category}
Descrição cadastrada: {description or "Não informada"}
Dimensão: {dimension}
Severidade: {severity}/5
Probabilidade: {probability}/5
Nota da matriz (severidade x probabilidade): {severity * probability}/25
Classificação da matriz: {classification}
Evidências e contexto informados pela pessoa: {evidence}

Retorne somente a justificativa, sem título, lista ou markdown.
""".strip()
    result = _request(
        "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        },
    )
    response = result.get("response")
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("A IA local não gerou uma justificativa.")
    response = response.strip()
    if "</think>" in response:
        response = response.rsplit("</think>", maxsplit=1)[-1].strip()
    if not response:
        raise RuntimeError("A IA local não gerou uma justificativa final.")
    return response[:1200]
