from flask import Flask, render_template, request, url_for
import os
from functions_detect import process_image_with_yolo, process_video_with_classes

app = Flask(__name__)

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

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        uploaded_files = request.files.getlist("arquivos")  # Obtém todos os arquivos enviados
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


if __name__ == "__main__":
    app.run(debug=True)
