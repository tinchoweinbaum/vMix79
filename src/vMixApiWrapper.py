"""
Este módulo es un wrapper para la api de vmix, así puedo importar
este módulo en otros archivos y puedo hacer llamados a la API de forma abstracta.

Las duraciones de las requests van en ms.
"""

import requests
import xml.etree.ElementTree as ET

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

    def listClear(self,listNum):
        function = "ListRemoveAll"
        self.__makeRequest(function,extraParams = {"Input": listNum})

    def listAddInput(self,listNum,path):
        function = "ListAdd"
        self.__makeRequest(function,extraParams = {"Input": listNum, "Value": path})

    def getInputPath_num(self, inputNum):
        self._updateState()
        xmlAct = self.__getState()  # root del XML (ElementTree)

        # Buscar el input por número
        for input_node in xmlAct.findall(".//input"):
            if input_node.get("number") == str(inputNum):

                input_type = input_node.get("type")

                # CASO 1: Video / Image / Audio file
                file_node = input_node.find("file")
                if file_node is not None and file_node.text:
                    return file_node.text

                # CASO 2: List con 1 solo item
                list_node = input_node.find("list")
                if list_node is not None:
                    items = list_node.findall("item")
                    if len(items) == 1:
                        return items[0].text
                    elif len(items) == 0:
                        return None
                    else:
                        # Esto en teoría NUNCA debería pasar
                        raise RuntimeError(
                            f"List input {inputNum} tiene más de un item"
                        )

                # CASO 3: Input sin path (Camera, GT, Color, etc)
                return None

        print(f"No se encontró el input {inputNum}, probablemente no este el preset correcto cargado.")
        return None

    def setOutput_number(self,inputNum):
        function = "ActiveInput"
        self.__makeRequest(function,extraParams = {"Input": inputNum})

    def setOverlay_on(self,inputNum,overNum):
        function = f"OverlayInput{overNum}"
        self.__makeRequest(function, extraParams = {"Input": inputNum, "Value": "On"})

    def setOverlay_off(self,overNum):
        function = f"OverlayInput{overNum}"
        self.__makeRequest(function, extraParams = {"Value": "Off"})


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
            print(f"Error HTTP al comunicarse con la API de vMix, probablemente no este vMix abierto: {e}")
            return None

        except requests.RequestException as e:
            print(f"Error de conexion o timeout con la API de vMix, probablemente no este vMix abierto: {e}")
            return None
    
    def __getState(self):
        try:
            query = requests.get(self.api_url) #pide el xml como texto (GET) y lo convierte a arbol
            query.raise_for_status()

            xmlArbol = ET.fromstring(query.text) #convierte
            return xmlArbol

        except requests.RequestException as e:
            print(f"Error de conexion o timeout con la API de vMix, probablemente no este vMix abierto: {e}")
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

    def _isInputLive(self, inputNum):
        """
        Recibe un numero de input y devuelve True si está al aire
        """

        self._updateState()
        estadoAct = self.__getState()

        inputAct = estadoAct.find("active")
        if inputAct is None or inputAct.text is None:
            return False

        return inputAct.text == str(inputNum)
    
    def _isOverlayLive(self,overlayNum):
        """
        Recibe un número de overlay y checkea si está activo.
        """        
        estado = self.__getState()
        overlay = estado.find(f".//overlay[@number='{overlayNum}']")
        if overlay is None:
            return False
        
        if overlay.text != "0":
            return True
        else:
            return False
        
    def _getOverlayInput(self,overlayNum):
        """
        Recibe un número de overlay y devuelve que input está saliendo por ese slot.
        La idea es llamarlo SÓLO cuando _isOverlayLive devolvió True
        """
        estado = self.__getState()
        overlay = estado.find(f".//overlay[@number='{overlayNum}']")

        if overlay is None: # Si no existe el numero de overlay
            return None
        
        if overlay.text is None: # Si no tiene ningun input el overlay.
            return None
        
        return int(overlay.text)
    
    def restartInput_number(self, inputNum):
        self.__makeRequest("Restart", {"Input": inputNum})

    def playInput_number(self, inputNum):
        self.__makeRequest("Play", {"Input": inputNum})


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