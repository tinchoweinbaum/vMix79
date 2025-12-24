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
from datetime import datetime
from typing import List
from utilities import Contenido # Clase de contenido (fila del excel)
from vMixApiWrapper import VmixApi # Clase wrapper de la webApi de vMix

class TipoContenido(IntEnum):
    VIDEO = 1
    CAMARA = 2
    PLACA = 3
    MUSICA = 4
    IMAGENCAM = 5
    FOTOBMP = 6

class NumsInput(IntEnum):
    CAMARA_ACT = 1
    PLACA_ACT = 2
    MUSICA_ACT = 3
    VIDEO_ACT = 4
    MICRO_ACT = 5
    PLACA_PROX = 6
    MUSICA_PROX = 7
    VIDEO_PROX = 8
    MICRO_PROX = 9

class Scheduler:
    def __init__(self,contenidos: List[Contenido] = None, vMix: VmixApi = None):
        self.contenidos = contenidos # Lista de objetos de la clase Contenido
        self.vMix = VmixApi # Objeto de la api de vMix
        self.contenidosIndex = 0 # El index de contenidos indica cuál es el próximo contenido a emitir. "Puntero"
        self.running = False

    def start(self):
        self.running = True
        print("Scheduler iniciado")

        # Precargar los inputs prox.

        while self.running:
            self._tick()
            time.sleep(0.5)
        
    
    def stop(self):
        self.running = False

    def _tick(self):
        horaAct = datetime.now().time()
        contAct = self.contenidos[self.contenidosIndex] # Objeto del contenido actual

        if self.contenidosIndex > len(self.contenidos): # Si recorrió todos los contenidos del día, stop.
            print("Se transmitió todo el playlist.")
            self.stop()

        if horaAct >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado.
            self._goLive(contAct)
            self.contenidosIndex += 1

    def _goLive(self,contAct):

        """
        Este método tiene la lógica para verificar que tipo de input se tiene que cambiar (1 a 6), llama a un metodo para cambiar correctamente
        """
        if contAct == None:
            print("Contenido inexistente")

        tipo = contAct.tipo
        match tipo:
            case TipoContenido.VIDEO:
                self._swapInput_num(NumsInput.VIDEO_ACT,NumsInput.VIDEO_PROX)
            case TipoContenido.CAMARA:
                pass # No se como voy a manejar todavia las camaras ni la música
            case TipoContenido.PLACA:
                self._swapInput_num(NumsInput.PLACA_ACT,NumsInput.PLACA_PROX)
            case TipoContenido.MUSICA:
                pass
            case TipoContenido.IMAGENCAM:
                self._swapInput_num(TipoContenido.IMAGENCAM) #q pija es imagen cam
            case TipoContenido.FOTOBMP:
                self._swapInput_num(NumsInput.MICRO_ACT,NumsInput.MICRO_PROX)
            case _:
                print(f"Tipo de contenido desconocido: {tipo}")

    def _swapInput_num(self,numInput_act,numInput_prox):
        """
        Pone el contenido de prox en act y pone al aire act, también vacía prox
        """
        vMix = self.vMix

        pathProx = vMix.getInputPath_num(numInput_prox)
        if pathProx is None:
            raise RuntimeError("El input prox no tiene contenido")
        
        vMix.listClear(numInput_prox) # swapea
        vMix.listAddInput(numInput_act,pathProx)

        vMix.setOutput_number(numInput_act) # manda al aire



if __name__ == "__main__":
    pathExcel = r"D:\proyectos-repos\vmix79\vMix79\src\playlist.xlsx"
    programacion = excParser.crea_lista(pathExcel) # Lista de objetos de clase Contenido con la programacion del dia
    schMain = Scheduler(programacion,VmixApi()) # Objeto principal Scheduler
    #schMain.start()