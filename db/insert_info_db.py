from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
PASTA_DB = BASE_DIR / "DataBase.db"

# Conecta ao banco de dados (cria se não existir, abre se já existir)
conn = sqlite3.connect(PASTA_DB)
cursor = conn.cursor()

# Cria a tabela apenas se ela ainda não existir
cursor.executescript("""
    CREATE TABLE IF NOT EXISTS pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cargo TEXT,
        setor TEXT
    );

    CREATE TABLE IF NOT EXISTS riscos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT,
        categoria TEXT,
        severidade INTEGER,
        probabilidade INTEGER
    );

    CREATE TABLE IF NOT EXISTS analises_risco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        risco_id INTEGER,
        pessoa_id INTEGER,
        data_analise TEXT NOT NULL,
        nivel_risco_calculado INTEGER,
        status TEXT,
        FOREIGN KEY (risco_id) REFERENCES riscos(id),
        FOREIGN KEY (pessoa_id) REFERENCES pessoas(id)
    );

    CREATE TABLE IF NOT EXISTS medidas_controle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        risco_id INTEGER,
        acao TEXT NOT NULL,
        responsavel_id INTEGER,
        prazo TEXT,
        status_acao TEXT,
        FOREIGN KEY (risco_id) REFERENCES riscos(id),
        FOREIGN KEY (responsavel_id) REFERENCES pessoas(id)
    );
""")

conn.commit()
conn.close()

print(f"Banco de dados atualizado com sucesso em: {PASTA_DB}")