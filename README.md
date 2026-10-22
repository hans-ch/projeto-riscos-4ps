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

- Cadastro de riscos com avaliações próprias de severidade e probabilidade nas dimensões Pessoas, Processos, Produtos e Políticas governamentais
- Validação dos dados e persistência imediata no SQLite
- Execução de 10.000 simulações PyFAIR por risco e por dimensão
- Comparação de exposição, matriz de risco e classificação FAIR separadas por dimensão
- Parecer final por risco: favorável somente quando as quatro exposições residuais médias ficam abaixo de R$ 50 mil/ano; qualquer dimensão média ou alta é não favorável até mitigação
- Justificativa do parecer com dimensões críticas, notas de severidade/probabilidade e exposição residual, além de gráfico de contribuição por risco
- Migração das pontuações antigas para as quatro dimensões como valores herdados que exigem revisão explícita
- Cadastro sem notas pré-preenchidas; severidade e probabilidade precisam ser escolhidas para cada dimensão
- Total de planejamento calculado pela soma FAIR das quatro exposições, sujeito a possíveis sobreposições
- Comparação entre perdas inerentes e residuais e cálculo do P95 total
- Histórico persistente das 20 execuções mais recentes para comparar tendências
- Benchmark configurável com metas próprias de perda residual, P95 e redução dos controles
- Gráficos de exposição inerente/residual, evolução histórica e matriz de risco 5 × 5
- Aplicação de redução de frequência conforme o status dos controles
- Registro dos resultados em `resultados_fair` no SQLite
- Exportação persistente do relatório HTML e da planilha Excel em `reports/`

## Estrutura principal

- `frontend/`: interface Vue 3, configuração do Vite e componentes em `src/Components/`
- `api.py`: API FastAPI e endpoints de análise e relatórios
- `analysis_service.py`: banco SQLite, modelos PyFAIR e geração dos relatórios
- `app.py`: inicializador local da API
- `analise_riscos.py`: execução analítica existente em modo script
- `DataBase.db`: base de dados local

## Endpoints

- `GET /api/health`: verifica se a API está disponível
- `GET /api/risks`: lista os riscos cadastrados
- `POST /api/risks`: cadastra um risco para análises futuras
- `PUT /api/risks/{id}/dimensions`: atualiza as quatro avaliações de um risco
- `GET /api/analysis/history`: lista as 20 execuções mais recentes
- `GET /api/benchmark`: consulta a referência configurada
- `PUT /api/benchmark`: salva nome e métricas de referência próprios
- `POST /api/analysis`: executa a análise e atualiza os resultados no SQLite
- `GET /api/reports/html`: baixa o relatório HTML da análise mais recente
- `GET /api/reports/excel`: baixa a planilha Excel da análise mais recente
