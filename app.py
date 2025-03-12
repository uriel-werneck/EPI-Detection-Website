from flask import Flask, render_template, request, url_for, redirect, flash, session
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import db, init_db, User
from validate_docbr import CPF
import numpy as np
import cv2 as cv
from ultralytics import YOLO

model = YOLO(r'C:\Users\uriel\Área de Trabalho\EPI-Detection-Website\app\static\model\yolov8s_custom.pt')

cpf_validator = CPF() # validador de cpf

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your_secret_key_here'  
init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/home")
@login_required
def home():
    return render_template("dashboard/home.html")

@app.route('/dashboard/upload/<type>', methods=['GET', 'POST'])
@login_required
def upload(type):
    if request.method == 'GET':
        if type == 'upload-imagem':
            return render_template('dashboard/upload/upload-imagem.html')
        elif type == 'upload-video':
            return render_template('dashboard/upload/upload-video.html')
        
    file = request.files.get('image')
    if file and file.name:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv.imdecode(file_bytes, cv.IMREAD_COLOR)

        result = model.predict(image, verbose=False)[0]
        classes_map = result.names
        boxes = result.boxes
        classes_list = boxes.cls.int().tolist()
        confidence_list = [float(f'{conf:.2f}') for conf in boxes.conf.tolist()]
        # creating text
        file_text = ['class;confidence\n']
        for class_id, conf in zip(classes_list, confidence_list):
            file_text.append(f'{classes_map[class_id]};{conf}\n')
        file_text[-1] = file_text[-1].removesuffix('\n')

        # salvar dados no banco de dados com id do usuário
        print(file_text)
    
    if type == 'image':
        # passar o path da imagem (s) como parâmetro
        return render_template('dashboard/upload/upload-imagem.html')
    elif type == 'video':
        return render_template('dashboard/upload/upload-video.html')
    # return redirect(url_for('home'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.senha, senha):
            login_user(user)
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Email ou senha incorretos', 'error')
    
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    return render_template("auth/login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    return redirect(url_for('index'))

def can_register(email: str, senha: str, confirmar_senha: str, cpf: str) -> bool:
    '''verifica se os dados para registrar a conta estão corretos'''
    user_with_email = User.query.filter_by(email=email).first()
    if user_with_email:
        flash('Já existe um usuário com esse email!', 'error')
        return False
    
    if not cpf_validator.validate(cpf):
        flash('CPF inválido!', 'error')
        return False
    
    user_with_cpf = User.query.filter_by(cpf=cpf).first()
    if user_with_cpf:
        flash('Já existe um usuário com esse CPF!')
        return False
    
    if senha != confirmar_senha:
        flash('Senhas não coincidem!', 'error')
        return False
    return True

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get('nome')
        sobrenome = request.form.get('sobrenome')
        cpf = request.form.get('cpf')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmar_senha')

        if can_register(email, senha, confirmar_senha, cpf):
            hash_password = generate_password_hash(senha)
            new_user = User(nome=nome, sobrenome=sobrenome, cpf=cpf, telefone=telefone, email=email, senha=hash_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuário registrado com sucesso!', 'success')
            return redirect(url_for('login'))
    
    if 'user_id' in session:
        return redirect(url_for('home'))
        
    return render_template("auth/register.html")

if __name__ == '__main__':
    app.run(debug=True)