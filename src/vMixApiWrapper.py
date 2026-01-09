"""
Este módulo es un wrapper para la api de vmix, así puedo importar
este módulo en otros archivos y puedo hacer llamados a la API de forma abstracta.

Las duraciones de las requests van en ms.

Rehacer todo esto usando protocolo TCP en vez de HTTPS, es bocha más rápido

"""

import socket
import threading
import time
import xml.etree.ElementTree as ET

class VmixApi:
    def __init__(self, host="127.0.0.1", port=8099, timeout=None):
        # Nota: El puerto TCP por defecto de vMix es 8099, no 8088.
        # Si pasas 8088 (HTTP) por error, intentaremos forzar 8099 o usar el dado si es explícito.
        if port != 8089: 
            print("La api de vMixTCP solo funciona en el puerto 8099. Se conectara por ese puerto y no por el especificado.")
            self.port = 8099
        else:
            self.port = port
            
        self.host = host
        self.timeout = timeout # Se mantiene por compatibilidad, aunque TCP usa socket timeout
        
        # --- Atributos de Estado (Idénticos al wrapper anterior) ---
        self.live = None
        self.preview = None
        self.inputs = {}
        self.overlays = {}
        self.audio = {}
        self.streaming = False
        
        # --- Variables Internas TCP ---
        self._sock = None # socket de conexion tcp
        self._running = False
        self._lock = threading.Lock() # Para evitar conflictos de lectura/escritura. Se asegura de que el buffer que se tiene guardado se mantenga en memoria.
        self._xml_root = None # Xml en memoria para acceso rápido.
        self._buffer = ""
        
        # Iniciar conexión inmediatamente
        self._connect_tcp()

    def _connect_tcp(self):
        """
        Metodo que se encarga de crear la conexion TCP de la api.
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Objeto de la clase socket, usando IPv4 y TCP (sock_stream)
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Desactiva optimizaciones de ancho de banda para reducir latencia
            self._sock.connect((self.host, self.port))
            self._running = True # Realiza la conexión misma a la api por TCP.
            
            # Listener TCP, la funcion va sin () porque NO se está llamando. Es un puntero a ella.
            self._thread = threading.Thread(target=self._tcp_listener, daemon=True) # Crea un objeto de la clase thread y lo arranca, target es un puntero a una función que se encarga del loop de lectura de la api.
            self._thread.start() # daemon = True lo marca como subproceso para el garbage collector de python, entonces si este script se detiene, también lo hace el daemon.
            
            # Suscripciones iniciales y petición de estado completo
            self._send_raw("SUBSCRIBE TALLY") # Pide a la api de vMix que pushee datos por el socket tcp cada vez que hay un cambio en el software.
            self._send_raw("SUBSCRIBE ACTS")
            self._send_raw("XML") # Pide el estado inicial completo
            
            # Pequeña espera para asegurar que el primer XML llegue y se pueblen los inputs
            # antes de que el usuario intente hacer algo.
            time.sleep(0.2)
            
        except Exception as e:
            print(f"ERROR CRÍTICO: No se pudo conectar a vMix por TCP ({self.host}:{self.port}): {e}")

    def _send_raw(self, text):
        """Envío crudo de strings a la api de vMix con el formato especifico que se pide en la documentación: terminadas en CRLF."""
        if self._sock and self._running:
            try:
                msg = text + "\r\n" # Arma el string con formato correcto
                self._sock.sendall(msg.encode('utf-8')) # Lo envía
            except socket.error:
                self._running = False

    def _tcp_listener(self):
        """Loop de lectura en hilo secundario."""
        while self._running:
            try:
                data = self._sock.recv(8192)
                if not data: break
                
                self._buffer += data.decode('utf-8', errors='ignore')
                
                while '\r\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\r\n', 1)
                    self._parse_tcp_line(line)
            except:
                self._running = False
                break

    def _parse_tcp_line(self, line):
        """Parsea líneas individuales del stream TCP."""
        parts = line.split(" ")
        
        with self._lock:
            # Procesar TALLY (Live/Preview)
            if parts[0] == "TALLY" and len(parts) > 2 and parts[1] == "OK":
                tally_str = parts[2]
                for i, char in enumerate(tally_str):
                    input_num = i + 1
                    if char == '1': self.live = input_num
                    elif char == '2': self.preview = input_num
            
            # Procesar XML (Estado completo)
            elif "XML" in line and "<vmix>" in line:
                try:
                    start = line.find("<vmix>")
                    end = line.find("</vmix>") + 7
                    if start != -1 and end != -1:
                        xml_raw = line[start:end]
                        self._xml_root = ET.fromstring(xml_raw)
                        self.__setState(self._xml_root)
                except:
                    print("No se pudo parsear el XML de vMix.")
                    pass

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


    def __makeRequest(self, function, duration=0, extraParams=None):
        """
        Envía rawtext a la api de vMix por TCP, que es la forma en que lo pide.
        """
        cmd = f"FUNCTION {function}"
        if duration > 0:
            cmd += f" Duration={duration}"
        
        if extraParams: # Si hay parámetros extras como numero de input, overlay, etc.
            for k, v in extraParams.items():
                cmd += f" {k}={v}"
        
        self._send_raw(cmd)
        return "TCP_SENT"
    
    def __getState(self):
        return self._xml_root # 
    
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