from flask import Flask, render_template, request, url_for
import os
import cv2
import torch
from ultralytics import YOLO

app = Flask(__name__)

# Configuração para uploads
UPLOAD_FOLDER = 'static/uploads'
RESULTS_FOLDER = 'static/results'
# configuração para relatorios txt
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

# Função para desenhar boxes de detecção na imagem
def draw_bounding_boxes(image, boxes, labels, colors=None):
    if colors is None:
        colors = [(255, 51, 0) for _ in range(len(boxes))]
    
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(image, (x1, y1), (x2, y2), colors[i], 2)

        # Colocar a classe do objeto no topo da caixa
        cv2.putText(image, str(labels[i]), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 5, colors[i], 8)
        
    return image

# Função para salvar e retornar URLs de imagens com caixas e classes
def process_image_with_yolo(image_path):
    model = YOLO('static/model/yolov8s_custom.pt')  # Caminho do modelo YOLO
    
    # Carregar a imagem
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Realizar a detecção com YOLO
    results = model(image_rgb)
    boxes = results[0].boxes.xyxy.cpu().numpy()  # Coordenadas das boxes detectadas
    labels = results[0].names  # Dicionário com as classes
    classes = results[0].boxes.cls.cpu().numpy()  # Classes dos objetos detectados

    # Mapear os ids das classes para os nomes das classes
    class_names = [labels[int(cls)] for cls in classes]

     # função para gerar os relatorios em txt
    txt_path = os.path.join(TXT_FOLDER, f"{os.path.basename(image_path).split('.')[0]}.txt")
    with open(txt_path, 'w') as f:
        f.write(f"Relatório de Detecção de Objetos - {os.path.basename(image_path)}\n\n")
        for i, class_name in enumerate(class_names):
            f.write(f"Objeto {i+1}: {class_name}\n")

    # Desenhar as caixas e as classes na imagem
    image_with_boxes = draw_bounding_boxes(image_rgb, boxes, class_names)

    # Salvar a imagem com as caixas desenhadas
    result_image_path = os.path.join(RESULTS_FOLDER, os.path.basename(image_path))
    cv2.imwrite(result_image_path, cv2.cvtColor(image_with_boxes, cv2.COLOR_RGB2BGR))

    # Retornar o caminho para visualização
    return url_for('static', filename=f'results/{os.path.basename(result_image_path)}'), class_names

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
                else:
                    file_urls.append(url_for('static', filename=f'uploads/{filename}'))
                    file_classes.append([])  # Nenhuma classe para vídeos

        return render_template("upload.html", file_urls=file_urls, file_classes=file_classes)

    return render_template("upload.html", file_urls=None, file_classes=None)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

if __name__ == "__main__":
    app.run(debug=True)
