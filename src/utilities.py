"""
Este archivo va a tener las clases/modulos útiles para cualquier otra parte del proyecto.

la clase Contenido representa una fila del excel (un contenido multimedia cualquiera)

la clasa Camara contiene las filas de la tabla CAMARAS de la db, y también un diccionario que guarda la relacion idCam <-> id del input en vMix
junto con un par de métodos necesarios para mandar al aire las camaras
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

    dicc = {
        1:  ("ed223384-698f-454d-80d1-be64f2dafaf9", "Hotel Amsterdam"),
        3:  ("2a64b2e9-16d1-4bac-a98a-cdca8fbaae88", "Sasso"),
        4:  ("1bd316ca-390c-4b76-8d5b-712795c3b330", "Costa Galana"),
        5:  ("8fd1e1de-e418-45b4-915c-04367a54ac5b", "Panorámica"),
        6:  ("66edb959-f378-4b92-8ab0-445a036eaf09", "Alicante"),
        7:  ("a48c47ad-f3a3-4839-830f-d988b68454a4", "Avda. Libertad"),
        8:  ("b5f158be-20b6-4054-b290-3223789633b3", "Gran Hotel Provincial"),
        11: ("4dc333c2-f16f-45a3-bbcf-e946d703d181", "Punto y Banca"),
        12: ("50d94274-51db-4a02-9ef4-2a7fefe433d4", "H. Guerrero"),
        13: ("8271381d-7a3b-4fe3-a5cb-ac201b437b7f", "Punta Iglesia"),
        14: ("509a6c98-443b-41f4-b269-e09431494ffe", "Gianelli Güemes"),
        15: ("d08cb91d-a260-43fa-a930-db75542be195", "Playa Varese"),
        17: ("6f1689be-b78e-4457-b2b7-57a3c9ff40bd", "EOC Mareógrafo"),
        19: ("b6b20fcb-d39f-438b-a224-d5da94301f4a", "Manolo Costa"),
        21: ("dfec8d0c-9648-4124-893d-bceb0561d1cc", "Bahía La Palmera"),
        22: ("b7e1df1f-d391-401e-bce9-6e3be4f699ad", "Gianelli Peatonal"),
        23: ("73d45764-e820-41dc-9878-c1c87f68f2cf", "Club Náutico"),
        24: ("6f0b849b-bb15-40ef-92ba-8dc59da7a166", "Maral Explanada"),
        25: ("f099766a-9d3d-405d-ab00-cf86da0d459a", "Playa Chica"),
        29: ("4ae9e945-19af-41c7-a70d-70ce7810f9a4", "Balneario Marbella"),
        34: ("ec46ce0a-1635-4466-b274-83d61cfbb98a", "Luna Roja"),
        35: ("4281e4c8-c7dd-493e-a10d-c9b8702e3853", "Club de Mar"),
        36: ("e17d5958-5304-480b-9fb4-fa79735188cf", "Torre de Manantiales"),
        37: ("cf56e4c2-95cb-44b3-8b4d-69776240065f", "La Barraca Chapadmalal"),
        39: ("35657cca-991d-49e3-b9a9-3ccf3b400b6b", "Punta Marina"),
    }

    @classmethod # Declara este método como estático para poder llamarlo sin tener que instanciar a la clase
    def _getCam_Id(cls,camNum):
        res = cls.dicc.get(camNum)
        return res[0] if res else None # Si no existe el ID devuelve None
    
    @classmethod # Declara este método como estático para poder llamarlo sin tener que instanciar a la clase
    def _getCam_Nombre(cls,camNum):
        res = cls.dicc.get(camNum)
        return res[1] if res else "Cámara desconocida."
    
class Musica():
    temasPorReporte = 8

    def __init__(self, id_playlist_detail, idplaylist, orden, path, nombre, fecha_ins):
        self.id_playlist_detail = id_playlist_detail
        self.idplaylist = idplaylist # No sé que es esto la verdad, es 1 para todos los elementos de la tabla.
        self.orden = orden
        self.path = path
        self.nombre = nombre
        self.fecha_ins = fecha_ins # tipo DATE de firebird
        