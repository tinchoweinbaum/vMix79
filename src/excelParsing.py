"""
Este módulo se va a encargar de parsear el excel de todos los días, o sea, recibe el excel diario y genera las estructuras
de datos que el scheduler necesita para sacar el contenido al aire

df contiene al excel playlist.xlsx

Este programa devuelve una lista de objetos de la clase Contenido
"""

import numpy as np
import pandas as pd
from utilities import Contenido

def crea_lista(pathExcel: str) -> list[Contenido]:
    df = pd.read_excel(pathExcel) #abre el excel y lo guarda como dataframe en df
    listaProgra = [] #Lista de contenidos a retornar

    if df.empty:
        return []

    for _, fila in df.iterrows():
        contenido = Contenido(
            id_playlist = str(fila["IDPLAYLIST"]),
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

    listaProgra.sort(key = lambda c: c.hora) # MUY IMPORTANTE: DEVUELVE LA LISTA ORDENADA POR HORA DE CADA ELEMENTO.
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

listaProgra =crea_lista(r"D:\proyectos-repos\vmix79\vMix79\src\playlist.xlsx")
#printLista(listaProgra)



 