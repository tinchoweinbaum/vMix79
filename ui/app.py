import sys
import threading

from flask import Flask, render_template
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR.parent))
from scheduler import Scheduler

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
    # --- Paths ---
    BASE_DIR = Path(__file__).resolve().parent
    schedulerPath = BASE_DIR / "scheduler.py"

    # --- Hilo del Scheduler ---
    schMain = Scheduler()
    threadScheduler = threading.Thread(target = schMain.start, daemon=True)
    threadScheduler.start()

    # --- Server de Flask ---
    app.run(host = "127.0.0.1", port = 5000)