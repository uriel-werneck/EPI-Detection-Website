from flask import Flask, render_template, request, url_for, redirect
import os
from werkzeug.security import generate_password_hash
from database import db, init_db, User

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
init_db(app)

@app.route("/home")
def home():
    return render_template("dashboard/home.html")

@app.route('/dashboard/upload/<type>')
def upload(type):
    if type == 'upload-imagem':
        return render_template('dashboard/upload/upload-imagem.html')
    elif type == 'upload-video':
        return render_template('dashboard/upload/upload-video.html')
    return redirect(url_for('home'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        senha = request.form.get('senha')
        # ...lógica de autenticação 
        return redirect(url_for('home'))
    return render_template("auth/login.html")

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

        if can_register(email, senha, confirmar_senha):
            hash_password = generate_password_hash(senha)
            new_user = User(nome=nome, sobrenome=sobrenome, cpf=cpf, telefone=telefone, email=email, senha=hash_password)
            db.session.add(new_user)
            db.session.commit()
            print('Usuário registrado com sucesso!')
            return redirect(url_for('login'))
        
    return render_template("auth/register.html")

if __name__ == '__main__':
    app.run(debug=True)