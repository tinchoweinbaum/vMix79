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
        self.indexEmision = 0 # El index de contenidos indica cuál es el próximo contenido a emitir. "Puntero"
        self.running = False

    def start(self):
        self.running = True
        print("Scheduler iniciado")

        self._cargaProx() # Precarga los inputs prox para el primer tick

        while self.running:
            self._tick()
            time.sleep(0.5)
        
    
    def stop(self):
        self.running = False

    def _tick(self):
        """
        _tick es el cerebro del programa, cada medio segundo checkea si hay que mandar un contenido nuevo al aire y lo manda
        si hay que hacerlo, depende totalmente de que la lógica de cargar prox sea totalmente correcta y NUNCA falle.
        """
        horaAct = datetime.now().time()
        contAct = self.contenidos[self.indexEmision] # Objeto del contenido actual

        if self.indexEmision > len(self.contenidos): # Si recorrió todos los contenidos del día, stop.
            print("Se transmitió todo el playlist.")
            self.stop()
            return

        if horaAct >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado.
            self._goLive(contAct)
            self.indexEmision += 1
            
    def _checkProxDescargados(self):
        # Devuelve un diccionario, las key son los nums de los inputs prox y los values son booleans

        vMix = self.vMix
        # True si no tiene nada cargado
        return {
            NumsInput.PLACA_PROX: vMix.getInputPath_num(NumsInput.PLACA_PROX) is None,
            NumsInput.VIDEO_PROX: vMix.getInputPath_num(NumsInput.VIDEO_PROX) is None,
            NumsInput.MICRO_PROX: vMix.getInputPath_num(NumsInput.MICRO_PROX) is None,
        }


    def _cargaProx(self):
        """
        Este método se encarga de cargar los inputs XXXX_PROX para que siempre haya algo cargado para poder ponerlo en act y sacarlo al aire.
        """
        vMix = self.vMix
        estadoAct = self._checkProxDescargados()
        if all(estadoAct.values()):
            return

        # True si no tiene nada cargado
        tipos_descargados = {
            TipoContenido.PLACA: estadoAct[NumsInput.PLACA_PROX],
            TipoContenido.VIDEO: estadoAct[NumsInput.VIDEO_PROX],
            TipoContenido.FOTOBMP: estadoAct[NumsInput.MICRO_PROX]
        }

        inputProxTipo = {
            TipoContenido.PLACA: NumsInput.PLACA_PROX,
            TipoContenido.VIDEO: NumsInput.VIDEO_PROX,
            TipoContenido.FOTOBMP: NumsInput.MICRO_PROX
        }

        indexLista = self.indexEmision # Recorro la lista desde el ultimo contenido emitido
        for cont in self.contenidos[indexLista + 1:]:
            if not any(tipos_descargados.values()): # Si son todos False
                return
            
            if tipos_descargados[cont.tipo]: # Si tengo que cargar el cont. actual
                vMix.listAddInput(inputProxTipo[cont.tipo],cont.path)
                tipos_descargados[cont.tipo] = False

        print("No se encontraron más contenidos para precargar")

    def _goLive(self,contAct):

        """
        Este método tiene la lógica para verificar que tipo de input se tiene que cambiar (1 a 6), llama a un metodo para cambiar correctamente

        OJO XQ EL FLUJO DE TODA ESTA FUNCION DEPENDE DE QUE ESTÉ CORRECTAMENTE CARGADO EL PROX. HAY QUE HACER LA FUNCION QUE SE ENCARGA DE ESO
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

        self._cargaProx() # Después de mandar al aire precarga el prox

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