"""
Archivo principal del proyecto, se encarga de organizar la transmisión y de mandar al aire el contenido que corresponda a la hora que corresponda.
Usa las clases de excelParser y vMixApiWrapper (TCP) para hacer esto.
Es totalmente dependiente de que el preset de vMix sea el correcto. Los Enums están armados para ese preset y sólo ese preset.
"""

import time
import excelParser as excParser #Parser del excel
from enum import IntEnum
from datetime import datetime, time as dt, timedelta
from typing import List
from utilities import Contenido # Clase de contenido (fila del excel)
from vMixApiWrapper import VmixApi # Clase wrapper de la webApi de vMix
from pathlib import Path

# TO DO: Fallback a negro cuando no existe un video. Placa transparente (camara desnuda) cuando no hay placa.
# TO DO: Interfaz gráfica en navegador con JavaScript para manejar modo manual/automático.
# TO DO: otra cosa más que no me puedo acordar ahora
# TO DO: Terminar de implementar la hora de inicio. Cuando arranca a una hora que no sea la hora exacta de arranque de un contenido queda con cualquier cosa
        # Hasta que detecta que tiene q mandar un nuevo contenido al aire. Ahí funciona perfecto después.

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
    MUSICA_ACT = 3
    VIDEO_A = 4
    MICRO_A = 5
    PLACA_B = 6
    MUSICA_PROX = 7
    VIDEO_B = 8
    MICRO_B = 9
    BLIP = 10

class OverlaySlots(IntEnum):
    SLOT_PLACA = 1

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

        self.running = False
        self.todo_precargado = False

    def _buscaHora(self):
        horaAct = datetime.now().time() 
        
        # Recorro la lista con enumerate xq devuelve dos valores: Index y valor.
        for i, cont in enumerate(self.contenidos):
            if cont.hora >= horaAct:
                self.indexEmision = i
                return

        self.indexEmision = len(self.contenidos)

    def start(self,blipPath):
        self.running = True
        print("Scheduler iniciado")

        self.videoAct = None
        self.videoProx = None

        self.placaAct = None # Modelo act/prox para videos/placas/micros. Act = al aire. Prox = Por salir
        self.placaProx = None # xAct y xProx son números de input en vMix: VIDEO_A o VIDEO_B por ejemplo

        self.microAct = None
        self.microProx = None

        self.__clearAll()

        self._buscaHora() # Asigna valor correcto actual a indexEmision
        self._cargaProx() # Precarga los inputs prox para el primer tick

        self.vMix.listAddInput(NumsInput.BLIP,blipPath) # Carga BLIP.WAV

        while self.running:
            self._tick()
            time.sleep(0.2)
        
    
    def stop(self):
        self.running = False

    def _tick(self):
        """
        _tick es el cerebro del programa, cada medio segundo checkea si hay que mandar un contenido nuevo al aire y lo manda
        si hay que hacerlo, depende totalmente de que la lógica de cargar prox sea totalmente correcta y NUNCA falle.
        """

        if self.indexEmision >= len(self.contenidos): # Si recorrió todos los contenidos del día, stop.
            print("Se transmitió todo el playlist.")
            self.stop()
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
            print("Error de precarga de video. (pre)")
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
            print("Mala inicializacion de placa.")
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
        
    def _cargaProx(self):
        """
        Busca en la lista de contenidos el PRÓXIMO de cada tipo para precargar.
        """
        # Banderas locales para saber si ya encontramos lo que buscábamos en este tick
        buscando_video = self.videoProx is None
        buscando_placa = self.placaProx is None
        buscando_micro = self.microProx is None

        for cont in self.contenidos[self.indexEmision:]:
            if not buscando_video and not buscando_placa and not buscando_micro:
                return
            
            if not cont.path_valido():
                print(cont.nombre + " No tiene un path valido.")
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
                    pass
                case _: # Default
                    pass

    def _yaCargado(self, cont):
        """
        Recibe un objeto de contenido y devuelve True si ya está precargado en el próximo input que va a salir al aire. False si no.
        """
        vMix = self.vMix
        match cont.tipo:
            case TipoContenido.VIDEO:
                return ((vMix.getInputPath_num(NumsInput.VIDEO_A) == cont.path and self.videoAct == NumsInput.VIDEO_A) or (vMix.getInputPath_num(NumsInput.VIDEO_B) == cont.path and self.videoAct == NumsInput.VIDEO_B))
            case TipoContenido.PLACA:
                return ((vMix.getInputPath_num(NumsInput.PLACA_A) == cont.path and self.placaAct == NumsInput.PLACA_A) or (vMix.getInputPath_num(NumsInput.PLACA_B) == cont.path and self.placaAct == NumsInput.PLACA_B))
            case TipoContenido.FOTOBMP:
                return ((vMix.getInputPath_num(NumsInput.MICRO_A) == cont.path and self.microAct == NumsInput.MICRO_A) or (vMix.getInputPath_num(NumsInput.MICRO_B) == cont.path and self.microAct == NumsInput.MICRO_B))
            case TipoContenido.MUSICA:
                pass

    def playBlip(self):
        vMix = self.vMix

        vMix.setAudio_on(NumsInput.BLIP) # Algorítimicamente es lo mismo preguntar si está apagado el sonido que prenderlo todas las veces
        vMix.playInput_number(NumsInput.BLIP)

    def _goLive(self,contAct):
        """
        Este método tiene la lógica para verificar que tipo de input se tiene que cambiar (1 a 6), llama a un metodo para cambiar correctamente

        OJO XQ EL FLUJO DE TODA ESTA FUNCION DEPENDE DE QUE ESTÉ CORRECTAMENTE CARGADO EL PROX. HAY QUE HACER HACER ALGO PARA RESOLVER CUANDO NO ES ASÍ.
        """
        print("Hora actual: " + str(datetime.now().time()))
        if contAct == None:
            print("Contenido inexistente")

        tipo = contAct.tipo
        match tipo:
            case TipoContenido.VIDEO:
                self._goLiveVideo()
            case TipoContenido.CAMARA:
                self.vMix.cutDirect_number(1) # PLACEHOLDER
            case TipoContenido.PLACA:
                self._goLivePlaca() # Cuando es placa swappea el input del overlay 1.
            case TipoContenido.MUSICA:
                pass
            case TipoContenido.IMAGENCAM:
                self.vMix.cutDirect_number(1) # PLACEHOLDER TAMBIEN
            case TipoContenido.FOTOBMP:
                self._goLiveMicro()
            case _:
                print(f"Tipo de contenido desconocido: {tipo}")

        self._cargaProx() # Después de mandar al aire precarga el prox.

    def _goLiveVideo(self):
        # Toggle de inputs de video.
        vMix = self.vMix
        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        if self.videoProx is None:
            print("Error de precarga de video. (post)")
            return

        vMix.setOutput_number(self.videoProx) # Manda al aire
        vMix.restartInput_number(self.videoProx)
        time.sleep(0.05) # Reinicia, espera y manda play
        vMix.playInput_number(self.videoProx)


        if self.videoAct is not None:
            vMix.listClear(self.videoAct)

        self.videoAct = self.videoProx
        self.videoProx = None

    def _goLivePlaca(self):
        # Toggle de inputs de placa.
        vMix = self.vMix

        if self.placaProx is None:
            print("Error de precarga de placa.")
            return

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
            print("Error de precarga de micro.")
            return

        vMix.setOutput_number(self.microProx) # Swapeo

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

        vMix.listClear(NumsInput.BLIP)

        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    blipPath = BASE_DIR.parent / "resources" / "BLIP.WAV"
    pathExcel = BASE_DIR / "playlistprueba.xlsx"

    if pathExcel.exists:
        programacion = excParser.crea_lista(pathExcel) # Lista de objetos de clase Contenido con la programacion del dia
        vMix = VmixApi() # Objeto API de vMix
        schMain = Scheduler(programacion,vMix)
        schMain.start(blipPath)
    else:
        print("No se encontró el playlist.xlsx")