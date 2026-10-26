from __future__ import annotations

import json
import os
import re
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


def generate_resolution_suggestions(
    *,
    title: str,
    category: str,
    description: str | None,
    dimensions: list[dict[str, Any]],
) -> list[dict[str, str | int]]:
    if not dimensions:
        raise ValueError("Informe as avaliações das dimensões antes de solicitar recomendações.")

    model = _get_installed_model()
    dimension_context = "\n".join(
        (
            f"- {item['dimension']}: severidade {item['severity']}/5, "
            f"probabilidade {item['probability']}/5, nota "
            f"{item['matrix_score']}/25 ({item['classification']}); "
            f"evidências: {item['evidence'] or 'não informadas'}; "
            f"justificativa: {item['justification'] or 'não informada'}"
        )
        for item in dimensions
    )
    prompt = f"""
Você auxilia na prevenção de riscos ocupacionais. Analise o risco completo
considerando conjuntamente suas quatro dimensões 4Ps e sugira de 3 a 5
recomendações práticas de prevenção, em português e em ordem de prioridade.
Priorize medidas que eliminem ou reduzam o risco na origem e controles
organizacionais; use EPI como complemento, não como única solução.
Baseie-se somente nos dados informados: não invente causas, controles existentes,
normas específicas ou fatos. Considere as notas para priorizar as ações.
As recomendações são apoio e devem ser validadas por uma pessoa responsável.

Risco: {title}
Categoria: {category}
Descrição: {description or "Não informada"}
Avaliações das quatro dimensões:
{dimension_context}

Retorne um objeto JSON com a chave "suggestions", contendo uma lista de ações.
Cada ação deve ter "action" (texto curto), "priority" (número de 1 a 5) e
"justification" (explicação curta ligada às evidências).
""".strip()

    result = _request(
        "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        },
    )
    response = result.get("response")
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("A IA local não gerou sugestões de resolução.")
    response = response.strip()
    if "</think>" in response:
        response = response.rsplit("</think>", maxsplit=1)[-1].strip()
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        raise RuntimeError("A IA local não retornou sugestões em formato JSON.")
    try:
        decoded = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise RuntimeError("A IA local retornou um JSON inválido.") from error

    suggestions = decoded.get("suggestions") if isinstance(decoded, dict) else None
    if not isinstance(suggestions, list) or not 3 <= len(suggestions) <= 5:
        raise RuntimeError("A IA local retornou uma quantidade inválida de sugestões.")

    validated_suggestions: list[dict[str, str | int]] = []
    for index, item in enumerate(suggestions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("A IA local retornou uma sugestão em formato inválido.")
        action = item.get("action")
        justification = item.get("justification")
        priority = item.get("priority")
        if (
            not isinstance(action, str)
            or not action.strip()
            or not isinstance(justification, str)
            or not justification.strip()
            or not isinstance(priority, int)
            or isinstance(priority, bool)
            or not 1 <= priority <= 5
        ):
            raise RuntimeError("A IA local retornou campos inválidos nas sugestões.")
        validated_suggestions.append(
            {
                "action": action.strip()[:300],
                "priority": priority if priority == index else index,
                "justification": justification.strip()[:700],
            }
        )
    return validated_suggestions
