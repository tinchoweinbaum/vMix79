"""
Este archivo va a tener las clases/modulos útiles para cualquier otra parte del proyecto.

la clase Contenido representa una fila del excel (un contenido multimedia cualquiera)
"""

from datetime import date, time
from vMixApiWrapper import VmixApi

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

    def go_live(self):
        """
        En este método habría que checkear que tipo de media es self, para poder actualizar el input correspondiente
        en el vMix y mandarlo al aire con el wrapper de la api
        """

    def debug_check_tipo3_paths(self):



        """
        Verifica que todos los contenidos de tipo 3
        tengan un path que comience con 'C:\\Placas'
        """

        print("=== DEBUG: Chequeo de paths para tipo 3 ===")

        ok = True

        for idx, contenido in enumerate(self.contenidos):
            if contenido.tipo == 3:
                if not contenido.path.startswith(r"C:\Placas"):
                    ok = False
                    print(
                        f"[ERROR] Index {idx} | "
                        f"Hora: {contenido.hora} | "
                        f"Nombre: {contenido.nombre} | "
                        f"Path inválido: {contenido.path}"
                    )

        if ok:
            print("OK: Todos los contenidos de tipo 3 tienen paths válidos")

        print("==========================================")
