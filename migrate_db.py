from flask import Flask
from database import db, init_db
import sqlite3
import os

app = Flask(__name__)

# Verificar o caminho correto do banco de dados
# Tente encontrar o banco de dados em diferentes locais comuns
possible_paths = [
    'users.db',                      # Na raiz do projeto
    'instance/users.db',             # Na pasta instance (padrão Flask)
    '../users.db',                   # Um nível acima
    'app/users.db',                  # Na pasta app
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')  # No mesmo diretório deste script
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        print(f"Banco de dados encontrado em: {path}")
        break

if db_path is None:
    print("Banco de dados não encontrado em nenhum local comum.")
    # Pergunte ao usuário onde está o banco de dados
    user_path = input("Por favor, digite o caminho completo para o banco de dados users.db: ")
    if os.path.exists(user_path):
        db_path = user_path
        print(f"Banco de dados encontrado em: {db_path}")
    else:
        print("Caminho fornecido não existe. Criando novo banco de dados na raiz do projeto.")
        db_path = 'users.db'

# Configure a aplicação com o caminho correto do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def add_columns_if_not_exist():
    if not os.path.exists(db_path):
        print(f"Banco de dados não encontrado em {db_path}. Criando novo banco de dados.")
        with app.app_context():
            init_db(app)
        return
    
    # Conectar ao banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar se a tabela detections existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='detections'")
    if not cursor.fetchone():
        print("Tabela 'detections' não existe. Criando tabela...")
        with app.app_context():
            init_db(app)
        conn.close()
        return
    
    # Verificar se as colunas existem
    cursor.execute("PRAGMA table_info(detections)")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Colunas existentes: {columns}")
    
    # Adicionar colunas se não existirem
    if 'image_data' not in columns:
        print("Adicionando coluna 'image_data' à tabela detections")
        cursor.execute("ALTER TABLE detections ADD COLUMN image_data TEXT")
    
    if 'video_data' not in columns:
        print("Adicionando coluna 'video_data' à tabela detections")
        cursor.execute("ALTER TABLE detections ADD COLUMN video_data TEXT")
    
    if 'is_stored_in_db' not in columns:
        print("Adicionando coluna 'is_stored_in_db' à tabela detections")
        cursor.execute("ALTER TABLE detections ADD COLUMN is_stored_in_db BOOLEAN DEFAULT 0")
    
    # Commit e fechar conexão
    conn.commit()
    conn.close()
    
    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    add_columns_if_not_exist()

