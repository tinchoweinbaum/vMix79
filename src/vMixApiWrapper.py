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
from xml.dom import minidom

def print_xml_bonito(root):
    if root is not None:
        # Convertimos a string
        raw_str = ET.tostring(root, encoding='utf-8')
        # Usamos minidom para darle formato
        pretty_str = minidom.parseString(raw_str).toprettyxml(indent="  ")
        print(pretty_str)

class VmixApi:
    def __init__(self, host="127.0.0.1", port=8099, timeout=None):
        # Nota: El puerto TCP por defecto de vMix es 8099, no 8088.
        # Si pasas 8088 (HTTP) por error, intentaremos forzar 8099 o usar el dado si es explícito.
        if port != 8099: 
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
            # print("hola llame a conncect tcp")
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
            print(f"[ERROR]: No se pudo conectar a vMix por TCP ({self.host}:{self.port}): {e}")

    def _send_raw(self, text):
        """Envío crudo de strings a la api de vMix con el formato especifico que se pide en la documentación: terminadas en CRLF."""
        if self._sock and self._running:
            try:
                msg = text + "\r\n" # Arma el string con formato correcto
                # print(f"ENVIANDO: {msg.strip()}") # Ver exactamente qué sale
                self._sock.sendall(msg.encode('utf-8')) # Lo envía
            except socket.error:
                self._running = False

    def _tcp_listener(self):
        """Loop de lectura en hilo secundario."""
        while self._running:
            # print("hola")
            try:
                data = self._sock.recv(8192)
                if not data:
                    break
                # print("Buffer actual: " + str(self._buffer))
                self._buffer += data.decode('utf-8', errors='ignore')
                
                while '\r\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\r\n', 1)
                    # print(f"VMIX RESPONDE: {line}")
                    self._parse_tcp_line(line)
            except:
                self._running = False
                break

    def _parse_tcp_line(self, line):
        # Manejo de Tally (Cambios de Live/Preview)
        if line.startswith("TALLY OK"):
            tally_str = line.split(" ")[2]
            with self._lock:
                for i, char in enumerate(tally_str):
                    if char == '1': self.live = i + 1
                    elif char == '2': self.preview = i + 1
            return

        # Manejo de XML (Estado Completo)
        if "<vmix>" in line:
            try:
                start, end = line.find("<vmix>"), line.find("</vmix>") + 7
                root = ET.fromstring(line[start:end])
                with self._lock:
                    self._xml_root = root
                self.__setState(root)
            except:
                print("No se pudo parsear el XML de vMix.")
                pass

    def cut(self):
        self.__makeRequest("Cut")
    
    def fade(self,duration = 500):
        self.__makeRequest("Fade",duration)

    def adelantaVideo(self,inputNum,segundos):
        ms = segundos * 1000
        self.__makeRequest("SetPosition", extraParams={"Input": inputNum, "Value": f"+{ms}"})

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

        self.__makeRequest("CutDirect", extraParams={"Input": inputNum})

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
        self.__makeRequest(function,extraParams = {"Input": listNum}) # No pido árbol XML acá porque no es necesario para borrar.

    def listAddInput(self,listNum,path):
        function = "ListAdd"
        self.__makeRequest(function,extraParams = {"Input": listNum, "Value": path})
        self._send_raw("XML")

    def getInputPath_num(self, inputNum):
            """
            Retorna el path del archivo cargado en un input específico.
            Versión optimizada para TCP y Multithreading.
            """
            xmlAct = self.__getState()  # __getState usa threadlock.

            if xmlAct is None:
                print("Error: El XML aún no ha sido cargado.")
                return None
            
            input_node = xmlAct.find(f".//input[@number='{inputNum}']")
            
            if input_node is not None:
                # CASO 1: Video / Image / Audio file (Nodo <file>)
                file_node = input_node.find("file")
                if file_node is not None and file_node.text:
                    return file_node.text

                # CASO 2: List (Nodo <list>)
                list_node = input_node.find("list")
                if list_node is not None:
                    items = list_node.findall("item")
                    if len(items) == 0:
                        return None # Lista vacía
                    if len(items) > 0:
                        print(f"ERROR: La lista {inputNum} tiene mas de 1 item")
                    else:
                        return items[0].text
            
                print(f"El input {inputNum} no es file ni list.")
                return None # el tipo de input no es file ni list. (no debería pasar nunca tampoco)
            

            print(f"No se encontró el input {inputNum}. Probablemente no este cargado el preset correcto de vMix.")
            return None
    
    def setAudio_on(self,inputNum):
        self.__makeRequest("AudioOn", extraParams = {"Input": inputNum})

    def setAudio_off(self,inputNum):
        self.__makeRequest("AudioOff", extraParams = {"Input": inputNum})

    def setOutput_number(self,inputNum):
        function = "ActiveInput"
        self.__makeRequest(function,extraParams = {"Input": inputNum})

    def setOverlay_on(self, inputNum, overNum):
            # OverlayInputXIn fuerza la entrada del overlay independientemente de si estaba puesto o no
            function = f"OverlayInput{overNum}In" 
            self.__makeRequest(function, extraParams = {"Input": inputNum})

    def setOverlay_off(self, overNum):
        # OverlayInputXOut fuerza la salida, no importa qué input tenga
        function = f"OverlayInput{overNum}Out"
        self.__makeRequest(function)


    def __makeRequest(self, function, extraParams=None, duration=0):
        cmd = f"FUNCTION {function}"
        
        params_list = [] # lista de parametros para el call.
        
        if duration > 0:
            params_list.append(f"Duration={duration}")
            
        if extraParams:
            for k, v in extraParams.items():
                params_list.append(f"{k}={v}")
        
        # Concateno parámetros con & para TCP, espacios no.
        if params_list:
            query_string = "&".join(params_list) # La versión de TCP que usa la API de vMix no acepta espacios para concatenar. cosas de vMix 29.
            cmd = f"{cmd} {query_string}"
            
        try:
            self._send_raw(cmd)
            return "TCP_SENT"
        except Exception as e:
            print(f"ERROR TCP: No se pudo enviar el comando {function}, {e}")
    
    def __getState(self):
        with self._lock:
            return self._xml_root # Le pide al daemon TCP que lockee el árbol en su estado actual para no devolverlo mientras se está modificando.
    
    def __setState(self, root):
        """Parsea el XML a diccionarios locales y hace el swap atómico."""
        temp_inputs = {}
        temp_overlays = {}
        
        # Parsear Inputs
        ins_node = root.find("inputs")
        if ins_node is not None:
            for inp in ins_node.findall("input"):
                key = inp.attrib.get("key")
                temp_inputs[key] = {
                    "number": int(inp.attrib.get("number", 0)),
                    "type": inp.attrib.get("type"),
                    "title": inp.attrib.get("title")
                }

        # Parsear Overlays
        ov_node = root.find("overlays")
        if ov_node is not None:
            for ov in ov_node.findall("overlay"):
                num = int(ov.attrib.get("number"))
                val = ov.text
                temp_overlays[num] = int(val) if val and val != "0" else None

        # Update de punteros (Thread Safe)
        with self._lock:
            self.inputs = temp_inputs
            self.overlays = temp_overlays
            
            st_node = root.find("streaming")
            if st_node is not None:
                self.streaming = st_node.text == "True"

            act, pre = root.find("active"), root.find("preview")
            if act is not None: self.live = int(act.text)
            if pre is not None: self.preview = int(pre.text)

    def _isInputLive(self, inputNum):
        """
        Recibe un numero de input y devuelve True si está al aire
        """

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
    
    def getLength(self, inputNum):
        """
        Usa el estado XML interno para obtener la duración de un input.
        """
        root = self.__getState()
        
        if root is None:
            return None

        try:
            input_tag = root.find(f".//input[@number='{inputNum}']")
            
            if input_tag is not None:
                duracion_str = input_tag.get('duration')
                
                if duracion_str:
                    return int(duracion_str)
                    
        except Exception as e:
            print(f"[ERROR]: Falló el parseo de duración para el input {inputNum}: {e}")
        
        return None
    
    def restartInput_number(self, inputNum):
        self.__makeRequest("Restart", {"Input": inputNum})

    def playInput_number(self, inputNum):
        self.__makeRequest("Play", {"Input": inputNum})

    def pauseInput_number(self,inputNum):
        self.__makeRequest("Pause", {"Input": inputNum})

    def openPreset(self, presetPath):
        self.__makeRequest("OpenPreset", {"Value": presetPath})

    def awaitPresetCargado(self, timeout = 200):
        """
        Función "Pseudoasíncrona". Devuelve True una vez cargó el preset o False si no lo pudo cargar después del timeout
        """
        print("Esperando a que vMix abra el preset...")
        # Primero damos un margen para que vMix empiece la carga
        time.sleep(2) 
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            self._send_raw("XML")
            time.sleep(0.5)
            
            with self._lock:
                if self.inputs and self._xml_root is not None:
                    print("\n[OK] Preset cargado y funcional.")
                    return True
            
            print(".", end="", flush=True)
            time.sleep(1)
            
        print("\n[ERROR] Timeout esperando el preset.")
        return False

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
    # vMix.listAddInput(1,r"D:\MEME.bmp")
    vMix.openPreset(r"C:\Users\marti\OneDrive\Desktop\proyectosXD\vMix79\vMix79\resources\vmix_resources\presetC79.vmix")
    