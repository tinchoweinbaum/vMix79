"Flask lo que hace es linkear funciones usando decoradores, con direcciones de la página web, entonces /app/reiniciar llama a la función decorada con @app.route('/reiniciar')"
import sys
import threading

from flask import Flask, render_template
from pathlib import Path
from pathlib import Path

# scheduler.py se importa dandole el path absoluto xq python es una pija.
from pathlib import Path

# agrega toda la carpeta src a los imports
raiz_del_proyecto = Path(__file__).resolve().parent.parent
carpeta_src = str(raiz_del_proyecto / "src")
if carpeta_src not in sys.path:
    sys.path.insert(0, carpeta_src)

from scheduler import Scheduler

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
    horaArranque = schMain.horaArranque
    app.run(host = "127.0.0.1", port = 5000, horaArranque = horaArranque) # Ver como hacer esto para que no tire la warning de 