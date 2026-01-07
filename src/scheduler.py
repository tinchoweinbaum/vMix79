"""
Este archivo es el principal del proyecto, es el scheduler que se encarga de la lógica de todo lo que debe salir al aire.
Usa todas las clases desarrolladas en el proyecto para organizar la transmisión por medio de una clase Scheduler que checkea cada medio segundo
el estado actual de la transmisión (método _tick()) para decidir si mandar otro contenido al aire o no.

El preset de vMix que se use debe tener 2 inputs por cada contenido dinámico. Tiene que precargar, por ejemplo, el próximo anuncio a salir antes de terminar de sacar el actual aire,
lo mismo con las placas, separadores, micros, etc.


IMPORTANTE: REHACER LOS METODOS QUE USEN _isInputLive(). IMPLEMENTAR ATRIBUTOS EN LA CLASE SCHEDULER QUE DETERMINAN SI EL INPUT DE CADA TIPO ES EL A O EL B.
TIENE QUE SER DETERMENÍSTICO E INDEPENDIENTE DE VMIX, NO PUEDO PREGUNTARLE TANTAS VECES AL VMIX QUE ES LO QUE ESTÁ PASANDO.
"""

import time
import excelParser as excParser #Parser del excel
from enum import IntEnum
from datetime import datetime, time as dt, timedelta
from typing import List
from utilities import Contenido # Clase de contenido (fila del excel)
from vMixApiWrapper import VmixApi # Clase wrapper de la webApi de vMix
from pathlib import Path

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

class OverlaySlots(IntEnum):
    PLACA_ACT = 1

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

        # ---- RELOJ SIMULADO ----
        self.sim_start_real = None      # datetime real cuando arranca el scheduler
        self.sim_start_time = dt(0,0) # hora simulada inicial (00:00)

    def _get_sim_time(self):
        elapsed = datetime.now() - self.sim_start_real
        sim_datetime = datetime.combine(datetime.today(), self.sim_start_time) + elapsed
        return sim_datetime.time()

    def start(self):
        self.running = True
        print("Scheduler iniciado")

        self.sim_start_real = datetime.now()  # hora simulada

        self.videoAct = None
        self.videoProx = None

        self.placaAct = None # Modelo act/prox para videos/placas/micros. Act = al aire. Prox = Por salir
        self.placaProx = None # xAct y xProx son números de input en vMix: VIDEO_A o VIDEO_B por ejemplo

        self.microAct = None
        self.microProx = None

        self.__clearAll()
        self._cargaProx() # Precarga los inputs prox para el primer tick

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

        if self.indexEmision > len(self.contenidos): # Si recorrió todos los contenidos del día, stop.
            print("Se transmitió todo el playlist.")
            self.stop()
            return
        
        horaAct = self._get_sim_time()
        contAct = self.contenidos[self.indexEmision] # Objeto del contenido actual

        if horaAct >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado.
            self._goLive(contAct)
            self.indexEmision += 1
    
    def _precargaVideo(self,cont):
        vMix = self.vMix

        if self.videoProx is not None: # Si no hace falta precargar:
            return
        
        if self.videoAct == NumsInput.VIDEO_A:
            inputLibre = NumsInput.VIDEO_B
        else:
            inputLibre = NumsInput.VIDEO_A

        if self.vMix.getInputPath_num(inputLibre) is not None:
            return

        vMix.listAddInput(inputLibre, cont.path)

        self.videoProx = inputLibre

    def _precargaPlaca(self,cont):
        vMix = self.vMix

        if self.placaProx is not None:
            return

        if self.placaAct == NumsInput.PLACA_A:
            inputLibre = NumsInput.PLACA_B
        else:
            inputLibre = NumsInput.PLACA_A

        if self.vMix.getInputPath_num(inputLibre) is not None:
            return

        vMix.listAddInput(inputLibre, cont.path)

        self.placaProx = inputLibre

    def _precargaMicro(self, cont):
        vMix = self.vMix
    
        if self.microProx is not None:
            return

        if self.microAct == NumsInput.MICRO_A:
            inputLibre = NumsInput.MICRO_B
        else:
            inputLibre = NumsInput.MICRO_A

        if self.vMix.getInputPath_num(inputLibre) is not None:
            return

        vMix.listAddInput(inputLibre, cont.path)

        self.microProx = inputLibre
        
    def _cargaProx(self):
        """
        Checkea que hace falta precargar en A o B para todos los tipos de contenido
        """
        indexLista = self.indexEmision # Recorro la lista desde el ultimo contenido emitido

        for cont in self.contenidos[indexLista:]:
            if cont.path_valido() and not self._yaCargado(cont):
                match cont.tipo:
                    case TipoContenido.VIDEO: self._precargaVideo(cont)
                    case TipoContenido.PLACA: self._precargaPlaca(cont)
                    case TipoContenido.FOTOBMP: self._precargaMicro(cont)

                if (self.videoProx is not None and self.placaProx is not None and self.microProx is not None): # Cuando haya precargado todo.
                    return
            elif(not cont.path_valido()):
                print(cont.nombre + " no tiene un path valido.")
            else:
                pass

    def _yaCargado(self, cont):
        """
        Recibe un objeto de contenido y devuelve True si ya está precargado en el próximo input que va a salir al aire. False si no.
        """
        vMix = self.vMix
        match cont.tipo:
            case TipoContenido.VIDEO:
                return ((vMix.getInputPath_num(NumsInput.VIDEO_A) == cont.path and self.videoProx == NumsInput.VIDEO_A) or (vMix.getInputPath_num(NumsInput.VIDEO_B) == cont.path and self.videoProx == NumsInput.VIDEO_B))
            case TipoContenido.PLACA:
                return ((vMix.getInputPath_num(NumsInput.PLACA_A) == cont.path and self.placaProx == NumsInput.PLACA_A) or (vMix.getInputPath_num(NumsInput.PLACA_B) == cont.path and self.placaProx == NumsInput.PLACA_B))
            case TipoContenido.FOTOBMP:
                return ((vMix.getInputPath_num(NumsInput.MICRO_A) == cont.path and self.microProx == NumsInput.MICRO_A) or (vMix.getInputPath_num(NumsInput.MICRO_B) == cont.path and self.microProx == NumsInput.MICRO_B))
            case TipoContenido.MUSICA:
                pass

    def _goLive(self,contAct):
        """
        Este método tiene la lógica para verificar que tipo de input se tiene que cambiar (1 a 6), llama a un metodo para cambiar correctamente

        OJO XQ EL FLUJO DE TODA ESTA FUNCION DEPENDE DE QUE ESTÉ CORRECTAMENTE CARGADO EL PROX. HAY QUE HACER HACER ALGO PARA RESOLVER CUANDO NO ES ASÍ.
        """
        print("Hora actual simulada: " + str(self._get_sim_time()))
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

        if self.todo_precargado == False:
            self._cargaProx() # Después de mandar al aire precarga el prox

    def _goLiveVideo(self):
        vMix = self.vMix

        if self.videoProx is None:
            print("Error de precarga de video.")
            return

        vMix.restartInput_number(self.videoProx)
        vMix.playInput_number(self.videoProx)
        vMix.setOutput_number(self.videoProx)

        if self.videoAct is not None:
            vMix.listClear(self.videoAct)

        self.videoAct = self.videoProx
        self.videoProx = None

    def _goLivePlaca(self):
        vMix = self.vMix

        if self.placaProx is None:
            print("Error de precarga de placa.")
            return

        vMix.setOverlay_on(self.placaProx, OverlaySlots.PLACA_ACT)

        if self.placaAct is not None:
            vMix.listClear(self.placaAct)

        self.placaAct = self.placaProx
        self.placaProx = None


    def _goLiveMicro(self):
        vMix = self.vMix

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

        vMix.setOverlay_off(OverlaySlots.PLACA_ACT)

        
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    pathExcel = BASE_DIR / "playlistprueba.xlsx"
    if pathExcel.exists:
        programacion = excParser.crea_lista(pathExcel) # Lista de objetos de clase Contenido con la programacion del dia
        vMix = VmixApi() # Objeto API de vMix
        schMain = Scheduler(programacion,vMix)
        schMain.start()
    else:
        print("No se encontró el playlist.xlsx")