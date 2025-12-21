"""
Este archivo va a tener las clases/modulos útiles para cualquier otra parte del proyecto.

la clase Contenido representa una fila del excel (un contenido multimedia cualquiera)
"""

from datetime import date, time
from vMixApiWrapper import VmixApi

class Contenido:
    def __init__(self, id_playlist: str, fecha: date, hora: time, bloque: str, tipo: str, id_mult: str, dura: int, nombre: str, path: str):
        self.id_playlist = id_playlist
        self.fecha = fecha
        self.hora = hora
        self.bloque = bloque
        self.tipo = tipo
        self.id_mult = id_mult
        self.dura = dura
        self.nombre = nombre
        self.path = path

    def go_live(self):
        """
        En este método habría que checkear que tipo de media es self, para poder actualizar el input correspondiente
        en el vMix y mandarlo al aire con el wrapper de la api
        """