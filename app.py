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
from datetime import datetime, timedelta
from sqlalchemy import func, text
import json
import math

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
    video_count = Detection.query.filter_by(user_id=current_user.id, upload_type='upload-video').count()
    time_series_data = get_time_series_data(current_user.id)
    detection_stats = {
        "total_images": len(detections),
        "video_count": video_count,
        "detected_classes": get_detected_classes(detections),
        "time_series_data": time_series_data
    }
    return render_template("dashboard/home.html", detection_stats=detection_stats)

def get_detected_classes(detections):
    class_counts = {}
    for detection in detections:
        classes = detection.detected_classes.split(',')
        for cls in classes:
            if cls and cls in TRANSLATIONS.values():
                class_counts[cls] = class_counts.get(cls, 0) + 1
    return class_counts

def get_time_series_data(user_id):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    formatted_dates = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%d/%m/%Y')
        formatted_dates.append(date_str)
        current_date += timedelta(days=1)
    detections_data = [0] * len(formatted_dates)
    uploads_data = [0] * len(formatted_dates)
    raw_sql = text("""
        SELECT 
            date(timestamp) as date_only, 
            SUM(quantity) as total_detections, 
            COUNT(id) as upload_count
        FROM detections
        WHERE 
            user_id = :user_id AND
            timestamp >= :start_date AND
            timestamp <= :end_date
        GROUP BY date_only
        ORDER BY date_only
    """)
    result = db.session.execute(
        raw_sql, 
        {"user_id": user_id, "start_date": start_date, "end_date": end_date}
    )
    daily_data = {}
    for row in result:
        db_date = row[0]
        total_detections = row[1]
        upload_count = row[2]
        display_date = datetime.strptime(str(db_date), '%Y-%m-%d').strftime('%d/%m/%Y')
        daily_data[display_date] = {
            'detections': int(total_detections or 0),
            'uploads': int(upload_count or 0)
        }
    for i, date_str in enumerate(formatted_dates):
        if date_str in daily_data:
            detections_data[i] = daily_data[date_str]['detections']
            uploads_data[i] = daily_data[date_str]['uploads']
    print("=" * 50)
    print("TIME SERIES DEBUG INFO")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Formatted dates: {formatted_dates}")
    print(f"Daily data from DB: {daily_data}")
    print(f"Final detections data: {detections_data}")
    print(f"Final uploads data: {uploads_data}")
    print("=" * 50)
    if all(x == 0 for x in detections_data) and all(x == 0 for x in uploads_data):
        print("WARNING: All data is zero. Adding test data for today.")
        today_index = formatted_dates.index(end_date.strftime('%d/%m/%Y'))
        today_detections = Detection.query.filter(
            Detection.user_id == user_id,
            func.date(Detection.timestamp) == func.date(end_date)
        ).all()
        if today_detections:
            today_count = sum(d.quantity for d in today_detections)
            detections_data[today_index] = today_count
            uploads_data[today_index] = len(today_detections)
            print(f"Added test data: {today_count} detections, {len(today_detections)} uploads")
    return {
        "dates": formatted_dates,
        "detections": detections_data,
        "uploads": uploads_data
    }

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
                    detected_classes=','.join(class_names),
                    timestamp=datetime.now()
                )
                db.session.add(detection)
                db.session.commit()
                print(f"New detection added: {detection.id}, timestamp: {detection.timestamp}")
                print(f"Detection classes: {detection.detected_classes}")
                print(f"Detection quantity: {detection.quantity}")
                flash('Imagem processada com sucesso! Clique em "Ver no Dashboard" para visualizar as estatísticas atualizadas.', 'success')
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
            flash('e-mail ou senha incorretos', 'Erro')
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

@app.route("/relatorios")
@login_required
def relatorios():
    detections = Detection.query.filter_by(user_id=current_user.id).all()
    video_count = Detection.query.filter_by(user_id=current_user.id, upload_type='upload-video').count()
    time_series_data = get_time_series_data(current_user.id)
    
    detection_stats = {
        "total_images": len(detections),
        "video_count": video_count,
        "detected_classes": get_detected_classes(detections),
        "time_series_data": time_series_data
    }
    
    now = datetime.now()
    
    return render_template("dashboard/relatorios.html", detection_stats=detection_stats, now=now)

@app.route("/minhas-deteccoes")
@login_required
def minhas_deteccoes():
    page = request.args.get('page', 1, type=int)
    per_page = 9  
    
    date_filter = request.args.get('date')
    class_filter = request.args.get('class')
    
    query = Detection.query.filter_by(user_id=current_user.id)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            query = query.filter(
                func.date(Detection.timestamp) == filter_date.date()
            )
        except ValueError:
            flash('Formato de data inválido. Use YYYY-MM-DD.', 'error')
    
    if class_filter:
        query = query.filter(Detection.detected_classes.like(f'%{class_filter}%'))
    
    query = query.order_by(Detection.timestamp.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    detections = pagination.items
    
    all_classes = set()
    for detection in Detection.query.filter_by(user_id=current_user.id).all():
        classes = detection.detected_classes.split(',')
        all_classes.update([cls for cls in classes if cls])
    
    detection_data = []
    for detection in detections:
        processed_filename = f"processed_{detection.file_name}"
        
        file_path = os.path.join(app.config['RESULTS_FOLDER'], processed_filename)
        file_exists = os.path.isfile(file_path)
        
        formatted_date = detection.timestamp.strftime('%d/%m/%Y %H:%M')
        
        classes = detection.detected_classes.split(',')
        
        detection_data.append({
            'id': detection.id,
            'filename': processed_filename,
            'original_filename': detection.file_name,
            'date': formatted_date,
            'classes': classes,
            'quantity': detection.quantity,
            'file_exists': file_exists
        })
    
    return render_template(
        "dashboard/minhas-deteccoes.html",
        detections=detection_data,
        pagination=pagination,
        all_classes=sorted(all_classes),
        current_date_filter=date_filter,
        current_class_filter=class_filter
    )

if __name__ == '__main__':
    app.run(debug=True)

