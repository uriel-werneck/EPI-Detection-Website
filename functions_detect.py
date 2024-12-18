import os
import cv2
from ultralytics import YOLO
from flask import url_for

# Configurações de pastas
UPLOAD_FOLDER = 'static/uploads'
RESULTS_FOLDER = 'static/results'
TXT_FOLDER = 'static/txt'

# Inicializar o modelo YOLO
model = YOLO('static/model/yolov8s_custom.pt')

TRANSLATIONS = {
    "helmet": "capacete",
    "vest": "colete",
    "gloves": "luvas",
    "boots": "botas",
    "safety-boot": "botas  de segurança",
    "safety-vest": "colete de segurança",
    "glass": "vidro",
    "worker": "trabalhador",
    "person": "pessoa",
   
}

# Função para desenhar boxes de detecção na imagem
def draw_bounding_boxes(image, boxes, class_names=None, colors=None):
    """
    Desenha caixas coloridas ao redor dos objetos detectados com os nomes das classes.
    :param image: A imagem onde as caixas serão desenhadas.
    :param boxes: As coordenadas das caixas a serem desenhadas.
    :param class_names: Lista com os nomes das classes correspondentes às caixas.
    :param colors: Lista de cores para cada caixa (opcional).
    :return: A imagem com as caixas desenhadas.
    """
    if colors is None:
        colors = [(255, 0, 0) for _ in range(len(boxes))]  # Padrão: cor vermelha

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)

        # Desenhar o retângulo
        cv2.rectangle(image, (x1, y1), (x2, y2), colors[i], 5)  # Espessura 2

        # Adicionar o nome da classe, se fornecido
        if class_names and i < len(class_names):
            class_name = class_names[i]
            label = f"{class_name}"

            # Desenhar o texto acima da caixa
            font_scale = 1.5
            font_thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
            )
            text_y = y1 - text_height - 5 if y1 - text_height - 5 > 0 else y1 + text_height + 5

            # cor das letras
            cv2.putText(image, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (255, 0, 0), font_thickness, cv2.LINE_AA)

    return image

# Função para salvar e retornar URLs de imagens com caixas e classes
def process_image_with_yolo(image_path):
    # Carregar a imagem
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Realizar a detecção com YOLO
    results = model(image_rgb)
    boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []  # Coordenadas das boxes detectadas
    classes = results[0].boxes.cls.cpu().numpy().astype(int) if results[0].boxes else []  # IDs das classes detectadas

    # Mapear os IDs das classes para os nomes traduzidos
    class_names = [TRANSLATIONS.get(model.names[cls].lower(), model.names[cls].lower()) for cls in classes]

    # Criar o relatório de texto
    txt_path = os.path.join(TXT_FOLDER, f"{os.path.basename(image_path).split('.')[0]}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
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

# Função para processar vídeos com YOLO.
def process_video_with_classes(video_path, output_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Erro ao abrir o vídeo: {video_path}")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processando vídeo: {video_path} ({frame_count} frames, {fps} FPS)")

    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = model(frame_rgb)
        boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int) if results[0].boxes else []
        class_names = [model.names[class_id] for class_id in class_ids] if results[0].boxes else []
        frame_with_boxes = draw_bounding_boxes(frame, boxes, class_names)
        out.write(frame_with_boxes)

        frame_idx += 1
        if frame_idx % 10 == 0:
            print(f"Frame {frame_idx}/{frame_count} processado.")

    cap.release()
    out.release()
    print(f"Vídeo salvo em: {output_path}")
    return output_path
