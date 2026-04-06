"""
Archivo principal del proyecto, se encarga de organizar la transmisión y de mandar al aire el contenido que corresponda a la hora que corresponda.
Usa las clases de Database y vMixApiWrapper (TCP) para hacer esto.
Es totalmente dependiente de que el preset de vMix sea el correcto. Los Enums están armados para ese preset y sólo ese preset.
Para la música se "fabrica" un playlist artificial, para poder manejar las horas de salida y entrada de las músicas.
"""
from utilities import Contenido, Camara, Musica # Clase que representa los Contenidos de la programación.
from vMixApiWrapper import VmixApi # Clase wrapper de la webApi de vMix.
from database import Database # Clase wrapper de la Database.
from obsManager import Obs

from enum import IntEnum, Enum
from datetime import datetime, time as dt, timedelta
from typing import List
from pathlib import Path

import threading
import time

# TO DO: Interfaz gráfica en navegador con JavaScript para manejar modo manual/automático. Agregar botón de "Actualizar placas".
# TO DO: Manejo correcto de arranque en reporte local. Encontrar la manera de detectar un reporte local en el arranque.
# TO DO: En el arranque el scheduler intenta mandar órdenes antes de que vMix esté listo, el 1er contenido no sale al aire porque vMix no está listo para recibirlos.
# TO DO: Reintentar infinitamente conectar con la base de datos cuando no logra la conexión. El programa tiene que ser robusto.

class TipoContenido(IntEnum):
    VIDEO = 1
    CAMARA = 2
    PLACA = 3
    MUSICA = 4
    IMAGENCAM = 5
    FOTOBMP = 6

class OverlaySlots(IntEnum):
    SLOT_PLACA = 1
    SLOT_NOTICIAS = 2
    SLOT_HORA = 3
    SLOT_DATOS = 4

class Bloque(IntEnum):
    DURACION = 5 # Duración en minutos.
    CANT_MAX = 288 # Cantidad de bloques = Minutos en un dia // 5

class FuenteDatos(IntEnum):
    SMN = 0
    DATOS_PROPIOS = 1
    ACCUWEATHER = 2

class DuraReporte:
    # da 309 segundos por algún motivo pero son los valores que hay en la db
    PRESENTA = 11
    ACTUAL_DATOS = 55
    ACTUAL_DETALLE = 50
    EXTENDIDO_MANANA = 35
    EXTENDIDO_TARDE = 30
    EXTENDIDO_2DIAS = 30
    SALIDA_SOL = 20
    FASES_LUNARES = 20
    MAREAS = 29
    MAPAS = 29

class IdInputs(str, Enum):
    MUSICA = "be7d700b-c30d-4a88-b4ad-9122dea69540"
    VIDEO_A = "ad2fc430-395b-4dc0-88c4-1b94ffa45aff"
    MICRO_A = "8495af6e-545f-49de-9501-77dd9c84fcd0"
    VIDEO_B = "cbab3333-2c77-438c-a180-2082f7569022"
    MICRO_B = "734f2c01-fd38-42f4-8d6c-d5ec59cdfeff"
    BLIP = "c426ef85-0b21-4518-a7cf-19c0aea8277e"
    OBS_CAMARA_A = "635e44d9-5801-4419-a2ed-e4ff0e0f8dfc"
    OBS_CAMARA_B = "5b0069eb-5a54-4d1e-ac5b-2f56b5b48cf8"

class IdPlacas(str, Enum):
    ACTUAL_DATOS = "6d6b377a-09bf-4e48-836b-7c147836e20b"
    ACTUAL_DETALLE = "1f91d1d8-211d-423e-a6c6-05a76029199d"
    EXTENDIDO_MANANA = "20d3d18d-a21a-4e21-a435-ba168b49114c"
    EXTENDIDO_TARDE = "46411a9f-c71d-49f4-9922-f3154eff93b2"
    EXTENDIDO_2DIAS = "2dd4a0dd-870d-4ff9-b9c3-026782feef72"
    SALIDA_SOL = "7484a5dc-3a50-4dc1-aeee-579358d05c3c"
    FASES_LUNARES = "2a76b702-0ea7-4422-aa05-b76b0bd937e9"
    MAREAS = "c5046a1f-243f-4e5a-b09b-fc64d5493566"
    NOTI_AGUANTE = "97cb7733-6d23-4d89-bb49-07ebccfd11b1"
    NOTICIAS = "c0ea010a-098d-4ea3-94b4-40246e3eed25"
    ACTUAL_DETALLE_CLIMA = "6a5dd7d8-6fda-4538-a6bd-b4a5ca451185"
    HORA_MAPAS = "f150e53a-b06d-4261-b61f-f76be331203e"
    FUENTE_DATOS = "ee4e849f-d024-4707-a682-5e236010c298"

class ObsEscenas(str, Enum):
    CAMARA_A = "CAMARA_A"
    CAMARA_B = "CAMARA_B"

class Scheduler:
    def __init__(self, vMix: VmixApi, database: Database):
        self.nroBloqueAire = 1
        self.bloqueAire: List[Contenido] = [] # Lista de objetos de la clase Contenido representando el bloque actual
        self.bloqueProx: List[Contenido] = [] 
        self.indexBloque = 0 # Puntero al contenido del bloque actual en emisión.

        self.vMix = vMix # Objeto de la api de vMix
        self.database = database # Objeto de la clase Database para hacer queries.

        self.videoAct = None # Los atributos de act y prox sirven para tener en memoria la respuesta a "¿Dónde tengo que mandar el próximo video?"
        self.videoProx = None # Así no hay que preguntarle a vMix que consume muchos más recursos

        self.microAct = None
        self.microProx = None

        self.camaraLive = False
        self.indexBloqueCam = 0
        self.horaProxCam = datetime.now()
        self.bloqueCamaras: List[Camara] = [] # Como el bloque de contenido pero con cámaras

        self.camAct = None # Estos 2 atributos se encargan de los dos inputs de cámaras.
        self.camProx = None

        self.obs = Obs() # Conexión con el web socket de obs para las cámaras
        self.obsAct = None # Que escena de OBS tiene la cámara que está al aire?
        self.obsProx = None

        self.musicaLive = False
        self.horaFadeMusica = None

        self.aguanteActualizada = False # Flag para saber si hay que actualizar Los datos de noti aguante este reporte

        self.running = False

    def start(self):

        self.running = True
        print("Scheduler iniciado\n")

        self.videoAct = None
        self.videoProx = None

        self.microAct = None
        self.microProx = None

        self.__clearAll()

        self._buscaBloque() # Asigna valor correcto actual a self.indexBloque.
        self.getMusica() # Cargo el bloque de música en memoria.
        self._cargaProx() # Precarga los inputs prox para el primer tick.

        if not self.bloqueAire:
            print("Bloque de arranque vacío.\n")
            self.stop()
            return

        self.actualizaPlacas()
        self.actualizaNoticias()
        self.actualizaCamaras()

        time.sleep(0.1)

        self._goLive(self.bloqueAire[self.indexBloque], cargaProx = False) # Manda al aire el contenido correspondiente a la hora de ejecución. NO llama a cargaProx.
        self.indexBloque += 1

        if self.indexBloque < len(self.bloqueAire): # Al disparar el primer contenido manualmente, hay que volver a recargar los inputs para el próximo tick.
            self._cargaProx()
        elif self.indexBloque >= len(self.bloqueAire):
            self._cargaProxBloque()

        time.sleep(1)

        while self.running:
            self._tick()
            time.sleep(0.2)


    def _tick(self):
        """
        _tick es el cerebro del programa, cada 0,2 segundos checkea si hay que mandar un contenido nuevo al aire y lo manda
        si hay que hacerlo. Se encarga también de la rotiación de cámaras y del cambio de bloque.
        
        La hora del contenido se compara con datetime.now().time()
        La hora de las cámaras se compara con datetime.now()
        """

        horaAct = datetime.now()

        # --- Rotación de cámaras ---
        if self.camaraLive and horaAct >= self.horaProxCam:
            self.proximaCamara()

        # --- Fade out de música ---
        if self.musicaLive and self.horaFadeMusica and horaAct >= self.horaFadeMusica:
            self.vMix.scriptStart("MusicaFade")
            print("[INFO]: Ejecutando fade-out de música.")
            self.horaFadeMusica = None
            
        # --- Cambio de Bloque ---
        if self.indexBloque >= len(self.bloqueAire):
            self._swapBloque()
            return
        
        # --- Disparo de contenido ---
        contAct = self.bloqueAire[self.indexBloque] # Objeto del contenido actual
        if horaAct.time() >= contAct.hora: # Si corresponde mandar al aire al contenido apuntado y no se terminó el bloque actual.
            self.indexBloque += 1
            self._goLive(contAct)
            
            if self.indexBloque >= len(self.bloqueAire): # Si mandé el último contenido del bloque al aire precargo el próximo bloque en self.bloqueProx
                self._cargaProxBloque()

    def _buscaBloque(self):
        """
        Carga el bloque actual según la hora y pone el indexBloque en el valor correspondiente.
        """
        #Calculo bloque:

        database = self.database

        ahora = datetime.now()
        fechaAct = ahora.strftime('%d.%m.%Y') 
        horaAct = ahora.time() # esto es datetime.time
        minutoAct = horaAct.hour * 60 +  horaAct.minute
        print(fechaAct)

        self.nroBloqueAire = minutoAct // Bloque.DURACION + 1 # Sumo 1 porque Firebird empieza desde 1 pero python desde 0.

        bloqueNew = database.getBloque_num(fechaAct, self.nroBloqueAire)
        if bloqueNew:
            self.bloqueAire = bloqueNew # Devuelve el bloque actual en una lista.
        else:
            print("[ERROR]: No se encontró el próximo bloque a emitir.\n")
            if ahora.time().minute % 10 < 5: # Si el bloque actual es reporte
                self.bloqueAire = self.__fallbackReporte(ahora, bloqueArranque = True) 
            else: # Si el bloque actual es noti
                self._actualizaNoti()
                self.bloqueAire = self.__fallbackNoti(ahora, bloqueArranque = True)

        # Calculo index:

        self.indexBloque = 0
        for i, cont in enumerate(self.bloqueAire):
            hora_item = cont.hora if isinstance(cont.hora, dt) else cont.hora.time() # Convierto a tipos comparables.
            if horaAct >= hora_item:
                self.indexBloque = i # Index del contenido que debería estar al aire.
            else:
                break

        print(f"Bloque de arranque: {self.nroBloqueAire}\n")
    
    def _startAudio(self):
        vMix = self.vMix

        vMix.setAudio_on(IdInputs.VIDEO_A)
        vMix.setAudio_on(IdInputs.VIDEO_B)

        vMix.setAudio_on(IdInputs.BLIP)
        vMix.setAudio_on(IdInputs.MUSICA)

        
    def _cargaProxBloque(self):
        """
        Este método se llama cuando hay que precargar el próximo bloque, o sea cuando se mandó al aire el último contenido del bloque anterior.
        """

        fechaAct = datetime.now().date()

        nroBloqueProx = self.nroBloqueAire + 1

        if nroBloqueProx > Bloque.CANT_MAX: # Si está al aire el último bloque voy al primer bloque de mañana
            fechaAct = fechaAct + timedelta(days = 1) # Dudo mucho de la lógica de cambio de día. Race condition para llamar antes de las 00
            nroBloqueProx = 1

        self.bloqueProx = self.database.getBloque_num(fechaAct, nroBloqueProx) # Guarda en bloqueProx el próximo bloque
        print(f"[INFO]: Bloque {nroBloqueProx} cargado. Ya no se puede modificar.\n")

    def stop(self):
        self.running = False

    def _precargaVideo(self,cont):
        vMix = self.vMix
        # print("Llamo precarga video.")
        if self.videoProx is not None: # Si no hace falta precargar:
            print("[ERROR]: Error de precarga de video. (pre)\n")
            print(cont.path)
            return
        
        if self.videoAct == IdInputs.VIDEO_A: # Si estaba A al aire, B es prox
            inputLibre = IdInputs.VIDEO_B
        else:
            inputLibre = IdInputs.VIDEO_A # Si estaba B al aire (o ninguno), prox es A
        
        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, cont.path)

        self.videoProx = inputLibre

    def _precargaMicro(self, cont):
        vMix = self.vMix
        # print("Llamo precarga micro.")
        if self.microProx is not None:
            return

        if self.microAct == IdInputs.MICRO_A:
            inputLibre = IdInputs.MICRO_B
        else:
            inputLibre = IdInputs.MICRO_A

        vMix.listClear(inputLibre)
        vMix.listAddInput(inputLibre, cont.path)

        self.microProx = inputLibre

    def _swapBloque(self):
        if not self.bloqueProx:
            print("[ERROR]: No se encontró el próximo bloque a emitir.\n")
            self.bloqueProx = self.__bloqueFallback()
            return
        
        self.bloqueAire = self.bloqueProx
        self.indexBloque = 0
        self.bloqueProx = [] # Como self.bloqueProx = Null

        if self.nroBloqueAire == Bloque.CANT_MAX: # Si acaba de terminar el último bloque del día
            self._cargaProx() # Llamo acá y no afuera del while para no cargar DESPUÉS de esperar y perder 1 segundo
            while datetime.now().time().hour == 23:
                time.sleep(0.1)
            self.nroBloqueAire = 1
        else:
            self.nroBloqueAire += 1
            self._cargaProx()


    def __bloqueFallback(self):
        """
        Devuelve un bloque default, que dependiendo de la hora es reporte o noti aguante.
        """
        ahora = datetime.now()
        bloqueNew: List[Contenido] = []
        if ahora.time().minute % 10 < 5: # Si el bloque que sigue va a ser noti
            self._actualizaNoti()
            bloqueNew = self.__fallbackNoti(ahora)
        else: # Si el bloque que sigue va a ser reporte
            bloqueNew = self.__fallbackReporte(ahora)
 

        return bloqueNew

    def __fallbackNoti(self, ahora: datetime, bloqueArranque = False) -> List[Contenido]:
        """
        Devuelve un bloque artificial de noti aguante. Si bloqueArranque = True, usa una hora en el pasado para que el bloque se dispare ya.
        Si bloqueArranque = False devuelve la próxima hora en la que corresponda noti aguante.
        """
        print("[INFO]: Usando bloque default Noti Aguante\n")
        minuto_actual = ahora.minute
        residuo = minuto_actual % 5 # % 5 y no 10 xq solo se llama después de y 5 a esta función. Esto hace que siempre de una hora de noti aguante y no de reporte.

        if bloqueArranque:
            horaArranque = ahora - timedelta(minutes=residuo)
        else:
            faltante = 5 - residuo
            horaArranque = ahora + timedelta(minutes=faltante)
        horaArranque = horaArranque.time()

        bloqueNoti = []
        objNoti = Contenido(None, ahora.date(), horaArranque, None, TipoContenido.PLACA, None, None, "Noti Aguante", "Noti Aguante", None, None) # Objeto noti aguante.
        objCamara = Contenido(None, ahora.date(), horaArranque, None, TipoContenido.CAMARA, None, None, "CAMARA", "CAMARA", None, None) # Objeto Cámara.
        objMusica = Contenido(None, ahora.date(), horaArranque, None, TipoContenido.MUSICA, None, None, "MUSICA", "MUSICA", None, None) # Objeto Musica.

        bloqueNoti.append(objNoti)
        bloqueNoti.append(objCamara)
        bloqueNoti.append(objMusica)

        return bloqueNoti

    def __fallbackReporte(self, ahora: datetime, bloqueArranque = False) -> List[Contenido]:
        """
        Devuelve un bloque artificial de reporte local con música y rotación de cámaras, creado a mano con duraciones hardcodeadas.
        Si bloqueArranque = True, usa una hora en el pasado para que el bloque se dispare ya.
        Si bloqueArranque = False devuelve la próxima hora en la que corresponda reporte local.
        """

        print("[INFO]: Usando bloque default Reporte Local\n")
        minuto_actual = ahora.minute
        residuo = minuto_actual % 5 # % 5 y no 10 xq solo se llama después de las 0 a esta función. Esto hace que siempre de una hora de reporte y no de noti aguante.

        if bloqueArranque:
            horaArranque = ahora - timedelta(minutes=residuo)
        else:
            faltante = 5 - residuo
            horaArranque = ahora + timedelta(minutes=faltante)

        puntero_temporal = horaArranque
        listaReporte: List[Contenido] = []

        objPresenta = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.VIDEO, None, None, "PRESENTA TRUCHA.mp4", r"\\SERVERLOC\Videos\PRESENTACIONES\PRESENTA TRUCHA.mp4",None, None)
        listaReporte.append(objPresenta)
        puntero_temporal += timedelta(seconds = DuraReporte.PRESENTA)

        objCamara = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.CAMARA, None, None, "CAMARA", "CAMARA", None, None) # Objeto camara
        listaReporte.append(objCamara)

        objMusica = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.MUSICA, None, None, "MUSICA", "MUSICA", None, None) # Objeto Musica
        listaReporte.append(objMusica)

        objDatos = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Actual Datos", r"c:\Placas\HD\tiempoactual.png", None, None)
        listaReporte.append(objDatos)
        puntero_temporal += timedelta(seconds = DuraReporte.ACTUAL_DATOS) # Musica, cámara y datos salen al mismo tiempo.

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Actual Detalle", r"c:\Placas\HD\tiempoactual1.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.ACTUAL_DETALLE)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Extendido Manana", r"c:\Placas\HD\Extendido1.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.EXTENDIDO_MANANA)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Extendido Tarde", r"c:\Placas\HD\Extendido1.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.EXTENDIDO_TARDE)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Extendido 2 Dias", r"c:\Placas\HD\Extendido2.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.EXTENDIDO_2DIAS)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Salida de Sol", r"c:\Placas\aire\HD\salidasol.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.SALIDA_SOL)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Fases Lunares", r"c:\Placas\aire\HD\faseslunares.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.FASES_LUNARES)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.PLACA, None, None, "Mareas", r"c:\Placas\aire\HD\mareas.png", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.MAREAS)

        objDetalle = Contenido(None, ahora.date(), puntero_temporal.time(), None, TipoContenido.VIDEO, None, None, "mapas", r"\\SERVERLOC\Videos\mapas.mp4", None, None)
        listaReporte.append(objDetalle)
        puntero_temporal += timedelta(seconds = DuraReporte.MAPAS)

        return listaReporte
    
    def _stopMusica(self):
        """
        Pausa la música. Saca el tema que estaba sonando para que arranque desde el próximo después.
        """
        self.vMix.setAudio_off(IdInputs.MUSICA)
        time.sleep(0.05)
        self.vMix.pauseInput(IdInputs.MUSICA)
        time.sleep(0.05)
        self.vMix.listNextItem(IdInputs.MUSICA)
        self.musicaLive = False

    def _cargaProx(self):
        """
        Recorre el bloque actual al aire para precargar en los inputs correspondientes.
        """
        # Banderas locales para saber si ya encontramos lo que buscábamos en este tick
        buscando_video = self.videoProx is None
        buscando_micro = self.microProx is None

        for cont in self.bloqueAire[self.indexBloque:]:
            if not buscando_video and not buscando_micro:
                return
            
            if not cont.path_valido() and cont.path not in ["MUSICA"]:
                # print(cont.nombre + " No tiene un path valido.")
                continue

            match cont.tipo:
                case TipoContenido.VIDEO:
                    if buscando_video:
                        self._precargaVideo(cont)
                        buscando_video = False # Actualizo las flags cuando encuentro
                
                case TipoContenido.PLACA:
                    if self.aguanteActualizada == False and cont.nombre == "Noti Aguante":
                        self.aguanteActualizada = True
                        self._actualizaNoti()
                
                case TipoContenido.FOTOBMP:
                    if buscando_micro:
                        self._precargaMicro(cont)
                        buscando_micro = False

                case TipoContenido.MUSICA:
                    continue
                
                case TipoContenido.CAMARA:
                    self.__initCamaras()
      
                case _: # Default
                    print(f"[ERROR]: Tipo de contenido desconocido: {cont.tipo}\n")
                    continue

    def playBlip(self):
        vMix = self.vMix

        vMix.setAudio_on(IdInputs.BLIP)
        vMix.playInput(IdInputs.BLIP)

    def _goLive(self,contAct: Contenido, cargaProx = True):
        """
        Este método tiene la lógica para mandar el tipo de contenido que corresponda al aire.
        Tiene un parámetro que funciona como flag para determinar si hay que precargar el proximo contenido o no. Se usa nada más en el primer llamado del arranque.
        """
        # print("Hora actual: " + str(datetime.now().time()) + "\n")
        if contAct == None:
            print("[ERROR]: Contenido inexistente\n")
            return

        if contAct.tipo != TipoContenido.PLACA and not contAct.path_valido() and contAct.path not in ["CAMARA", "MUSICA","IMAGENCAM"]:
            print("[ERROR]: No se encontró " + contAct.path + ", la imagen va a quedar congelada.\n")
            return

        tipo = contAct.tipo
        match tipo:
            case TipoContenido.VIDEO:
                musicaBool = placaBool = horaBool = contAct.nombre.lower() in ["mapas"] # Lo mantengo en 3 vars. separadas porque capaz después hay otro video que usa otra combinación de estas vars.

                horaAct = datetime.now().time()
                if horaAct.minute % 10 == 0 and horaAct.second < 10: # Cuando viene presenta trucha actualiza cámaras, noticias, placas y pide 5 temas al azar.
                    self.actualizaPlacas()
                    self.actualizaCamaras()
                    self.actualizaNoticias()
                    self.getMusica()
                    self.aguanteActualizada = False # Cuando sale el repote al aire hay que actualizar noti aguante de nuevo.

                print(f"{str(datetime.now().time())} - {contAct.path} al aire")   
                self._goLiveVideo(musica = musicaBool, noticias = placaBool, hora = horaBool)
            case TipoContenido.CAMARA:
                self.camaraLive = True
                self._goLiveCamara()
            case TipoContenido.PLACA:
                self._goLivePlaca(contAct)
            case TipoContenido.MUSICA:
                self._goLiveMusica(contAct.dura)
            case TipoContenido.IMAGENCAM:
                print("IMAGENCAM")
            case TipoContenido.FOTOBMP:
                blipBool = contAct.nombre in ["79 partidas","79 Partidas"]
                self._goLiveMicro(blip = blipBool)
            case _:
                print(f"[ERROR]: Tipo de contenido desconocido: {tipo}\n")

        if cargaProx:
            self._cargaProx() # Después de mandar al aire precarga el prox.
    
    def _goLiveMusica(self, duracion):
        """
        Da play al input de música y guarda la hora del fade out.
        """
        self.musicaLive = True
        print("[INFO]: Música al aire.")
        self.vMix.setAudio_on(IdInputs.MUSICA)
        self.vMix.playInput(IdInputs.MUSICA)
        self.horaFadeMusica = datetime.now() + timedelta(seconds = duracion - Musica.DuracionFade)
        print(f"el fade de música se va a ejecutar a las {self.horaFadeMusica}")

    def _goLiveVideo(self, musica = False, noticias = False, hora = False):
        # Toggle de inputs de video.
        vMix = self.vMix

        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        if not noticias:
            vMix.setOverlay_off(OverlaySlots.SLOT_NOTICIAS)

        if not musica and self.musicaLive:
            self._stopMusica()

        if not hora:
            vMix.setOverlay_off(OverlaySlots.SLOT_HORA)
        else:
            vMix.setOverlay_on(IdPlacas.HORA_MAPAS, OverlaySlots.SLOT_HORA)

        if self.videoAct is not None:
            vMix.listClear(self.videoAct)

        if self.videoProx is None:
            print("[ERROR]: Error de precarga de video. (post)\n")
            return
        
        vMix.setOutput_number(self.videoProx) # Manda al aire
        vMix.restartInput_number(self.videoProx)
        time.sleep(0.05) # Reinicia, espera y manda play
        vMix.playInput(self.videoProx)

        self.camaraLive = False # Ya no sale al aire cámara.

        if self.videoAct is not None:
            vMix.listClear(self.videoAct)

        self.videoAct = self.videoProx
        self.videoProx = None

    def _goLivePlaca(self,contAct: Contenido):
        """
        Toggle de inputs de placa, adaptado para las placas en GT cada una en un input distinto.
        """

        # Si molesta mucho el pequeño delay que hay entre cámara y placa al arrancar al reporte, se puede reimplementar con una lista de placas porque el reporte siempre sigue el mismo orden
        # Y de esa manera se evitaría el match para mejor performance.

        vMix = self.vMix
        self.playBlip()

        match contAct.nombre:
            case "Actual Datos":
                vMix.setOverlay_on(IdPlacas.ACTUAL_DATOS, OverlaySlots.SLOT_PLACA)
                self.actualizaFuenteDatos("Actual Datos")
                time.sleep(0.05)
                vMix.setOverlay_on(IdPlacas.FUENTE_DATOS,OverlaySlots.SLOT_DATOS)

            case "Actual Detalle":
                self.actualizaFuenteDatos("Actual Detalle")
                horaAct = datetime.now().time()
                if horaAct.hour >= 6  and horaAct.hour < 12:
                    vMix.setOverlay_on(IdPlacas.ACTUAL_DETALLE_CLIMA, OverlaySlots.SLOT_PLACA)
                else:
                    vMix.setOverlay_on(IdPlacas.ACTUAL_DETALLE, OverlaySlots.SLOT_PLACA)
                time.sleep(0.05)
                vMix.setOverlay_on(IdPlacas.FUENTE_DATOS,OverlaySlots.SLOT_DATOS)

            case "Extendido Manana":
                    vMix.setOverlay_on(IdPlacas.EXTENDIDO_MANANA, OverlaySlots.SLOT_PLACA)
                    self.actualizaFuenteDatos("Extendido Manana")
                    time.sleep(0.05)
                    vMix.setOverlay_on(IdPlacas.FUENTE_DATOS,OverlaySlots.SLOT_DATOS)

            case "Extendido Tarde":
                vMix.setOverlay_on(IdPlacas.EXTENDIDO_TARDE, OverlaySlots.SLOT_PLACA)
                self.actualizaFuenteDatos("Extendido Tarde")
                time.sleep(0.05)
                vMix.setOverlay_on(IdPlacas.FUENTE_DATOS,OverlaySlots.SLOT_DATOS)

            case "Extendido 2 Dias":
                vMix.setOverlay_on(IdPlacas.EXTENDIDO_2DIAS, OverlaySlots.SLOT_PLACA)
                self.actualizaFuenteDatos("Extendido 2 Dias")
                time.sleep(0.05)
                vMix.setOverlay_on(IdPlacas.FUENTE_DATOS,OverlaySlots.SLOT_DATOS)

            case "Salida de Sol":
                vMix.setOverlay_on(IdPlacas.SALIDA_SOL, OverlaySlots.SLOT_PLACA)
                vMix.setOverlay_off(OverlaySlots.SLOT_DATOS)

            case "Fases Lunares":
                vMix.setOverlay_on(IdPlacas.FASES_LUNARES, OverlaySlots.SLOT_PLACA)
                vMix.setOverlay_off(OverlaySlots.SLOT_DATOS)

            case "Mareas":
                vMix.setOverlay_on(IdPlacas.MAREAS, OverlaySlots.SLOT_PLACA)
                vMix.setOverlay_off(OverlaySlots.SLOT_DATOS)
            
            case "Noti Aguante":
                vMix.setOverlay_on(IdPlacas.NOTI_AGUANTE, OverlaySlots.SLOT_PLACA)
                vMix.setOverlay_off(OverlaySlots.SLOT_DATOS)

            case _:
                print(f"[ERROR]: No se encontró la placa {contAct.nombre}.")
                return
            
        vMix.setOverlay_on(IdPlacas.NOTICIAS, OverlaySlots.SLOT_NOTICIAS) # Después de mandar al aire las placas mando al aire las noticias.


    def _goLiveMicro(self, blip = False):
        # Toggle de inputs de micro (.bmp).
        vMix = self.vMix
        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

        if self.microProx is None:
            print("[ERROR]: Error de precarga de micro.\n")
            return
    
        vMix.setOutput_number(self.microProx) # Swapeo
        if blip: # Si corresponde sonar blip
            self.playBlip()

        self.camaraLive = False # Ya no sale al aire cámara

        if self.microAct is not None:
            vMix.listClear(self.microAct) # Cleareo anterior

        self.microAct = self.microProx
        self.microProx = None

    def __initCamaras(self):
        "Carga en OBS la primera cámara e inicializa los atributos de estado."
        obs = self.obs
        
        self.indexBloqueCam = 0 # Inicializo estados de cámaras.
        self.camAct = None
        self.camProx = IdInputs.OBS_CAMARA_A

        primera_camara = self.bloqueCamaras[0]
        # Agregar protección por si no existe el playlist de cámaras.

        # Inicializo estados de OBS.
        obs.clearScene(ObsEscenas.CAMARA_A) # Limpio las 2 escenas antes de empezar.
        obs.clearScene(ObsEscenas.CAMARA_B)

        obs.add_rtsp(ObsEscenas.CAMARA_A,primera_camara.nombre,primera_camara.dir_conexion)
        self.obsAct = None
        self.obsProx = ObsEscenas.CAMARA_A

    def _swapCamLive(self):
        """Método interno para cambiar la cámara al aire en vMix. Actualiza atributos de estado de vMix y OBS"""
        camAct: Camara = self.bloqueCamaras[self.indexBloqueCam]

        indexProx = (self.indexBloqueCam + 1) % len(self.bloqueCamaras)
        proxCam: Camara = self.bloqueCamaras[indexProx]

        self._actualizarTxtCamara(camAct.nombre) # Nombre de la cámara.

        self.vMix.setOutput_number(self.camProx)

        if self.obsAct is not None: # Borro la cámara anterior.
            self.obs.clearScene(self.obsAct)

        self.horaProxCam = datetime.now() + timedelta(seconds=camAct.tiempo) # Actualiza horaProxCam.

        self.camAct = self.camProx # Actualizo atributos del scheduler.
        self.camProx = IdInputs.OBS_CAMARA_A if self.camAct == IdInputs.OBS_CAMARA_B else IdInputs.OBS_CAMARA_B

        self.obsAct = self.obsProx # Actualizo atributos de OBS.
        self.obsProx = ObsEscenas.CAMARA_A if self.obsAct == ObsEscenas.CAMARA_B else ObsEscenas.CAMARA_B

        self.obs.add_rtsp(self.obsProx, proxCam.nombre, proxCam.dir_conexion) # Precargo la próxima cámara.

    def _actualizarTxtCamara(self, nombreCam):
        """Escribe el .txt que vMix usa de data source para el nombre de la camara"""
        
        intentos = 0
        while intentos <= 3:
            try:
                ruta_txt = Path(__file__).resolve().parent.parent / "resources" / "vmix_resources" / "nombrecam.txt"
                with open(ruta_txt, "w", encoding="utf-8") as f:
                    f.write(nombreCam)
                    break
            except Exception as e:
                print(f"[ERROR]: No se pudo escribir el nombre de la cámara en el .txt: {e}\nReintentando...")
                intentos += 1
    
    def _goLiveCamara(self):
        self.camaraLive = True

        if not self.bloqueCamaras:
            print("[ERROR]: No se encontró un bloque de cámaras válido, se va a emitir la cámara default.") # Dar la opción de cambiar cámara default en la ui del navegador
            return

        self._swapCamLive()

    def proximaCamara(self):

        self.indexBloqueCam += 1
        if self.indexBloqueCam >= len(self.bloqueCamaras): # Aumento index de camaras y si me paso loopeo.
            self.indexBloqueCam = 0

        self._swapCamLive(self.indexBloqueCam)
        
    def actualizaPlacas(self):
        try:
            database = self.database
            fecha = datetime.now().date()
            
            datos = database.getDatos_placas(fecha)
            if datos:
                database._actualizaJson(datos)
                print(f"[INFO]: {datetime.now().strftime('%H:%M:%S')} - Placas actualizadas correctamente.")
            else:
                print("[INFO]: No se encontraron datos para actualizar las IdPlacas. Se mantienen los datos anteriores.")
                
        except Exception as e:
            print(f"[ERROR]: Error al actualizar las placas: {e}")

    def actualizaFuenteDatos(self, placa):
        """"Me convenía hacerlo con SetText, trolie un toque ok lo admito."""
        DB = self.database

        ruta_base = Path(__file__).resolve().parent.parent
        directorio_destino = ruta_base / "resources" / "vmix_resources"
        archivo_final = directorio_destino / "fuente_datos.txt"
        
        try:
            valor = database.getDatos_fuente(placa)

            if valor == FuenteDatos.SMN:
                fuente = "Fuente: S.M.N"
            elif valor == FuenteDatos.DATOS_PROPIOS:
                fuente = "Fuente: Datos Propios."
            else:
                fuente = "Fuente: Accuweather"

            if valor is not None:
                with open(archivo_final, "w", encoding="utf-8") as f:
                    f.write(str(fuente))
                
        except Exception as e:
            print(f"[ERROR]: No se pudo actualizar la fuente de los datos: {e}")

    def actualizaNoticias(self):
        try:
            database = self.database

            noticias = database.get_Noticias()
            if noticias:
                database._actualizaJson({"noticias": noticias})
                print(f"[INFO]: {datetime.now().strftime('%H:%M:%S')} - Noticias actualizadas correctamente.")
            else:
                print("[INFO]: No se encontraron datos para actualizar las noticias. Se mantienen las noticias anteriores.")

        except Exception as e:
            print(f"[ERROR]: Error al actualizar las noticias: {e}")

    def actualizaCamaras(self):
        DB = self.database

        bloqueCamNew = DB.get_Camaras()
        if bloqueCamNew:
            self.bloqueCamaras = bloqueCamNew
            print(f"[INFO]: {datetime.now().strftime('%H:%M:%S')} - Cámaras actualizadas correctamente.\n")
        # Si es Null NO asigno, me quedo con el anterior.
        # Ya está contemplado el caso de que no exista el bloque en la función de la db.

    def _fecha_en_espanol(self):
        ahora = datetime.now()
        
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        dia_semana = dias[ahora.weekday()]
        mes = meses[ahora.month - 1]
        
        return f"{dia_semana}, {ahora.day} de {mes} de {ahora.year}"

    def _actualizaNoti(self):
        # Cálculo hora del próximo reporte.
        ahora = datetime.now()
        minutos_faltantes = 10 - (ahora.minute % 10)
        proxima_hora = ahora + timedelta(minutes=minutos_faltantes)
        horaProxReporte = proxima_hora.replace(second=0, microsecond=0)
        self.vMix.setText(IdPlacas.NOTI_AGUANTE, "Próximo reporte local: " + horaProxReporte.strftime('%H:%M'),"proxReporte.Text")

        #Seteo la fecha
        self.vMix.setText(IdPlacas.NOTI_AGUANTE,self._fecha_en_espanol(),"fecha.Text")
    
    def _loaderMusica(self,bloqueMusicaNew):
        """Método para que el hilo de música cargue las músicas de forma paralela."""
        try:
            vMix = self.vMix

            for tema in bloqueMusicaNew:
                vMix.listAddInput(IdInputs.MUSICA, tema.path)
                time.sleep(10)
        
        except Exception as e:
            print(f"[ERROR]: en el hilo paralelo de carga de música: {e}")

    def getMusica(self):
        """
        Carga el List Input de vMix con canciones traídas de la db.
        La cantidad de canciones se maneja con el atributo temasPorReporte en utilities.py
        """

        DB = self.database

        self.vMix.listClear(IdInputs.MUSICA) # Limpio música anterior.
        time.sleep(0.1)

        bloqueMusicaNew = DB.get_Musicas() # Pido bloque nuevo de músicas
        if bloqueMusicaNew:
            print(f"[INFO]: {datetime.now().strftime('%H:%M:%S')} - Música cargada correctamente.")
        else:
            print("[ERROR]: No se pudieron pedir las músicas.")
            return

        threadCarga = threading.Thread(target = self._loaderMusica, args=(bloqueMusicaNew,),daemon=True)
        threadCarga.start()

    def __clearAll(self):
        vMix = self.vMix

        vMix.listClear(IdInputs.MICRO_A)
        vMix.listClear(IdInputs.MICRO_B)

        vMix.listClear(IdInputs.VIDEO_A)
        vMix.listClear(IdInputs.VIDEO_B)

        vMix.listClear(IdInputs.MUSICA)

        vMix.setOverlay_off(OverlaySlots.SLOT_PLACA)

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent

    database = Database()
    vMix = VmixApi()
    schMain = Scheduler(vMix,database)

    schMain.start()