"""Esta clase va a ser instanciada dentro de la clase Scheduler, la clase Scheduler tiene un atributo bloqueCamaras, y es a ese atributo que accede el manager para tener el bloque de camaras.
    En esta clase NO está la lógica para ver cuando cambio de cámaras, solo está la implementación física del cambio. Es decir, maneja procesos de ffmpeg y llama a la api de vMix para hacer swap.
    Los atributos Act/Prox de esta clase tienen que estar sincronizados con los del scheduler.
"""

from vMixApiWrapper import VmixApi
from scheduler import Scheduler
from utilities import Camara

import subprocess
import time

from enum import Enum

class InputsCamID(str, Enum):
    CAMARA_A = "123520d4-a22c-4e83-a5b7-a8291e7cb82c"
    CAMARA_B = "2a18a0fc-55d1-44d9-9f48-9071142ba548"

class CamarasManager():
    def __init__(self, scheduler: Scheduler, ffmpeg_path = "ffmpeg" , mtx_path = "mediamtx",):
        """Inicializa todos los parámetros de la clase y abre una instancia de MediaMTX para hacer de puente con ffmpeg y vMix."""

        self.ffmpeg_path = ffmpeg_path # Los valores default del init asumen que los .exe de ffmpeg y mediamtx están en el path.
        self.mtx_path = mtx_path
        self.scheduler = scheduler # Le paso la referencia en memoria del obj. scheduler para que se pueda llamar a _actualizaCamaras()
        self.vMix = VmixApi()
        
        self.ffmpegCam_a = None
        self.ffmpegCam_b = None

        self.ffmpegAct =  None

        try:
            self.mtx = subprocess.Popen(mtx_path)
            # self.mtx = subprocess.Popen(mtx_path, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(2) # Damos tiempo a que MediaMTX abra el puerto 8554
        except Exception as e:
            print(f"[ERROR]: Error al ejecutar MediaMTX: {e}")
            raise

        #func. para dale a ffmpegCamaraProx un ffmpeg con la primer camara del playlist.

    def _llama_ffmpeg(self, cam_url, via):
        """Devuelve el proceso ffmpeg con la conexión de la cámara abierta. Método privado."""
        comando = [
            self.ffmpeg_path, 
            "-rtsp_transport", "tcp", 
            "-i", cam_url, 
            "-c", "copy", 
            "-f", "rtsp", 
            f"rtsp://127.0.0.1:8554/{via}"
        ]
        # Usamos creationflags para no llenar de ventanas la PC
        # return subprocess.Popen(
        #     comando, 
        #     stdout=subprocess.DEVNULL, 
        #     stderr=subprocess.DEVNULL,
        #     creationflags=subprocess.CREATE_NO_WINDOW
        # )

        # Este llamado crea una terminal con cada vez que abre una conexión a una cámara.
        return subprocess.Popen(
            comando, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    
    def iniciaCamaras(self):
        """Establece conexión con la primera cámara. Abre una instancia de ffmpeg."""
        primera_camara: Camara = self.scheduler.bloqueCamaras[0]
        self.ffmpegCam_a = self._llama_ffmpeg(primera_camara.dir_conexion, 'camara_a') # Creo el ffmpeg de la primera cámara y actualizo estado.
        self.ffmpegAct = self.ffmpegCam_a