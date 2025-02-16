from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Inicialização do banco de dados
db = SQLAlchemy()

"""
Criar a tabela:
-> flask shell

 - from database import db
 - db.create_all()
"""

def init_db(app):
    # Definindo a URI de conexão do PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost:5432/epidetection'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desabilitar a modificação do track para performance
    db.init_app(app)
    
# Definindo o modelo User
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    sobrenome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)  # Ex: '123.456.789-01'
    telefone = db.Column(db.String(15), nullable=False)  # Ex: '(11) 98765-4321'
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)  # Senha armazenada de forma segura
    confirmar_senha = db.Column(db.String(200), nullable=False)  # Pode ser usado para verificar a confirmação de senha

    def __repr__(self):
        return f'<User {self.nome} {self.sobrenome}>'

# # Configuração do Flask
# app = Flask(__name__)
# init_db(app)

