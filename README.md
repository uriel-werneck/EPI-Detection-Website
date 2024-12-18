# Projeto de Detecção de Objetos com YOLOv8 e Flask

Este projeto utiliza o modelo YOLOv8 para detecção de objetos em imagens e vídeos, integrando-o a uma aplicação web com Flask. O modelo YOLOv8 é utilizado para identificar e rotular objetos em tempo real, como capacetes, coletes, botas, entre outros, em imagens ou vídeos enviados pelos usuários.

## Funcionalidades

- **Upload de Imagens e Vídeos:** O usuário pode enviar imagens (PNG, JPG, JPEG) e vídeos (MP4) para o servidor.
- **Detecção de Objetos:** O modelo YOLOv8 detecta objetos nas imagens e vídeos enviados.
- **Relatórios de Detecção:** Para cada imagem processada, um relatório de texto é gerado com os objetos detectados.
- **Exibição de Resultados:** As imagens com caixas delimitadoras e os rótulos dos objetos são exibidas após o processamento.

## Apresentação do Projeto

Aqui está uma demonstração do funcionamento do sistema:

![Demonstração do sistema](Video.gif)

## Requisitos

- Python 3.x
- Flask
- OpenCV
- Ultralytics (para YOLOv8)
- Torch (PyTorch)

## Instalação

1. Clone este repositório:

   ```bash
   git clone <url-do-repositorio>
   cd <diretorio-do-projeto>
   pip install -r requirements.txt
