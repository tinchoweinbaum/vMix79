"""
Este módulo es un wrapper para la api de vmix, así puedo importar
este módulo en otros archivos y puedo hacer llamados a la API de forma abstracta.

Las duraciones de las requests van en ms.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime

class VmixApi:
    def __init__(self, host="127.0.0.1", port=8088, timeout=15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.api_url = f"http://{host}:{port}/api/"

        #Estos atributos se usan para representar el estado actual del vMix
        self.live = None
        self.preview = None
        self.inputs = {}
        self.overlays = {}
        self.audio = {}
        self.streaming = False

    def cut(self):
        self.__makeRequest("Cut")
    
    def fade(self,duration = 500):
        self.__makeRequest("Fade",duration)

    def cutDirect_key(self,inputKey):
        """
        Lleva un input identificado por key directamente al aire por cut.
        Si se llegase a necesitar se puede hacer una función que lo haga por cualquier otro método
        """

        input = self.inputs.get(inputKey) #Checkea que exista el input
        if not input:
            print(f"No existe el input {inputKey}")
            return
        
        inputNum = input["number"]

        self.__makeRequest("Cut", extraParams={"Input": inputNum})

    def cutDirect_number(self,inputNum):
        """
        Lleva un input identificado por número directamente al aire por cut.
        Si se llegase a necesitar se puede hacer una función que lo haga por cualquier otro método
        """
        inputKey = None

        for key, data in self.inputs.items(): #Itera por el diccionario de keys (inputs) buscando que input tiene el numero pedido
            if data["number"] == inputNum:
                inputKey = key
                break

        if not inputKey:
            print(f"No existe el input con número {inputNum}")
            return

        self.cutDirect_key(inputKey)

    def __makeRequest(self,function,duration = 0,extraParams = None): #TODOS LLAMAN A ESTA FUNCIÓN PARA EFECTUAR LA REQUEST.
        params = { #Creo un diccionario para hacer la request.
            "Function": function,
            "Duration": duration
        }

        if extraParams is not None: #Parametros extra para otras funciones que requieran mas parametros
            params.update(extraParams)

        try: 
            query = requests.get(self.api_url,params = params,timeout = 15.0)
            query.raise_for_status()
            self._updateState() #Updatea el estado del objeto con el vMix en vivo
            return query.text #devuelve el xml de vMix
        
        except requests.exceptions.HTTPError as e:
            print(f"Error HTTP al comunicarse con la API de vMix: {e}")
            return None

        except requests.RequestException as e:
            print(f"Error de conexion o timeout con la API de vMix: {e}")
            return None
    
    def __getState(self):
        try:
            query = requests.get(self.api_url) #pide el xml como texto y lo convierte a arbol para __setState
            query.raise_for_status()

            xmlArbol = ET.fromstring(query.text) #convierte
            return xmlArbol

        except requests.RequestException as e:
            print(f"Error de conexion o timeout con la API de vMix: {e}")
            return None

        except ET.ParseError as e:
            print(f"Error al parsear XML de vMix: {e}")
            return None
    
    def __setState(self,arbolXml):
        if arbolXml is None:
            return
        
        # Resetea el estado de vMix
        self.inputs.clear()
        self.overlays.clear()
        self.live = None
        self.preview = None
        self.streaming = False

        #Actualización de live/preview:
        active = arbolXml.find("active") #Se fija que inputs están de preview/live y actualiza
        preview = arbolXml.find("preview")

        if active is not None:
            self.live = int(active.text)

        if preview is not None:
            self.preview = int(preview.text)

        #Actualización de inputs:

        inputs = arbolXml.find("inputs")
        
        if inputs is not None: #Itera por todos los inputs del preset y actualiza su estado
            for input in inputs.findall("input"):
                key = input.attrib.get("key")
                self.inputs[key] = {
                    "number": int(input.attrib.get("number",0)),
                    "type": input.attrib.get("type"),
                    "state": input.attrib.get("state"),
                    "title": input.attrib.get("title")
                }

        #Actualización de overlays:

        overlays = arbolXml.find("overlays")

        if overlays is not None:
            for overlay in overlays:
                num = int(overlay.attrib.get("number", 0)) #Itera por los overlays tomando su numero y su input

                if overlay.text is not None:
                    self.overlays[num] = int(overlay.text)
                else:
                    self.overlays[num] = None

        #Actualizacion de streaming:

        streaming = arbolXml.find("streaming")
        self.streaming = True if streaming.text == "True" else False

    def _updateState(self):
        estadoAct = self.__getState()
        self.__setState(estadoAct)

    def print_state(self):
        print("===== ESTADO ACTUAL DE vMix =====")
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Live input: {self.live}")
        print(f"Preview input: {self.preview}")
        print(f"Streaming: {self.streaming}")

        print("\n--- Inputs ---")
        if not self.inputs:
            print("(vacío)")
        else:
            for key, data in self.inputs.items():
                print(f"Key: {key}")
                for k, v in data.items():
                    print(f"  {k}: {v}")

        print("\n--- Overlays ---")
        if not self.overlays:
            print("(vacío)")
        else:
            for num, input_num in self.overlays.items():
                print(f"Overlay {num}: input {input_num}")

        print("\n--- Audio ---")
        if not self.audio:
            print("(vacío)")
        else:
            for k, v in self.audio.items():
                print(f"{k}: {v}")

        print("================================\n")

if __name__ == "__main__":
    vMix = VmixApi()
    vMix._updateState()