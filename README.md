#Projeto de Análise de Riscos 4P's

##Passo a passo para inicializar o projeto python e suas depenencias

###Usando pip
```text
# 1. Criar o ambiente virtual
python -m venv .venv

# 2. Ativar o ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instalar os pacotes a partir do requirements.txt que você gerou
pip install -r requirements.txt

# 4. Rodar o projeto
streamlit run app.py

```

###Usando uv
```text
# 1. Sincronizar o projeto uv
uv sync

# 2. Rodar o projeto
uv run streamlit run app.py
```