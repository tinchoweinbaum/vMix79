"""
Este archivo está deprecado, porque se cambio la lectura del excel por queries a la DB para
conseguir la información de la programación.

df contiene al excel playlist.xlsx

Este programa devuelve una lista de objetos de la clase Contenido.

IMPORTANTE: NO hay que ordenar el playlist por hora porque eso hace que pasen cosas como que salga primero las placas y despues las cámaras, o que salgan cámaras encima de micros.
Hay que ver más adelante una manera de ordenar esto correctamente o de usar Excel de tal manera que tenga esto en cuenta.
"""

import pandas as pd
from utilities import Contenido

def crea_lista(pathExcel: str, ordenaHora = False) -> list[Contenido]:
    df = pd.read_excel(pathExcel) #abre el excel y lo guarda como dataframe en df
    listaProgra = [] #Lista de contenidos a retornar

    if df.empty:
        return []

    for _, fila in df.iterrows():
        contenido = Contenido(
            id_playlist = str(fila["IDPLAYLIST"]), #Cada atributo es parte de una columna en el excel que se identifica por su header (primer fila del documento)
            fecha = fila["FECHA"],
            hora = fila["HORA"],
            bloque = fila["BLOQUE"],
            tipo = fila["TIPOMULTIMEDIA"],
            id_mult = str(fila["IDMULTIMEDIA"]),
            dura = int(fila["DURACION"]),
            nombre = fila["NOMBRE"],
            path = fila["PATH"],
            orden = fila["ORDEN"],
            es_publi = fila["ESPUBLICIDAD"]
        )
        listaProgra.append(contenido)

    if(ordenaHora):
        listaProgra.sort(key = lambda c: c.hora) # MUY IMPORTANTE: DEVUELVE LA LISTA ORDENADA POR HORA DE CADA ELEMENTO SI SE MARCA EL FLAG.

    return listaProgra

def printLista(lista):
    print("====== DEBUG CONTENIDOS ======")

    if not lista:
        print("La lista está vacía")
        return

    for i, c in enumerate(lista, start=1):
        print(f"\n--- Contenido #{i} ---")
        print(f"id_playlist : {c.id_playlist}")
        print(f"fecha       : {c.fecha}")
        print(f"hora        : {c.hora}")
        print(f"bloque      : {c.bloque}")
        print(f"tipo        : {c.tipo}")
        print(f"id_mult     : {c.id_mult}")
        print(f"dura (ms)   : {c.dura}")
        print(f"nombre      : {c.nombre}")
        print(f"path        : {c.path}")

    print("\n====== FIN DEBUG ======\n")