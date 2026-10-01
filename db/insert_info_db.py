from pathlib import Path
import sqlite3

# Pega o diretório exato onde este script Python está (a pasta 'db')
BASE_DIR = Path(__file__).resolve().parent

# Caminho final do banco de dados na mesma pasta do script
PASTA_DB = BASE_DIR / "DataBase.db"

# Conecta ao banco de dados no caminho correto
conn = sqlite3.connect(PASTA_DB)

# Cria o cursor (objeto que executa os comandos SQL)
cursor = conn.cursor()


#cursor.execute

conn.commit()
conn.close()

print(f"Banco de dados criado com sucesso em: {PASTA_DB}")