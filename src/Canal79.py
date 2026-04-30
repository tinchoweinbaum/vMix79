"""
Nueva arquitectura del programa: Ahora la clase principal va a ser la clase Canal79, un objeto de esta clase tiene y controla a todos los elementos
que entran en juego en la emisión del canal 79: vMix, OBS, Scheduler y app de Flask.

El main simplemente instancia a la clase, llama a Canal.start_all() (que inicia a todo lo necesario) y queda corriendo en el hilo del scheduler y de la app de Flask.
"""

import subprocess
import psutil
import time
import socket
import os
import webbrowser
import sys

from pathlib import Path
from vMixApiWrapper import VmixApi
from obsManager import Obs

class Canal79:
    def __init__(self):
        # --- Procesos y Scheduler ---
        self.vMix_process = None
        self.Obs_process = None

        self.flaskApp = None
        web_actions = { # Le paso un diccionario de punteros a funciones del objeto Canal79 a la app de flask, para no tener que pasarle TODO el objeto cuando quiera por ejemplo, reiniciar.
            "restart": self.restart,
        }

        self.scheduler = None

        # --- Paths ---
        self.vMixPath = None
        self.obsPath = None

        # --- Información ---
        self.running = False

    
    def isVmixRunning():
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'vMix64.exe':
                return True
        return False

    def Canal79(presetPath, appPath):
        """
        Abre el preset de Canal79, corre la app de flask y abre el Control de Emisión en el navegador.
        """
        VmixApi().openPreset(presetPath)
        
        if VmixApi().awaitPresetCargado(timeout = 100):
            subprocess.Popen([sys.executable, appPath]) # Corre la app de flask que aparte levanta el scheduler en otro hilo.
            time.sleep(0.5) # Espera medio segundo a que la app de flask levante el server
            webbrowser.open("http://localhost:5000")


    def runVmix(vMixPath):
        subprocess.Popen([vMixPath])

    def isObsRunning():
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'obs64.exe':
                return True
            
        return False

    def runObs(obs_executable_path, nombre_coleccion):

        obsPath = os.path.dirname(obs_executable_path)
        try:
            comando = [
                obs_executable_path,
                "--collection", nombre_coleccion,
                "--disable-shutdown-check", # Salta el mensaje de "Safe Mode" si se cerró mal
            ]
        
            subprocess.Popen(comando, cwd = obsPath)
            
        except FileNotFoundError:
            print("[ERROR]: No se encontró el ejecutable de OBS en la ruta especificada.")
        except Exception as e:
            print(f"[ERROR]: Ocurrió un error inesperado al abrir OBS: {e}")

    def vmix_tcp_ready(host="127.0.0.1", port=8099, timeout=1):
        """
        Intenta abrir una conexión al puerto TCP de vMix.
        Devuelve True si el server aceptó la conexión, False si no.
        """
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

    def wait_for_vmix_server(timeout_total=30):
        """
        Bucle que espera hasta que el servidor TCP responda.
        """
        print("[INFO]: Esperando a que vMix levante local server TCP...", end="", flush=True)
        inicio = time.time()
        while time.time() - inicio < timeout_total:
            if vmix_tcp_ready():
                print("\n[INFO]: Local server TCP levantado por vMix. Comenzando ejecución.")
                return True
            print(".", end="", flush=True)
            time.sleep(1)

        print("\n[ERROR]: Timeout. El server TCP de vMix no respondió.")
        return False

    def wait_for_obs(timeout=30):
        inicio = time.time()
        while time.time() - inicio < timeout:
            if isObsRunning():
                print("\n[INFO]: OBS detectado y corriendo.")
                return True
            time.sleep(1)
        
        print("\n[ERROR]: Timeout esperando a OBS.")
        return False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    schedulerPath = BASE_DIR / "scheduler.py"
    presetPath = BASE_DIR.parent / "resources" / "vmix_resources" / "presetC79.vmix"
    vMixPath = r"C:\Program Files (x86)\vMix\vMix64.exe" # Permitir canbiar esto en un archivo de configuraciones o en el panel de control
    obsPath = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
    obsLib = "escenasObs"

    if not isObsRunning():
        runObs(obsPath,obsLib)

    wait_for_obs()

    if not isVmixRunning(): 
        runVmix(vMixPath)

    wait_for_vmix_server()
    
    try:
        appPath = BASE_DIR.parent/ "ui" / "app.py"
        Canal79(presetPath, appPath)
    except Exception as e:
        print(f"Error al conectar con vMix: {e}")