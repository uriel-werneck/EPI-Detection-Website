from flask import Flask, render_template, request, url_for, redirect, flash, session
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import db, init_db, User, Detection
from validate_docbr import CPF
import numpy as np
import cv2 as cv
from ultralytics import YOLO
from functions_detect import process_image_with_yolo, draw_bounding_boxes  
from functions_detect import TRANSLATIONS

model = YOLO(os.path.join('app', 'static', 'model', 'yolov8s_custom.pt'))

cpf_validator = CPF()  

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = os.path.join(static_dir, 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join(static_dir, 'results')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

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
    detections = Detection.query.filter_by(user_id=current_user.id).all()

    detection_stats = {
        "total_images": len(detections),  
        "detected_classes": get_detected_classes(detections),  
    }

    return render_template("dashboard/home.html", detection_stats=detection_stats)

def get_detected_classes(detections):
    class_counts = {}
    for detection in detections:
        classes = detection.detected_classes.split(',')
        for cls in classes:
            if cls in TRANSLATIONS.values():
                class_counts[cls] = class_counts.get(cls, 0) + 1
    return class_counts

@app.route('/dashboard/upload/<type>', methods=['GET', 'POST'])
@login_required
def upload(type):
    if request.method == 'GET':
        if type == 'upload-imagem':
            return render_template('dashboard/upload/upload-imagem.html')
        elif type == 'upload-video':
            return render_template('dashboard/upload/upload-video.html')

    file = request.files.get('image') if type == 'upload-imagem' else request.files.get('video')
    if file and file.filename:
        file_bytes = file.read()
        if type == 'upload-imagem':
            image = cv.imdecode(np.frombuffer(file_bytes, np.uint8), cv.IMREAD_COLOR)
            class_names, boxes = process_image_with_yolo(image)  

            if class_names:
                image_with_boxes = draw_bounding_boxes(image, boxes, class_names)
                result_filename = f"processed_{file.filename}"
                result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
                cv.imwrite(result_path, image_with_boxes)

                detection = Detection(
                    user_id=current_user.id,
                    file_name=file.filename,
                    detection_data=','.join(class_names),
                    upload_type=type,
                    quantity=len(class_names),
                    detected_classes=','.join(class_names)
                )
                db.session.add(detection)
                db.session.commit()

                return render_template('dashboard/upload/upload-imagem.html', processed_image=result_filename)
            else:
                flash('Nenhuma classe detectada na imagem.', 'warning')
        else:
            flash('Tipo de upload não suportado.', 'error')
    else:
        flash('Nenhum arquivo selecionado ou arquivo inválido.', 'error')

    return redirect(url_for('upload', type=type))

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
            flash('Incorrect email or password', 'error')
    
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