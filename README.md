# Projeto de Análise de Riscos 4P's

Aplicação Vue 3 e FastAPI para avaliar riscos nas dimensões Pessoas, Processos, Produtos e Políticas governamentais. A análise é baseada somente nas notas de severidade e probabilidade (matriz 5 × 5); não estima perdas nem usa valores monetários.

## Requisitos

- Python 3.13 ou superior
- Node.js 20 ou superior e npm
- `uv` (recomendado) ou `pip`
- Ollama local para gerar sugestões de justificativa com IA

## Executar

Na raiz do projeto:
```powershell
python -m pip install streamlit
python -m venv .venv
.\.venv\Scripts\activate
pip install uv
uv sync
uv run python app.py
```

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Para habilitar sugestões locais, instale [Ollama](https://ollama.com/), abra-o e instale uma versão da família DeepSeek R1. O sistema detecta automaticamente a tag instalada (por exemplo, `7b`, `14b` ou outra):

```powershell
ollama pull deepseek-r1:14b
```

A aplicação envia os dados da avaliação somente ao serviço Ollama local (`127.0.0.1:11434`). Sem Ollama, o cadastro e a análise matricial continuam disponíveis; a justificativa pode ser escrita manualmente. Toda sugestão da IA deve ser conferida e pode ser editada antes do salvamento.

Para escolher uma família/modelo diferente ou o endereço local:

```powershell
$env:OLLAMA_MODEL = "deepseek-r1"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
uv run python app.py
```

`OLLAMA_MODEL` pode ser apenas o nome da família ou incluir uma tag específica. Se a tag escolhida não estiver instalada, a aplicação procura outra versão instalada da mesma família.

O endereço da IA é limitado a `localhost`, `127.0.0.1` ou `::1`; a aplicação não encaminha os dados para serviços externos.

## Banco de dados

Por padrão, a API usa `DataBase.db` na raiz. Para selecionar outro banco:

```powershell
$env:RISK_DB_PATH = "C:\caminho\para\DataBase.db"
uv run python app.py
```

O servidor cria as colunas e tabelas ausentes, preserva os riscos existentes e marca avaliações antigas como herdadas. Notas antigas não incluem evidências ou justificativas: revise-as no cadastro antes de considerar o parecer concluído.

## Critérios da matriz

- Cada dimensão recebe severidade e probabilidade de 1 a 5.
- Nota da dimensão = severidade × probabilidade, de 1 a 25.
- Baixo: 1–7; médio: 8–14; alto: 15–25.
- Um risco é favorável somente quando os quatro P's ficam na faixa baixa. Uma nota média ou alta em qualquer dimensão torna o risco não favorável.
- Cada avaliação inclui evidências observadas e uma justificativa editável. A IA local pode sugerir uma frase com base nos dados informados, sem calcular dinheiro; não se deve aceitar sugestões que acrescentem fatos não observados.

## Funcionalidades

- Cadastro, edição e exclusão de riscos e avaliações dos quatro P's
- Justificativas por dimensão, escritas manualmente ou sugeridas por IA local
- Parecer final favorável/não favorável baseado nas classificações da matriz
- Gráfico da distribuição das notas baixas, médias e altas por dimensão
- Matriz de risco 5 × 5 filtrada por dimensão
- Histórico da quantidade de riscos favoráveis e não favoráveis
- Exportação de relatório HTML e Excel com notas, evidências e justificativas
- Migração de avaliações antigas com indicação de pontuações herdadas

## Estrutura principal

- `frontend/`: interface Vue e componentes em `src/Components/`
- `api.py`: API FastAPI, validação e rotas de análise/IA local
- `analysis_service.py`: banco SQLite, CRUD e regras da matriz
- `rating_analysis.py`: análise 4Ps, histórico de notas e relatórios
- `local_ai.py`: conexão local com Ollama

## Endpoints

- `GET /api/health`: verifica a API
- `GET /api/risks`: lista os riscos e avaliações 4Ps
- `POST /api/risks`: cadastra risco, notas, evidências e justificativas
- `PUT /api/risks/{id}`: edita os dados e avaliações
- `DELETE /api/risks/{id}`: exclui risco e registros associados
- `POST /api/ai/dimension-justification`: gera sugestão com Ollama local
- `GET /api/ai/status`: verifica disponibilidade do modelo local
- `POST /api/analysis`: classifica as notas e atualiza o histórico
- `GET /api/analysis/progress`: consulta o progresso da análise
- `GET /api/analysis/history`: lista o histórico de classificações
- `GET /api/reports/html`: baixa o relatório HTML da análise mais recente
- `GET /api/reports/excel`: baixa a planilha da análise mais recente
