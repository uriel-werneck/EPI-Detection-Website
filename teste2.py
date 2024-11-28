from flask import Flask, render_template, request, url_for
import os

app = Flask(__name__)
# Configuração para uploads
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Cria o diretório se não existir

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def hello_world():
    return render_template("index.html")

# Rota para Upload
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        uploaded_files = request.files.getlist("arquivos")  # Obtém todos os arquivos enviados
        file_urls = []  # URLs das imagens salvas

        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)  # Salva o arquivo
                file_urls.append(url_for('static', filename=f'uploads/{filename}'))  # Gera URL

        return render_template("upload.html", file_urls=file_urls)  # Envia URLs para exibição

    return render_template("upload.html", file_urls=None)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/desafios/<int:dia>")
def desafio(dia):
    if dia == 1:
        return f"Jogar bola"
    elif dia == 2:
        return f"Estudar"
    else:
        return f"Ler livro"

#http://127.0.0.1:5000/desafios/3
# http://127.0.0.1:5000/desafios/2
# http://127.0.0.1:5000/desafios/1