# Projeto de Análise de Riscos 4P's

Aplicação de análise quantitativa de riscos com simulações OpenFAIR/PyFAIR. A interface foi migrada do Streamlit para Vue 3; a análise continua em Python, servida por uma API FastAPI e usando a base SQLite existente.

## Requisitos

- Python 3.13 ou superior
- Node.js 20 ou superior e npm
- `uv` (recomendado) ou `pip`

## Executar em desenvolvimento

Na raiz do projeto, instale as dependências Python:

```powershell
uv sync
```

Inicie a API em um terminal:

```powershell
uv run python app.py
```

A API e a documentação interativa ficam disponíveis em:

- API: <http://127.0.0.1:8000>
- Documentação: <http://127.0.0.1:8000/docs>

Em outro terminal, instale e inicie o front Vue:

```powershell
cd frontend
npm install
npm run dev
```

Abra o endereço informado pelo Vite, normalmente <http://localhost:5173>.

## Banco de dados

Por padrão, a API continua usando `DataBase.db` na raiz do projeto. Para apontar para outra base, defina `RISK_DB_PATH` antes de iniciar o servidor:

```powershell
$env:RISK_DB_PATH = "C:\caminho\para\DataBase.db"
uv run python app.py
```

O servidor cria as tabelas ausentes e só insere os dados demonstrativos quando a tabela de riscos está vazia. Ele preserva os riscos e controles já cadastrados.

## Funcionalidades

- Execução de 10.000 simulações PyFAIR por risco
- Comparação entre perdas inerentes e residuais e cálculo do P95 total
- Aplicação de redução de frequência conforme o status dos controles
- Registro dos resultados em `resultados_fair` no SQLite
- Exportação persistente do relatório HTML e da planilha Excel em `reports/`

## Estrutura principal

- `frontend/`: interface Vue 3 e configuração do Vite
- `api.py`: API FastAPI e endpoints de análise e relatórios
- `analysis_service.py`: banco SQLite, modelos PyFAIR e geração dos relatórios
- `app.py`: inicializador local da API
- `analise_riscos.py`: execução analítica existente em modo script
- `DataBase.db`: base de dados local

## Endpoints

- `GET /api/health`: verifica se a API está disponível
- `POST /api/analysis`: executa a análise e atualiza os resultados no SQLite
- `GET /api/reports/html`: baixa o relatório HTML da análise mais recente
- `GET /api/reports/excel`: baixa a planilha Excel da análise mais recente
