"""
Este archivo es el principal del proyecto, es el scheduler que se encarga de la lógica de todo lo que debe salir al aire.
Usa todas las clases desarrolladas en el proyecto para organizar la transmisión por medio de una clase Scheduler que checkea cada medio segundo
el estado actual de la transmisión (método _tick()) para decidir si mandar otro contenido al aire o no.

El preset de vMix que se use debe tener 2 inputs por cada contenido dinámico. Tiene que precargar, por ejemplo, el próximo anuncio a salir antes de terminar de sacar el actual aire,
lo mismo con las placas, separadores, micros, etc.
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

    def _checkAB_descargado(self, A, B):

        """
        A y B son numeros de inputs, sus valores cambian según el tipo de contenido que se quiera consultar.
        Se devuelve el número de input a precargar con el próximo contenido.
        IMPORTANTE: No se "contemplan" los casos de que uno esté al aire y el otro ya esté precargado, porque en ese caso,
        no hay que hacer nada, asumiendo que el contenido precargado en el input que no está al aire es el correcto.
        """
        vMix = self.vMix

        A_live = vMix._isInputLive(A)
        B_live = vMix._isInputLive(B)

        A_cargado = vMix.getInputPath_num(A) is not None
        B_cargado = vMix.getInputPath_num(B) is not None

        if not A_live and not A_cargado:
            return A
        
        if not B_live and not B_cargado:
            return B
        
        return None

    def _checkProxDescargados(self):
        return {
            TipoContenido.PLACA: self._checkAB_descargado(NumsInput.PLACA_A, NumsInput.PLACA_B),
            TipoContenido.VIDEO: self._checkAB_descargado(NumsInput.VIDEO_A, NumsInput.VIDEO_B),
            TipoContenido.FOTOBMP: self._checkAB_descargado(NumsInput.MICRO_A, NumsInput.MICRO_B),
        }

    def _cargaProx(self):
        """
        Rehacer este método para que funcione correctamente con la lógica de input_A e input_B.
        Este método tiene que cargar el input que NO esté al aire del tipo correspondiente.

        OJO ARREGLAR: CUANDO TERMINA DE PRECARGAR TODO EL PLAYLIST SE SALE DEL INDEX DE LA LISTA. MANEJAR ESO.
        """
        vMix = self.vMix
        inputsParaCargar = self._checkProxDescargados() # Diccionario de números de input a cargar. 

        if all(v is None for v in inputsParaCargar.values()): # Si no hay nada a precargar
            return

        indexLista = self.indexEmision # Recorro la lista desde el ultimo contenido emitido

        for cont in self.contenidos[indexLista:]:
            if all(v is None for v in inputsParaCargar.values()): # Si no hay que precargar nada
                return
            
            if inputsParaCargar.get(cont.tipo) is not None: # Si tengo que cargar el cont. actual
                if cont.path_valido() and not self._yaCargado(cont):
                    print("cargo "  + str(cont.nombre) + "en input " + str(NumsInput(inputsParaCargar.get(cont.tipo))))
                    vMix.listAddInput(inputsParaCargar.get(cont.tipo),cont.path)
                    inputsParaCargar[cont.tipo] = None # Problema!!!
                else:
                    print(f"{cont.nombre} no tiene un path valido: {cont.path}")

        #self.todo_precargado = True
        #print("No se encontraron más contenidos para precargar")

    def _yaCargado(self, cont):
        """
        Recibe un objeto de contenido y devuelve True si ya está precargado. False si no, XD.
        """
        vMix = self.vMix
        match cont.tipo:
            case TipoContenido.VIDEO:
                return ((vMix.getInputPath_num(NumsInput.VIDEO_A) == cont.path) and (vMix.getInputPath_num(NumsInput.VIDEO_B) == cont.path))
            case TipoContenido.PLACA:
                return ((vMix.getInputPath_num(NumsInput.PLACA_A) == cont.path) and (vMix.getInputPath_num(NumsInput.PLACA_B) == cont.path))
            case TipoContenido.FOTOBMP:
                return ((vMix.getInputPath_num(NumsInput.MICRO_A) == cont.path) and (vMix.getInputPath_num(NumsInput.MICRO_B) == cont.path))
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
                self.vMix.cutDirect_number(1) # placheolder de camara
            case TipoContenido.FOTOBMP:
                self._goLiveMicro()
            case _:
                print(f"Tipo de contenido desconocido: {tipo}")

        if self.todo_precargado == False:
            self._cargaProx() # Después de mandar al aire precarga el prox

    def _goLiveVideo(self):
        vMix = self.vMix
        A_live = vMix._isInputLive(NumsInput.VIDEO_A)

        if A_live: # Si está A al aire.
            vMix.restartInput_number(NumsInput.VIDEO_B)
            vMix.playInput_number(NumsInput.VIDEO_B)
            vMix.setOutput_number(NumsInput.VIDEO_B)
            vMix.listClear(NumsInput.VIDEO_A)
        else:
            vMix.restartInput_number(NumsInput.VIDEO_A) # Si está B (o ninguno) al aire.
            vMix.playInput_number(NumsInput.VIDEO_A)
            vMix.setOutput_number(NumsInput.VIDEO_A)
            vMix.listClear(NumsInput.VIDEO_B)

    def _goLivePlaca(self):
        vMix = self.vMix

        if vMix._isOverlayLive(OverlaySlots.PLACA_ACT): # Si está saliendo una placa ya al aire.
            if(vMix._getOverlayInput(OverlaySlots.PLACA_ACT) == NumsInput.PLACA_A): # Si era A.
                vMix.setOverlay_on(NumsInput.PLACA_B,OverlaySlots.PLACA_ACT)
                vMix.listClear(NumsInput.PLACA_A)
            else:
                vMix.setOverlay_on(NumsInput.PLACA_A,OverlaySlots.PLACA_ACT) # Si era B.
                vMix.listClear(NumsInput.PLACA_B)
        else:
            vMix.setOverlay_on(NumsInput.PLACA_A,OverlaySlots.PLACA_ACT)

    def _goLiveMicro(self):
        vMix = self.vMix
        A_live = vMix._isInputLive(NumsInput.VIDEO_A)

        if A_live: # Si está A al aire.
            vMix.setOutput_number(NumsInput.MICRO_B)
            vMix.listClear(NumsInput.MICRO_A)
        else:
            vMix.setOutput_number(NumsInput.MICRO_A) # Si está B (o ninguno) al aire.
            vMix.listClear(NumsInput.MICRO_B)

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