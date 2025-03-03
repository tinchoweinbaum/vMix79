"""
Este archivo va a tener las clases/modulos útiles para cualquier otra parte del proyecto.

la clase Contenido representa una fila del excel (un contenido multimedia cualquiera)
"""

from datetime import date, time
from pathlib import Path

class Contenido:
    def __init__(self, id_playlist: str, fecha: date, hora: time, bloque: str, tipo: str, id_mult: str, dura: int, nombre: str, path: str, orden: int, es_publi: bool):
        self.id_playlist = id_playlist
        self.fecha = fecha
        self.hora = hora
        self.bloque = bloque
        self.tipo = tipo
        self.id_mult = id_mult
        self.dura = dura
        self.nombre = nombre
        self.path = path
        self.orden = orden
        self.es_publi = es_publi

    def path_valido(self):        
        p = Path(self.path)
        return p.exists() and p.is_file()