"""
Archivo principal del proyecto, se encarga de organizar la transmisión y de mandar al aire el contenido que corresponda a la hora que corresponda.
Usa las clases de excelParser y vMixApiWrapper (TCP) para hacer esto.
Es totalmente dependiente de que el preset de vMix sea el correcto. Los Enums están armados para ese preset y sólo ese preset.
"""

import time
import excelParser as excParser #Parser del excel
from enum import IntEnum, Enum
from datetime import datetime, time as dt, timedelta
from typing import List
from utilities import Contenido # Clase de contenido (fila del excel)
from vMixApiWrapper import VmixApi # Clase wrapper de la webApi de vMix
from pathlib import Path
import pause
import random

# TO DO: Placa transparente (camara desnuda) cuando no hay placa.
# TO DO: Interfaz gráfica en navegador con JavaScript para manejar modo manual/automático.
# TO DO: A veces cuando se arranca en mitad de una tanda de anuncios no salen bien. Sale 2 veces el mismo o se saltea uno.
# TO DO: Cuando se arranca en mitad de un reporte local en vez de la cámara manda el mapa de fondo. ???
# TO DO: Cuando se arranca en mitad de un reporte local, hay que encontrar una manera prolija de poner cámara y música.

class TipoContenido(IntEnum):
    VIDEO = 1
    CAMARA = 2
    PLACA = 3
    MUSICA = 4
    IMAGENCAM = 5
    FOTOBMP = 6

class NumsInput(IntEnum):
    CAMARA_ACT = 1
    PLACA_A = 2
    MUSICA_A = 3
    VIDEO_A = 4
    MICRO_A = 5
    PLACA_B = 6
    MUSICA_B = 7
    VIDEO_B = 8
    MICRO_B = 9
    BLIP = 10

class OverlaySlots(IntEnum):
    SLOT_PLACA = 1

class Rutas(str, Enum):
    MUSICA = r"C:\SERVERLOC_RES\MusicaAire"


class Scheduler:
    def __init__(self,contenidos: List[Contenido] = None, vMix: VmixApi = None):
        self.contenidos = contenidos # Lista de objetos de la clase Contenido
        self.vMix = vMix # Objeto de la api de vMix
        self.indexEmision = 0 # El index de contenidos indica cuál es el próximo contenido a emitir. "Puntero"

        self.videoAct = None
        self.videoProx = None

        self.placaAct = None # Estos 3 atributos están para no depender de las respuestas de vMix que tardan en llegar.
        self.placaProx = None

        self.microAct = None
        self.microProx = None

        self.musicaAct = None
        self.musicaProx = None

        self.camaraLive = False

        self.running = False
        self.todo_precargado = False

    def _buscaIndex(self):
        """
        Deja indexEmision en el valor que apunte al contenido de la hora actual.
        """
        horaAct = datetime.now().time() 
        
        # Recorro la lista con enumerate xq devuelve dos valores: Index y valor.
        if horaAct >= self.contenidos[-1].hora:
            self.indexEmision = len(self.contenidos) - 1 
            return
        
        for i, cont in enumerate(self.contenidos):
            try:
                if  horaAct >= cont.hora and horaAct < self.contenidos[i + 1].hora:
                    self.indexEmision = i 
                    return
            except IndexError:
                    self.indexEmision = len(self.contenidos)
                    return
    
    def start(self,blipPath):
        self.running = True
        print("Scheduler iniciado")

        self.videoAct = None
        self.videoProx = None

        self.placaAct = None # Modelo act/prox para videos/placas/micros. Act = al aire. Prox = Por salir
        self.placaProx = None # xAct y xProx son números de input en vMix: VIDEO_A o VIDEO_B por ejemplo

        self.microAct = None
        self.microProx = None

        self.camaraLive = False

        self.__clearAll()

        self.vMix.listAddInput(NumsInput.BLIP,blipPath) # Carga BLIP.WAV

        self._buscaIndex() # Asigna valor correcto actual a indexEmision
        self._cargaProx() # Precarga los inputs prox para el primer tick

        self._goLive(self.contenidos[self.indexEmision]) # Manda al aire el contenido correspondiente a la hora de ejecución.
        self.indexEmision += 1

        while self.running:
            self._tick()
            time.sleep(0.2)
        
    
    def stop(self):
        self.running = False

    def __restart(self):
        print("Se transmitió todo el playlist de hoy. Reiniciando...")
        
        ahora = datetime.now()
        manana = datetime.combine(ahora.date() + timedelta(days=1), dt(0, 0, 0))
        
        pause.until(manana) # Espera hasta las 00:00:01

        # *Parsea excel nuevo cambiando la lista de contenidos*

        self.indexEmision = 0
        self._cargaProx() # Maneja correctamente los atributos de prox y act


    def _tick(self):
        """
        _tick es el cerebro del programa, cada medio segundo checkea si hay que mandar un contenido nuevo al aire y lo manda
        si hay que hacerlo, depende totalmente de que la lógica de cargar prox sea totalmente correcta y NUNCA falle.
        """

        if self.indexEmision >= len(self.contenidos): # Si recorrió todos los contenidos del día.
            self.__restart()
            return
        
        contAct = self.contenidos[self.indexEmision] # Objeto del contenido actual
        horaAct = datetime.now().time()

        if horaAct >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado.
            self.indexEmision += 1
            self._goLive(contAct)
    
    def _precargaVideo(self,cont):
        vMix = self.vMix
        # print("Llamo precarga video.")
        if self.videoProx is not None: # Si no hace falta precargar:
            print("[ERROR]: Error de precarga de video. (pre)")
            print(cont.path)
            return
        
        if self.videoAct == NumsInput.VIDEO_A: # Si estaba A al aire, B es prox
            inputLibre = NumsInput.VIDEO_B
        else:
            inputLibre = NumsInput.VIDEO_A # Si estaba B al aire (o ninguno), prox es A
        
        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, cont.path)

        self.videoProx = inputLibre

    def _precargaPlaca(self,cont):
        vMix = self.vMix
        # print("Llamo precarga placa.")
        if self.placaProx is not None:
            print("[ERROR]: Mala inicializacion de placa.")
            return

        if self.placaAct == NumsInput.PLACA_A:
            inputLibre = NumsInput.PLACA_B
        else:
            inputLibre = NumsInput.PLACA_A

        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, cont.path)

        self.placaProx = inputLibre

    def _precargaMicro(self, cont):
        vMix = self.vMix
        # print("Llamo precarga micro.")
        if self.microProx is not None:
            return

        if self.microAct == NumsInput.MICRO_A:
            inputLibre = NumsInput.MICRO_B
        else:
            inputLibre = NumsInput.MICRO_A

        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, cont.path)

        self.microProx = inputLibre

    def _precargaMusica(self,path):
        vMix = self.vMix
        if self.musicaProx is not None:
            print("[ERROR]: Error de precarga de musica. (pre)")
            return

        if self.musicaAct == NumsInput.MUSICA_A:
            inputLibre = NumsInput.MUSICA_B
        else:
            inputLibre = NumsInput.MUSICA_A

        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, path) # Al elegirse un archivo de una carpeta al azar, siempre existe el path.

        self.musicaProx = inputLibre
    
    def __randomMusica(self):
        """
        Elige un archivo al azar de la carpeta de música
        """
        musicaRuta = Path(Rutas.MUSICA) 
        
        if not musicaRuta.exists():
            print(f"[ERROR]: La ruta {Rutas.MUSICA} no existe.")
            return None
        musicas = [item for item in musicaRuta.iterdir() if item.is_file()]
        
        if not musicas:
            print("[ERROR]: No hay archivos en la carpeta de música.")
            return None

        return str(random.choice(musicas)) 
    
    def _stopMusica(self):
        """
        Clean slate para cuando se llame a goLiveMusica.
        De esta manera se puede usar musicaAct == None como forma de checkear si está sonando música actualmente.
        """
        print("llamo stop musica")
        print(f"MUSICA PROX: {self.musicaProx}")
        print(f"MUSICA ACT: {self.musicaAct}")
        vMix = self.vMix

        if self.musicaAct is not None: # Si estaba sonando música.
            vMix.pauseInput_number(self.musicaAct)
            vMix.listClear(self.musicaAct)
        self.musicaAct = None

        if self.musicaProx is not None:
            vMix.listClear(self.musicaProx)
        self.musicaProx = None



    def _cargaProx(self):
        """
        Busca en la lista de contenidos el PRÓXIMO de cada tipo para precargar.
        """
        # Banderas locales para saber si ya encontramos lo que buscábamos en este tick
        buscando_video = self.videoProx is None
        buscando_placa = self.placaProx is None
        buscando_micro = self.microProx is None
        buscando_musica = self.musicaProx is None

        for cont in self.contenidos[self.indexEmision:]:
            if not buscando_video and not buscando_placa and not buscando_micro and not buscando_musica:
                return
            
            if not cont.path_valido() and cont.path not in ["CAMARA", "MUSICA"]:
                # print(cont.nombre + " No tiene un path valido.")
                continue

            match cont.tipo:
                case TipoContenido.VIDEO:
                    if buscando_video:
                        self._precargaVideo(cont)
                        buscando_video = False # Actualizo las flags cuando encuentro
                
                case TipoContenido.PLACA:
                    if buscando_placa:
                        self._precargaPlaca(cont)
                        buscando_placa = False
                
                case TipoContenido.FOTOBMP:
                    if buscando_micro:
                        self._precargaMicro(cont)
                        buscando_micro = False

                case TipoContenido.MUSICA:
                    if buscando_musica:
                        musicaPath = self.__randomMusica()
                        if musicaPath is not None:
                            self._precargaMusica(musicaPath) # _precargaMusica a diferencia de las otras funciones espera un path, no un cont
                            buscando_musica = False
                        else:
                            print("No se pudo elegir una musica aleatoria.")
                
                case TipoContenido.CAMARA:
                    pass
      
                case _: # Default
                    print(f"[ERROR]: Tipo de contenido desconocido: {cont.tipo}")
                    pass

    def playBlip(self):
        vMix = self.vMix

        vMix.setAudio_on(NumsInput.BLIP) # Algorítimicamente es lo mismo preguntar si está apagado el sonido que prenderlo todas las veces
        vMix.playInput_number(NumsInput.BLIP)

    def _goLive(self,contAct):
        """
        Este método tiene la lógica para mandar el tipo de contenido que corresponda al aire.
        """
        print("Hora actual: " + str(datetime.now().time()))
        if contAct == None:
            print("[ERROR]: Contenido inexistente")

        if not contAct.path_valido() and contAct.path not in ["CAMARA", "MUSICA"]:
            print("[ERROR]: No se encontró " + contAct.path + ", la imagen va a quedar congelada.")
            return

        tipo = contAct.tipo
        match tipo:
            case TipoContenido.VIDEO:
                if contAct.nombre in ["mapas"]: # Si se necesita que otro video tenga música, se agrega a la lista.
                    self._goLiveVideo(musica = True)
                else:
                    self._goLiveVideo()
            case TipoContenido.CAMARA:
                self.camaraLive = True
                self.vMix.cutDirect_number(1) # PLACEHOLDER
            case TipoContenido.PLACA:
                self._goLivePlaca()
            case TipoContenido.MUSICA:
                self._goLiveMusica()
            case TipoContenido.IMAGENCAM:
                self.camaraLive = True
                self.vMix.cutDirect_number(1) # PLACEHOLDER TAMBIEN
            case TipoContenido.FOTOBMP:
                self._goLiveMicro()
            case _:
                print(f"[ERROR]: Tipo de contenido desconocido: {tipo}")

        self._cargaProx() # Después de mandar al aire precarga el prox.

    def _goLiveMusica(self):
        vMix = self.vMix
        if self.musicaProx is None:
            print("[ERROR]: Error de precarga de música. (post)")
            return

        if self.musicaAct is not None:
            vMix.setAudio_off(self.musicaAct)
            vMix.listClear(self.musicaAct) # Apago y cleareo música anterior

        vMix.setAudio_on(self.musicaProx)
        vMix.restartInput_number(self.musicaProx)
        time.sleep(0.05)
        vMix.playInput_number(self.musicaProx)

        self.musicaAct = self.musicaProx
        self.musicaProx = None


    def _goLiveVideo(self, musica = False):
        # Toggle de inputs de video.
        vMix = self.vMix
        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)
        
        if not musica:
            self._stopMusica()

        if self.videoProx is None:
            print("[ERROR]: Error de precarga de video. (post)")
            return

        vMix.setOutput_number(self.videoProx) # Manda al aire
        vMix.restartInput_number(self.videoProx)
        time.sleep(0.05) # Reinicia, espera y manda play
        vMix.playInput_number(self.videoProx)

        self.camaraLive = False # Ya no sale al aire cámara.

        if self.videoAct is not None:
            vMix.listClear(self.videoAct)

        self.videoAct = self.videoProx
        self.videoProx = None

    def _goLivePlaca(self):
        # Toggle de inputs de placa.
        vMix = self.vMix

        if self.placaProx is None:
            print("[ERROR]: Error de precarga de placa.")
            return
        
        if not self.camaraLive:
            vMix.cutDirect_key(NumsInput.CAMARA_ACT) # Si no habia una camara de fondo la pone.
            self.camaraLive = True

        if self.musicaAct is None: # SOLUCION ATADA CON ALAMBRE!!!!! REHACER CON LA CAMARA
            self._goLiveMusica()

        vMix.setOverlay_on(self.placaProx, OverlaySlots.SLOT_PLACA)
        self.playBlip()

        if self.placaAct is not None:
            vMix.listClear(self.placaAct)

        self.placaAct = self.placaProx
        self.placaProx = None


    def _goLiveMicro(self):
        # Toggle de inputs de micro (.bmp).
        vMix = self.vMix
        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        if self.microProx is None:
            print("[ERROR]: Error de precarga de micro.")
            return

        vMix.setOutput_number(self.microProx) # Swapeo

        self.camaraLive = False # Ya no sale al aire cámara

        if self.microAct is not None:
            vMix.listClear(self.microAct) # Cleareo anterior

        self.microAct = self.microProx
        self.microProx = None

    def __clearAll(self):
        vMix = self.vMix

        vMix.listClear(NumsInput.MICRO_A)
        vMix.listClear(NumsInput.MICRO_B)

        vMix.listClear(NumsInput.PLACA_A)
        vMix.listClear(NumsInput.PLACA_B)

        vMix.listClear(NumsInput.VIDEO_A)
        vMix.listClear(NumsInput.VIDEO_B)

        vMix.listClear(NumsInput.MUSICA_A)
        vMix.listClear(NumsInput.MUSICA_B)    

        vMix.listClear(NumsInput.BLIP)

        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    blipPath = BASE_DIR.parent / "resources" / "BLIP.WAV"
    pathExcel = BASE_DIR / "playlist.xlsx"

    if pathExcel.exists:
        programacion = excParser.crea_lista(pathExcel) # Lista de objetos de clase Contenido con la programacion del dia
        vMix = VmixApi() # Objeto API de vMix
        schMain = Scheduler(programacion,vMix)
        schMain.start(blipPath)
    else:
        print("[ERROR]: No se encontró el playlist.xlsx")
        time.sleep(5)