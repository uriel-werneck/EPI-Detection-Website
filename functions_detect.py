import cv2
from ultralytics import YOLO

model = YOLO('app/static/model/yolov8s_custom.pt')

TRANSLATIONS = {
    "helmet": "capacete",
    "vest": "colete",
    "gloves": "luvas",
    "boots": "botas",
    "safety-boot": "botas de segurança",
    "safety-vest": "colete de segurança",
    "glass": "vidro",
    "worker": "trabalhador",
    "person": "pessoa",
}

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
        colors = [(255, 0, 0) for _ in range(len(boxes))]  

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)

        cv2.rectangle(image, (x1, y1), (x2, y2), colors[i], 5)  

        if class_names and i < len(class_names):
            class_name = class_names[i]
            label = f"{class_name}"

            font_scale = 1.5
            font_thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
            )
            text_y = y1 - text_height - 5 if y1 - text_height - 5 > 0 else y1 + text_height + 5

            cv2.putText(image, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (255, 0, 0), font_thickness, cv2.LINE_AA)

    return image

def process_image_with_yolo(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model(image_rgb)
    if not results or not results[0].boxes:
        print("Nenhuma detecção encontrada na imagem.")
        return [], []
    boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []
    classes = results[0].boxes.cls.cpu().numpy().astype(int) if results[0].boxes else []
    class_names = [TRANSLATIONS.get(model.names[cls].lower(), model.names[cls].lower()) for cls in classes]
    print(f"Classes detectadas: {class_names}")
    return class_names, boxes