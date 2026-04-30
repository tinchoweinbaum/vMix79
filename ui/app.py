"Flask lo que hace es linkear funciones usando decoradores, con direcciones de la página web, entonces /app/reiniciar llama a la función decorada con @app.route('/reiniciar')"
import sys
import threading

from flask import Flask, render_template
from pathlib import Path

# agrega toda la carpeta src a los imports
raiz_del_proyecto = Path(__file__).resolve().parent.parent
carpeta_src = str(raiz_del_proyecto / "src")
if carpeta_src not in sys.path:
    sys.path.insert(0, carpeta_src)

from scheduler import Scheduler

app = Flask(__name__)
schMain = Scheduler() # Instancio objeto de clase Scheduler. Variable global para no tener que pasarle a todas las funciones el objeto scheduler
 
@app.route('/')
def index():
    return render_template('index.html', horaArranque = horaArranque)

@app.route('/restart')
def restart():
    schMain.restart()


if __name__ == "__main__":
    # --- Paths ---
    BASE_DIR = Path(__file__).resolve().parent
    schedulerPath = BASE_DIR / "scheduler.py"

    # --- Hilo del Scheduler ---
    threadScheduler = threading.Thread(target = schMain.start, daemon=True)
    threadScheduler.start()

    # --- Server de Flask ---
    horaArranque = schMain.horaArranque
    app.run(host = "127.0.0.1", port = 5000) # Ver como hacer esto para que no tire la warning de "TAS LOCO COMO VAS A USAR ESTO FUERA DE PRODUCCIOn!!!"