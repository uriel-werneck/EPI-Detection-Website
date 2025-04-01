from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

"""
Criar a tabela:
-> flask shell

 - from database import db
 - db.create_all()
"""

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
    db.init_app(app)
    with app.app_context():
        db.create_all() 

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    sobrenome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)     
    telefone = db.Column(db.String(15), nullable=False)  
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)  
    email_confirmado = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<User {self.nome} {self.sobrenome}>'

class Detection(db.Model):
    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  
    file_name = db.Column(db.String(200), nullable=False)
    detection_data = db.Column(db.Text, nullable=False)  
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    upload_type = db.Column(db.String(20), nullable=False)  # Alterado para suportar 'upload-video'
    quantity = db.Column(db.Integer, nullable=False) 
    detected_classes = db.Column(db.Text, nullable=False)
    # Novos campos para armazenar imagens e vídeos no banco de dados
    image_data = db.Column(db.Text)  # Base64 da imagem ou frame do vídeo
    video_data = db.Column(db.Text)  # Base64 do vídeo (se aplicável)
    is_stored_in_db = db.Column(db.Boolean, default=False)  # Indica se está armazenado no banco

    def __repr__(self):
        return f'<Detection {self.id} - User {self.user_id}>'

