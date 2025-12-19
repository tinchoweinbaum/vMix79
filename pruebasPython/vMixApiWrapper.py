"""
Este módulo es un wrapper para la api de vmix, así puedo importar
este módulo en otros archivos y puedo hacer llamados a la API como una persona normal
y no un homínido que lo hace x request html a pelo
"""

import requests

class VmixApi:
    def __init__(self,host = "10.149.53.175" , port = "8080"):
        self.host = host #la IP del host es la ip de la máquina que está corriendo vmix
        self.port = port #Puerto default de vMix
        self.api_url = f"http://{host}:{port}/api/"

    def cut(self):
        return self.__makeRequest("Cut")

    def __makeRequest(self,function,duration = 0): #TODOS LLAMAN A ESTA FUNCIÓN PARA EFECTUAR LA REQUEST.
        params = { #Creo un diccionario para hacer la request.
            "Function": function,
            "Duration": duration
        }

        try: 
            query = requests.get(self.api_url,params = params,timeout = 2.0)
            query.raise_for_status()
            return query.text #devuelve el xml de vMix
        
        except requests.exceptions.HTTPError as e:
            print(f"Error HTTP al comunicarse con la API de vMix: {e}")
            return None

        except requests.RequestException as e:
            print(f"Error de conexion o timeout con la API de vMix: {e}")
            return None
        
if __name__ == "__main__":
    vMix = VmixApi()
    vMix.cut()