from flask import Flask, render_template
"Flask lo que hace es linkear funciones usando decoradores, con direcciones de la página web, entonces /app/reiniciar llama a la función decorada con @app.route('/reiniciar')"

app = Flask(__name__)
 
@app.route('/')
def index():
    diccTest = {
        "titulo":"hola si",
        "otro": "¿Quién habla?"
    }
    return render_template('index.html', data = diccTest)

if __name__ == "__main__":
    app.run(host = "127.0.0.1", port = 5000, debug = True) # A esta función la tiene que llamar Canal79.py