"""
Este archivo contiene a la clase que se encarga de cargar los datos de las placas para que el scheduler las mande al aire con los datos correctos.
Se maneja con un archivo json que contiene la info. para todas las placas en valores KV.
"""
import json
from vMixApiWrapper import VmixApi

class PlacasManager:
    def __init__(self,path_json,vMix: VmixApi):
        self.path_json = path_json
        self.vMix = vMix
    
    def cargaPlaca(self,nombrePlaca,inputNum):
        try:
            with open(self.path_json, 'r', encoding = 'utf-8') as arch:
                datos = json.load(arch) # Baja el json entero a un diccionario.

                if nombrePlaca not in datos:
                    print(f"[ERROR]: No se encontró la placa {nombrePlaca}")
                    return
                
                placaAct = datos[nombrePlaca] # placaAct ahora tiene el "subdiccionario" de la placa que se llamó
                # indexPag = placaAct["index"] # Con este valor se llama a selectIndex
                campos = placaAct["campos"]
                for campo, valor in campos.items():
                    self.vMix.setText(inputNum, valor, campo)

        except FileNotFoundError:
            print(f"[ERROR]: No se encontró el archivo {self.path_json}")
        except json.JSONDecodeError:
            print(f"[ERROR]: No se pudo decodificar f{self.path_json}. Probablemente tenga errores de sintaxis.")
        except Exception as e:
            print(f"[ERROR]: Error desconocido {e}")
