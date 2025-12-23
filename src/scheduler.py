"""
Este archivo es el principal del proyecto, es el scheduler que se encarga de la lógica de todo lo que debe salir al aire.
Usa todas las clases desarrolladas en el proyecto para organizar la transmisión por medio de una clase Scheduler que checkea cada medio segundo
el estado actual de la transmisión (método _tick()) para decidir si mandar otro contenido al aire o no.

El preset de vMix que se use debe tener 2 inputs por cada contenido dinámico. Tiene que precargar, por ejemplo, el próximo anuncio a salir antes de terminar de sacar el actual aire,
lo mismo con las placas, separadores, micros, etc.
"""

import time
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
        contAct = self.contenidos[self.contenidosIndex]

        if horaAct >= contAct.hora:
            #mandar al aire
            self.contenidosIndex += 1


