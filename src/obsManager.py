"""Este archivo tiene la clase Obs que va a tener la conexión con OBS hecha para que scheduler.py pueda cargar/descargar cámaras en los outputs NDI A/B para vMix"""

from obswebsocket import obsws, requests
import time

class Obs:
    def __init__(self, host = "127.0.0.1" , puerto = 4455, password = "masterkey"):
        self.host = host
        self.puerto = puerto
        self.password = password

        self.client = obsws(host, puerto, password) # Instancia la clase obsws
        try:
            self.client.connect() # Conecta con el objeto client a obs
            print(f"[INFO]: Conectado con OBS en {host}:{puerto}")
        except Exception as e:
            print(f"[ERROR]: No se pudo conectar al Web Socket de OBS: {e}")

    def add_rtsp(self, scene, inputName, rtsp_url):
        "Agrega una cámara RTSP en la escena indicada, NO comienza la conexión hasta no darle Cut al input de la cámara."
        try:
            self.client.call(requests.CreateInput(
                sceneName = scene,
                inputName = inputName,
                inputKind ="ffmpeg_source",
                inputSettings = {
                    "is_local_file": False,
                    "input": rtsp_url,
                    "looping": False,
                    "hw_decode": True, # Aceleración x hardware para usar GPU
                    "reconnect_delay": 2,
                    "buffering_mb": 1, # Buffer bajo para menor latencia en NDI
                    "close_when_inactive": False, # Las cámaras tienen que estar cargadas hasta que se borre el input
                    "restart_on_activate": False
                },
                sceneItemEnabled=True
            ))
        except Exception as e:
            print(f"[ERROR]: Error al agregar la cámara con url {rtsp_url} a OBS: {e}")

    def restart_input(self,inputName):
        self.client.call(requests.TriggerMediaInputAction(
        sourceName= inputName,
        mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART" 
    ))
        
    def remove_input(self, inputName):
        try:
            self.client.call(requests.RemoveInput(inputName=inputName))
        except Exception as e:
            print(f"[ERROR]: Error al eliminar el input {inputName}: {e}")

    def clearScene(self, scene):
        """Limpia todos los inputs de una escena específica."""
        try:
            response = self.client.call(requests.GetSceneItemList(sceneName=scene))
            scene_items = response.getSceneItems()

            for item in scene_items:
                name = item['sourceName']
                self.remove_input(name)
                
        except Exception as e:
            print(f"[ERROR]: Error al limpiar la escena {scene}: {e}")

if __name__ == "__main__":
    testObs = Obs()