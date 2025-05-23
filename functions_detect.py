import cv2
import os
import datetime
from ultralytics import YOLO
import numpy as np
import base64
from io import BytesIO

model = YOLO('app/static/model/modelo 1 (93 epochs).pt')

RESULTS_FRAMES_FOLDER = 'app/static/results/frames'
TXT_VIDEOS_FOLDER = 'app/static/results/txt'

os.makedirs(RESULTS_FRAMES_FOLDER, exist_ok=True)
os.makedirs(TXT_VIDEOS_FOLDER, exist_ok=True)

TRANSLATIONS = {
    "helmet": "capacete",
    "no-helmet": "sem-capacete",
    "vest": "colete",
    "no-vest": "sem-colete",
    "person": "pessoa",
}

COLORS = {
    "capacete": {
        'body': (255, 255, 0),
        'text': (0, 0, 0)
    },
    "sem-capacete":{
        'body': (0, 0, 255),
        'text': (255, 255, 255)
    },
    "colete": {
        'body': (255, 0, 0),
        'text': (255, 255, 255)
    },
    "sem-colete": {
        'body': (0, 0, 255),
        'text': (255, 255, 255)
    },
    "pessoa": {
        'body': (165, 2, 138), 
        'text': (255, 255, 255)
    }
}


def draw_bounding_boxes(image, boxes, class_names=None):
    """
    Desenha caixas coloridas ao redor dos objetos detectados com os nomes das classes.
    :param image: A imagem onde as caixas serão desenhadas.
    :param boxes: As coordenadas das caixas a serem desenhadas.
    :param class_names: Lista com os nomes das classes correspondentes às caixas.
    :param colors: Lista de cores para cada caixa (opcional).
    :return: A imagem com as caixas desenhadas.
    """

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)

        if class_names and i < len(class_names):
            class_name = class_names[i]
            label = f"{class_name}"

            cv2.rectangle(image, (x1, y1), (x2, y2), COLORS[class_name]['body'], 5)

            (compr_texto, larg_texto), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 1.5, 2)
            caixa_id = cv2.rectangle(image, (x1, y1 - 29), (x1 + compr_texto, y1), COLORS[class_name]['body'], -1)
            cv2.putText(caixa_id, label, (x1, y1 - 3), cv2.FONT_HERSHEY_DUPLEX, 1.5, COLORS[class_name]['text'], 2)

    return image

def process_image_with_yolo(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model(image_rgb, conf=0.12)
    if not results or not results[0].boxes:
        print("Nenhuma detecção encontrada na imagem.")
        return [], []
    boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []
    classes = results[0].boxes.cls.cpu().numpy().astype(int) if results[0].boxes else []
    class_names = [TRANSLATIONS.get(model.names[cls].lower(), model.names[cls].lower()) for cls in classes]
    print(f"Classes detectadas: {class_names}")
    return class_names, boxes

def process_video_with_classes(video_path, output_path):
    """
    Processa um vídeo para detectar EPIs e retorna informações sobre as detecções.
    :param video_path: Caminho para o arquivo de vídeo
    :param output_path: Caminho para salvar o vídeo processado
    :return: Dicionário com informações sobre o processamento do vídeo
    """
    creation_time = os.path.getctime(video_path)
    formatted_date = datetime.datetime.fromtimestamp(creation_time).strftime('%d/%m/%Y %H:%M:%S')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Erro ao abrir o vídeo: {video_path}")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processando vídeo: {video_path} ({frame_count} frames, {fps} FPS)")

    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    detected_classes = {}
    frame_info = []  

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = model(frame_rgb)
        boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int) if results[0].boxes else []
        class_names = [TRANSLATIONS.get(model.names[class_id].lower(), model.names[class_id].lower()) for class_id in class_ids] if results[0].boxes else []

        frame_with_boxes = draw_bounding_boxes(frame, boxes, class_names)

        frame_info.append({
            'frame': frame_with_boxes,
            'num_objects': len(class_names),
            'class_names': class_names
        })

        for class_name in class_names:
            if class_name in detected_classes:
                detected_classes[class_name] += 1
            else:
                detected_classes[class_name] = 1

        out.write(frame_with_boxes)
        frame_idx += 1

    cap.release()
    out.release()
    print(f"Vídeo salvo em: {output_path}")

    frame_info.sort(key=lambda x: x['num_objects'], reverse=True)

    max_objects = frame_info[0]['num_objects'] if frame_info else 0
    max_frames = [frame for frame in frame_info if frame['num_objects'] == max_objects] if frame_info else []

    selected_frame = max_frames[-1] if max_frames else None  
    
    result_info = {
        'detected_classes': [],
        'max_objects': 0,
        'frame_image_base64': None,
        'frame_filename': None,
        'total_frames': frame_idx,
        'creation_date': formatted_date
    }
    
    if selected_frame:
        selected_frame_image = selected_frame['frame']
        selected_frame_class_names = selected_frame['class_names']
        
        frame_filename = os.path.join(RESULTS_FRAMES_FOLDER, f"{os.path.basename(video_path).split('.')[0]}_max_objects_frame.jpg")
        cv2.imwrite(frame_filename, selected_frame_image)
        
        _, buffer = cv2.imencode('.jpg', selected_frame_image)
        frame_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        txt_path = os.path.join(TXT_VIDEOS_FOLDER, f"{os.path.basename(video_path).split('.')[0]}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Relatório de Detecção de Classes - {os.path.basename(video_path)} - Data de criação: {formatted_date}\n")
            f.write(f"Frame com maior quantidade de classes ({max_objects} objetos):\n")
            for class_name in selected_frame_class_names:
                f.write(f"{class_name}\n")
        
        result_info.update({
            'detected_classes': selected_frame_class_names,
            'max_objects': max_objects,
            'frame_image_base64': frame_image_base64,
            'frame_filename': os.path.basename(frame_filename)
        })
    
    return result_info

def image_to_base64(image):
    """
    Converte uma imagem OpenCV para base64 para armazenamento no banco de dados.
    :param image: Imagem OpenCV
    :return: String base64 da imagem
    """
    _, buffer = cv2.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')

def base64_to_image(base64_string):
    """
    Converte uma string base64 para uma imagem OpenCV.
    :param base64_string: String base64 da imagem
    :return: Imagem OpenCV
    """
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

