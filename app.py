from flask import Flask, render_template, request, url_for, redirect, flash, session, jsonify, send_file
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import db, init_db, User, Detection
from validate_docbr import CPF
import numpy as np
import cv2 as cv
from ultralytics import YOLO
from functions_detect import process_image_with_yolo, draw_bounding_boxes, process_video_with_classes, image_to_base64, base64_to_image
from functions_detect import TRANSLATIONS
from datetime import datetime, timedelta
from sqlalchemy import func, text, inspect
from datetime import datetime, timedelta
import json
import math
import tempfile
import uuid
import sqlite3

model = YOLO(os.path.join('app', 'static', 'model', 'yolov8s_custom.pt'))

cpf_validator = CPF()  

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = os.path.join(static_dir, 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join(static_dir, 'results')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

init_db(app)

def check_columns_exist():
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('detections')]
    return {
        'image_data': 'image_data' in columns,
        'video_data': 'video_data' in columns,
        'is_stored_in_db': 'is_stored_in_db' in columns
    }

with app.app_context():
    columns_exist = check_columns_exist()
    print(f"Colunas existentes no banco: {columns_exist}")

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

def get_time_series_data(user_id, start_date=None, end_date=None):
    if start_date is None or end_date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
    
    days_diff = (end_date - start_date).days
    
    if days_diff < 1:
        days_diff = 1
    
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
    
    return {
        "dates": formatted_dates,
        "detections": detections_data,
        "uploads": uploads_data
    }

@app.route('/dashboard/upload/<type>', methods=['GET', 'POST'])
@login_required
def upload(type):
    columns_exist = check_columns_exist()
    
    if request.method == 'GET':
        if type == 'upload-imagem':
            return render_template('dashboard/upload/upload-imagem.html')
        elif type == 'upload-video':
            return render_template('dashboard/upload/upload-video.html')
        
    if type == 'upload-imagem':
        file = request.files.get('image')
        if file and file.filename:
            file_bytes = file.read()
            image = cv.imdecode(np.frombuffer(file_bytes, np.uint8), cv.IMREAD_COLOR)
            class_names, boxes = process_image_with_yolo(image)  
            if class_names:
                image_with_boxes = draw_bounding_boxes(image, boxes, class_names)
                result_filename = f"processed_{file.filename}"
                result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
                cv.imwrite(result_path, image_with_boxes)
                
                detection_data = {
                    'user_id': current_user.id,
                    'file_name': file.filename,
                    'detection_data': ','.join(class_names),
                    'upload_type': type,
                    'quantity': len(class_names),
                    'detected_classes': ','.join(class_names),
                    'timestamp': datetime.now()
                }
                
                if columns_exist['image_data']:
                    image_base64 = image_to_base64(image_with_boxes)
                    detection_data['image_data'] = image_base64
                
                if columns_exist['is_stored_in_db']:
                    detection_data['is_stored_in_db'] = True
                
                detection = Detection(**detection_data)
                db.session.add(detection)
                db.session.commit()
                
                print(f"New detection added: {detection.id}, timestamp: {detection.timestamp}")
                print(f"Detection classes: {detection.detected_classes}")
                print(f"Detection quantity: {detection.quantity}")
                flash('Imagem processada com sucesso! Clique em "Ver no Dashboard" para visualizar as estatísticas atualizadas.', 'success')
                return render_template('dashboard/upload/upload-imagem.html', processed_image=result_filename)
            else:
                flash('Nenhuma classe detectada na imagem.', 'warning')
                
    elif type == 'upload-video':
        file = request.files.get('video')
        if file and file.filename:
            temp_dir = tempfile.mkdtemp()
            temp_video_path = os.path.join(temp_dir, file.filename)
            file.save(temp_video_path)
            
            unique_id = str(uuid.uuid4())[:8]
            output_filename = f"processed_{unique_id}_{file.filename}"
            output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)
            
            result_info = process_video_with_classes(temp_video_path, output_path)
            
            if result_info:
                detection_data = {
                    'user_id': current_user.id,
                    'file_name': file.filename,
                    'detection_data': ','.join(result_info['detected_classes']),
                    'upload_type': type,
                    'quantity': result_info['max_objects'],
                    'detected_classes': ','.join(result_info['detected_classes']),
                    'timestamp': datetime.now()
                }
                
                if columns_exist['image_data'] and result_info['frame_image_base64']:
                    detection_data['image_data'] = result_info['frame_image_base64']
                
                if columns_exist['is_stored_in_db']:
                    detection_data['is_stored_in_db'] = True
                
                detection = Detection(**detection_data)
                db.session.add(detection)
                db.session.commit()
                
                flash('Vídeo processado com sucesso! Clique em "Ver no Dashboard" para visualizar as estatísticas atualizadas.', 'success')
                return render_template('dashboard/upload/upload-video.html', 
                                      processed_video=output_filename,
                                      frame_image=result_info['frame_filename'],
                                      detected_classes=result_info['detected_classes'],
                                      max_objects=result_info['max_objects'])
            else:
                flash('Erro ao processar o vídeo.', 'error')
                
            try:
                os.remove(temp_video_path)
                os.rmdir(temp_dir)
            except:
                pass
        else:
            flash('Nenhum arquivo selecionado ou arquivo inválido.', 'error')
    else:
        flash('Tipo de upload não suportado.', 'error')
        
    return redirect(url_for('upload', type=type))

@app.route('/get-detection-image/<int:detection_id>')
@login_required
def get_detection_image(detection_id):
    columns_exist = check_columns_exist()
    detection = Detection.query.filter_by(id=detection_id, user_id=current_user.id).first()
    
    if not detection:
        return "Detecção não encontrada", 404
    
    if columns_exist['image_data'] and hasattr(detection, 'image_data') and detection.image_data:
        image = base64_to_image(detection.image_data)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.close()
        cv.imwrite(temp_file.name, image)
        
        return send_file(temp_file.name, mimetype='image/jpeg', as_attachment=True, 
                        download_name=f"detection_{detection_id}.jpg")
    else:
        processed_filename = f"processed_{detection.file_name}"
        file_path = os.path.join(app.config['RESULTS_FOLDER'], processed_filename)
        
        if os.path.isfile(file_path):
            return send_file(file_path, mimetype='image/jpeg', as_attachment=True,
                            download_name=processed_filename)
        else:
            return "Imagem não encontrada", 404

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
    if '_flashes' in session:
        session['_flashes'].clear()
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
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    show_all = request.args.get('show_all') == 'true'
    media_type = request.args.get('media_type', 'all')  
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    using_custom_filter = False
    
    if show_all:
        start_date = datetime(2000, 1, 1)  
        end_date = datetime.now()
        using_custom_filter = False
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            using_custom_filter = True
        except ValueError:
            flash('Formato de data inválido. Use YYYY-MM-DD.', 'error')
    
    print(f"DEBUG: Date filter - start_date: {start_date}, end_date: {end_date}")
    print(f"DEBUG: Using custom filter: {using_custom_filter}, show_all: {show_all}")
    print(f"DEBUG: Media type filter: {media_type}")
    
    query = Detection.query.filter(
        Detection.user_id == current_user.id,
        Detection.timestamp >= start_date,
        Detection.timestamp <= end_date
    )
    
    if media_type == 'image':
        query = query.filter(Detection.upload_type == 'upload-imagem')
    elif media_type == 'video':
        query = query.filter(Detection.upload_type == 'upload-video')
    
    detections = query.all()
    
    print(f"DEBUG: Found {len(detections)} detections in date range with media type filter: {media_type}")
    
    video_query = query.filter(Detection.upload_type == 'upload-video')
    video_count = video_query.count()
    
    time_series_data = get_time_series_data(current_user.id, start_date, end_date)
    
    detection_stats = {
        "total_images": len(detections),
        "video_count": video_count,
        "detected_classes": get_detected_classes(detections),
        "time_series_data": time_series_data,
        "date_filter": {
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "is_custom": using_custom_filter,
            "show_all": show_all
        },
        "media_type": media_type  
    }
    
    now = datetime.now()
    
    return render_template("dashboard/relatorios.html", detection_stats=detection_stats, now=now)

@app.route("/minhas-deteccoes")
@login_required
def minhas_deteccoes():
    columns_exist = check_columns_exist()
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
        
        file_exists = True
        is_stored_in_db = False
        
        if columns_exist['is_stored_in_db'] and hasattr(detection, 'is_stored_in_db') and detection.is_stored_in_db:
            if columns_exist['image_data'] and hasattr(detection, 'image_data') and detection.image_data:
                processed_filename = f"/get-detection-image/{detection.id}"
                is_stored_in_db = True
            else:
                file_path = os.path.join(app.config['RESULTS_FOLDER'], processed_filename)
                file_exists = os.path.isfile(file_path)
        else:
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
            'file_exists': file_exists,
            'upload_type': detection.upload_type,
            'is_stored_in_db': is_stored_in_db
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