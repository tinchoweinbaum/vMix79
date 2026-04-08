import subprocess
import psutil
import time
import socket
from pathlib import Path
from vMixApiWrapper import VmixApi
from obsManager import Obs

def isVmixRunning():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'vMix64.exe':
            return True
        
    return False

def Canal79(vMix, schedulerPath, presetPath):
    """
    Función que abre el preset y arranca el Canal 79. Necesita que vMix ya esté abierto.
    """
    VmixApi().openPreset(presetPath)
    
    if VmixApi().awaitPresetCargado(timeout = 100):
        print("Iniciando scheduler...")
        subprocess.run(["python",f"{schedulerPath}"])
    else:
        print(f"No se pudo abrir el preset en {presetPath}")

def runVmix(vMixPath):
    subprocess.Popen([vMixPath])

def isObsRunning():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'obs64.exe':
            return True
        
    return False

def runObs(obs_executable_path, nombre_coleccion):

    try:
        comando = [
            obs_executable_path,
            "--collection", nombre_coleccion,
            "--disable-shutdown-check", # Salta el mensaje de "Safe Mode" si se cerró mal
        ]
    
        subprocess.Popen(comando)
        
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

def wait_for_obs():
    intentos = 0

    while intentos < 5:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'obs64.exe':
                print("[INFO]: Obs corriendo...")
                return True
            intentos += 1
            time.sleep(2)
            
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
        vMix = VmixApi()
        Canal79(vMix, schedulerPath, presetPath)
    except Exception as e:
        print(f"Error al conectar con vMix: {e}")

