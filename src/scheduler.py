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

class Scheduler:
    def __init__(self,contenidos: List[Contenido] = None, vMix: VmixApi = None):
        self.contenidos = contenidos # Lista de objetos de la clase Contenido
        self.vMix = VmixApi # Objeto de la api de vMix
        self.contenidosIndex = 0 # El index de contenidos indica cuál es el próximo contenido a emitir. "Puntero"
        self.running = False

    def start(self):
        self.running = True
        print("Scheduler iniciado")

        while self.running:
            self._tick()
            time.sleep(0.5)
        
    
    def stop(self):
        self.running = False

    def _tick(self):
        horaAct = datetime.now().time()
        contAct = self.contenidos[self.contenidosIndex] # Objeto del contenido actual

        if self.contenidosIndex > len(self.contenidos): # Si recorrió todos los contenidos del día, stop.
            self.stop()

        if horaAct >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado.
            #mandar al aire
            self.contenidosIndex += 1

class TipoContenido(IntEnum):
    VIDEO = 1
    CAMARA = 2
    PLACA = 3
    MUSICA = 4
    IMAGENCAM = 5
    FOTOBMP = 6

if __name__ == "__main__":
    pathExcel = r"D:\proyectos-repos\vmix79\vMix79\src\playlist.xlsx"
    programacion = excParser.crea_lista(pathExcel) # Lista de objetos de clase Contenido con la programacion del dia
    schMain = Scheduler(programacion,VmixApi()) # Objeto principal Scheduler