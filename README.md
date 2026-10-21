# Projeto de Análise de Riscos 4P's

Este projeto consiste em uma aplicação em Python para análise de riscos com uso do framework Streamlit e da biblioteca PyFAIR. A interface permite simular cenários de risco, avaliar impactos e visualizar relatórios de análise.

## Requisitos

Antes de iniciar, verifique se você possui:

- Python 3.14 ou superior
- pip instalado
- Git (opcional, caso queira clonar o projeto)
- acesso ao terminal do sistema

Para confirmar a versão do Python:

```bash
python --version
```

Se a versão não aparecer ou estiver incompatível, instale o Python antes de continuar.

## Como rodar o projeto

A forma mais comum é usar um ambiente virtual para isolar as dependências do projeto.

### Opção 1: usando pip

1. Abra o terminal e entre na pasta do projeto:

```bash
cd C:\caminho\para\projeto-riscos-4ps
```

2. Crie o ambiente virtual:

```bash
python -m venv .venv
```

3. Ative o ambiente virtual:

No Windows:

```bash
.venv\Scripts\activate
```

4. Atualize o pip:

```bash
python -m pip install --upgrade pip
```

5. Instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

6. Inicie a aplicação:

```bash
streamlit run app.py
```

7. Acesse a aplicação no navegador:

```text
http://localhost:8501
```

---

### Opção 2: usando uv

Se você preferir usar o `uv`, siga os passos abaixo:

1. Entre na pasta do projeto:

```bash
cd C:\caminho\para\projeto-riscos-4ps
```

2. Sincronize o ambiente do projeto:

```bash
uv sync
```

3. Execute a aplicação:

```bash
uv run streamlit run app.py
```

---

## Resumo rápido

Se quiser a solução mais direta, basta rodar:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

---

## Dicas importantes

- Sempre execute os comandos dentro da pasta do projeto.
- Verifique se o ambiente virtual está ativado antes de instalar as dependências.
- Se a aplicação não abrir, confirme que o Streamlit foi instalado corretamente.
- Caso o VS Code esteja usando outro interpretador, selecione o Python da pasta `.venv`.
- Se o projeto estiver usando um ambiente diferente, certifique-se de que a versão do Python seja compatível com o projeto.

## Estrutura principal do projeto

- `app.py`: aplicação principal do Streamlit
- `requirements.txt`: dependências do projeto
- `pyproject.toml`: configuração do projeto
- `README.md`: instruções de uso
