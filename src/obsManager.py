"""Este archivo tiene la clase Obs que va a tener la conexión con OBS hecha para que scheduler.py pueda cargar/descargar cámaras en los outputs NDI A/B para vMix"""

from obswebsocket import obsws, requests

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
            res = self.client.call(requests.CreateInput(
                sceneName = scene,
                inputName = inputName,
                inputKind ="ffmpeg_source",
                inputSettings = {
                    "is_local_file": False,
                    "input": rtsp_url,
                    "looping": False,
                    "hw_decode": True,
                    "rtsp_transport": "tcp", # RTSP over TCP
                    "reconnect_delay": 2,
                    "buffering_mb": 4,
                    "close_when_inactive": False,
                    "restart_on_activate": False,
                    "active": True,
                    "clear_on_media_end": False,
                    "ffmpeg_options": "rtsp_transport=tcp allowed_media_types=video"# Traer SOLO video, sin audio y RTSP over TCP
                },
                sceneItemEnabled=True
            ))
            # Extraigo ID de la nueva cámara para estirarla.
            try:
                nuevo_id = res.datain.get('sceneItemId')
                self.stretchMedia(scene, nuevo_id)
            except Exception as e:
                print(f"[ERROR]: Error al extraer el ID de la cámara {inputName} o al estirar la imagen de la misma: {e}")
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

    def stretchMedia(self, scene, item_id):
            self.client.call(requests.SetSceneItemTransform(
                sceneName=scene,
                sceneItemId=item_id, # El cliente a veces mapea el nombre al ID internamente
                sceneItemTransform={
                    'boundsType': 'OBS_BOUNDS_STRETCH',
                    'boundsWidth': 1920.0,
                    'boundsHeight': 1080.0
                }
            ))

    def print_all_ids(self, scene_name):
            try:
                res = self.client.call(requests.GetSceneItemList(sceneName=scene_name))
                
                # 'datain' es el diccionario crudo con la respuesta de OBS
                # Adentro tiene la key 'sceneItems' que es la lista de inputs
                items = res.datain.get('sceneItems', [])
                
                print(f"\n--- IDs de inputs en la escena: {scene_name} ---")
                for item in items:
                    nombre = item['sourceName']
                    id_num = item['sceneItemId']
                    print(f"Input: {nombre} | ID: {id_num}")
                print("-------------------------------------------\n")
                
            except Exception as e:
                print(f"[ERROR]: Error al leer datain: {e}")

if __name__ == "__main__":
    testObs = Obs()
    testObs.print_all_ids("Scene")
    testObs.stretchMedia("Scene", 8)