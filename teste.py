from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("index.html")

# Rota para Upload
@app.route("/upload")
def upload():
    return render_template("upload.html")

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