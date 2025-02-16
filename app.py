from flask import Flask, render_template, request, url_for
import os
from functions_detect import process_image_with_yolo, process_video_with_classes
from database import db, init_db, User
from werkzeug.security import generate_password_hash

app = Flask(__name__)
init_db(app)


# Configuração para uploads
UPLOAD_FOLDER = 'static/uploads'
RESULTS_FOLDER = 'static/results'
TXT_FOLDER = 'static/txt'

# Verifique se as pastas existem, se não, crie-as
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, TXT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'mp4'

def can_register(email: str, senha: str, confirmar_senha: str) -> bool:
    '''verifica se os dados para registrar a conta estão corretos'''
    user_with_email = User.query.filter_by(email=email).first()
    if user_with_email:
        print('Já existe um usuário com esse email!')
        return False
    if senha != confirmar_senha:
        print('Senhas não conhicidem!')
        return False
    return True

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get('nome')
        sobrenome = request.form.get('sobrenome')
        cpf = request.form.get('cpf')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmar_senha')

        if can_register(email, senha, confirmar_senha):
            # criptografa a senha antes de salvar no banco de dados
            hash_password = generate_password_hash(senha) 

            # registra o usuário no banco de dados
            new_user = User(nome=nome, sobrenome=sobrenome, cpf=cpf, telefone=telefone, email=email, senha=hash_password, confirmar_senha=hash_password)
            db.session.add(new_user)
            db.session.commit()
            print('Usuário registrado com sucesso!')

            return render_template("index.html") # Redireciona para a página de login
        
    return render_template("cadastro.html")

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        uploaded_files = request.files.getlist("arquivos")  
        file_urls = []  # URLs das imagens com boxes
        file_classes = []  # Classes dos objetos detectados

        for file in uploaded_files:
            if file and allowed_file(file.filename):
                # Salvar o arquivo enviado
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Processar a imagem com YOLO
                if filename.lower().endswith(('jpg', 'jpeg', 'png')):
                    result_url, classes = process_image_with_yolo(file_path)
                    file_urls.append(result_url)  # URL da imagem com as caixas
                    file_classes.append(classes)  # Lista das classes detectadas

                # Processar vídeos
                elif filename.lower().endswith('mp4'):
                    output_video_path = os.path.join(app.config['RESULTS_FOLDER'], f"processed_{filename}")
                    process_video_with_classes(file_path, output_video_path)
                    file_urls.append(url_for('static', filename=f'results/processed_{filename}'))
                    file_classes.append(["Vídeo processado com sucesso."])

        return render_template("upload.html", file_urls=file_urls, file_classes=file_classes)

    return render_template("upload.html", file_urls=None, file_classes=None)

# nova rota para upload somente de videos
@app.route("/upload_videos", methods=["GET", "POST"])
def upload_videos():
    if request.method == "POST":
        uploaded_files = request.files.getlist("arquivos_videos")  # Certifique-se de que o nome do campo está correto
        file_urls = []  # URLs dos vídeos processados

        for file in uploaded_files:
            if file and allowed_video(file.filename):  # Verificar se é vídeo
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Processar o vídeo com YOLO
                output_video_path = os.path.join(app.config['RESULTS_FOLDER'], f"processed_{filename}")
                result = process_video_with_classes(file_path, output_video_path)
                if result is None:
                    print(f"Erro ao processar o vídeo: {filename}")
                    continue
                
                # Adicionar URL do vídeo processado para exibição
                file_urls.append(url_for('static', filename=f'results/processed_{filename}'))

        return render_template("upload_videos.html", file_urls=file_urls)

    return render_template("upload_videos.html", file_urls=None)



@app.route("/relatorios")
def relatorios():
    reports = []
    # Iterar sobre todos os arquivos de relatório na pasta TXT_FOLDER
    for txt_file in os.listdir(TXT_FOLDER):
        if txt_file.endswith('.txt'):  # Garantir que estamos lidando apenas com arquivos .txt
            report = {}
            txt_path = os.path.join(TXT_FOLDER, txt_file)

            # Substituir extensão do arquivo para encontrar a imagem correspondente
            image_name = txt_file.replace('.txt', '.png')  # Use '.png' ou outra extensão conforme necessário
            image_path = os.path.join(RESULTS_FOLDER, image_name)

            # Verificar se a imagem correspondente existe
            if os.path.exists(image_path):
                report['image_url'] = url_for('static', filename=f'results/{image_name}')
            else:
                report['image_url'] = None  # Para evitar erros se a imagem não for encontrada

            # Ler os objetos detectados do relatório .txt
            report['objects'] = []
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[2:]:  # Ignorar as duas primeiras linhas do cabeçalho
                    report['objects'].append(line.strip())

            reports.append(report)

    return render_template("relatorios.html", reports=reports)


if __name__ == '__main__':
    # Criar as tabelas no banco de dados (executar uma vez)
    with app.app_context():
        print("Tentando criar as tabelas...")
        db.create_all()  # Cria as tabelas no banco de dados
    app.run(debug=True)
