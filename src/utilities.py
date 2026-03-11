"""
Este archivo va a tener las clases/modulos útiles para cualquier otra parte del proyecto.

la clase Contenido representa una fila del excel (un contenido multimedia cualquiera)

la clasa Camara contiene las filas de la tabla CAMARAS de la db
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
    
class Camara:
    def __init__(self, id_camara: int, nombre: str, desc: str, es_default: bool, dir_conexion: str, tiempo: int, orden: int, activo: bool, escalar: bool, mensaje: str,dir_verificada: str, hora_desde: time, hora_hasta: time, user: str, clave: str, controla_sol: bool):
        self.id_camara = id_camara
        self.nombre = nombre
        self.desc = desc
        self.es_default = es_default
        self.dir_conexion = dir_conexion
        self.tiempo = tiempo
        self.orden = orden
        self.activo = activo
        self.escalar = escalar
        self.mensaje = mensaje
        self.dir_verificada = dir_verificada
        self.hora_desde = hora_desde
        self.hora_hasta = hora_hasta
        self.user = user
        self.clave = clave
        self.controla_sol = controla_sol
