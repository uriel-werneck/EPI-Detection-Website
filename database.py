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
    # Definindo a URI de conexão do banco de dados
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desabilitar a modificação do track para performance
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Criar todas as tabelas

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
    email_confirmado = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<User {self.nome} {self.sobrenome}>'

# Definindo o modelo Detection
class Detection(db.Model):
    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Relaciona a detecção com o usuário
    file_name = db.Column(db.String(200), nullable=False)
    detection_data = db.Column(db.Text, nullable=False)  # Dados de detecção armazenados como texto
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    upload_type = db.Column(db.String(10), nullable=False)  # Tipo de upload: 'imagem' ou 'video'
    quantity = db.Column(db.Integer, nullable=False)  # Quantidade de objetos detectados
    detected_classes = db.Column(db.Text, nullable=False)  # Classes dos objetos detectados

    def __repr__(self):
        return f'<Detection {self.id} - User {self.user_id}>'

if __name__ == '__main__':
    app = Flask(__name__)
    init_db(app)