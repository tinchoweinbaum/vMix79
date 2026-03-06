"""
Wrapper de la conexión a la DB de firebird para el proyecto.
IMPORTANTE: Para que funcione tiene que estar corriendo el servicio de FirebirdDB en windows. También tiene que tener fbclient.dll de 64 bits en la carpeta resources del proyecto.
Las fechas las devuelve en formato datetime.datetime
"""
import fdb
import json
import os
from pathlib import Path
from utilities import Contenido
from pathlib import Path
from datetime import date, datetime, time
from dotenv import load_dotenv
from decimal import Decimal

class Database:
    def __init__(self):
        """
        Inicia la conexión con la DB. Busca todos los datos que necesita en un archivo db.env, si no encuentra, lo crea.
        """
        BASE_DIR = Path(__file__).resolve().parent.parent
        envPath = BASE_DIR / "config" / "db.env"
        load_dotenv(str(envPath))

        self.host = os.getenv("DB_HOST","localhost") # El segundo parámetro es el default, por si no existe el .env o no encuentra lo que busca.
        self.path = f"{self.host}:{os.getenv("DB_PATH",r"C:\Canal79\DB\CANAL79_DB.FDB")}"
        self.user = os.getenv("DB_USER","SYSDBA")
        self.password = os.getenv("DB_PASS","masterkey")
        self.charset = "UTF8"
        self.conn = None # Este atributo es el que tiene la conexión como tal guardada en memoria.

        BASE_DIR = Path(__file__).resolve().parent
        dllPath = BASE_DIR.parent / "resources" / "fbclient.dll"
        self.__connectDB(str(dllPath)) # Cuando se instancia la clase se llama esta función, no hace falta hacerlo aparte.

    def __connectDB(self,dllPath):  
        """
        Abre la conexión con la DB. Si ya existía esta conexión, no hace nada.
        Devuelve True si se pudo conectar y False si no.
        """
        try:
            fdb.load_api(dllPath) #
            print(f"[INFO]: fbclient.dll cargada correctamente desde {dllPath}")
        except Exception as e:
            print(f"[ERROR]: Error cargando fbclent.dll: {e}")

        try:
            if self.conn is None:
                self.conn = fdb.connect(dsn = self.path, user = self.user, password = self.password, charset = self.charset) # Metodo de la DB para conectar con python.                
            else:
                return False
        except Exception as e:
            print(f"[ERROR]: No se pudo conectar con la base de datos de Firebird. {e}")
            return False
        
        print("[INFO]: Conexión con la DB establecida.\n")
        return True
    
    def getBloque_num(self, fecha, nroBloque):
        """
        Devuelve un bloque de 5 minutos de programación, representado por una lista
        de objetos de la clase Contenido.
        """

        # Query:
        
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida a la Database para pedir un bloque.")
            return
        
        self.conn.begin()
        cursor: fdb.Cursor = self.conn.cursor()

        query = """SELECT HORA, PATH, NOMBRE, TIPOMULTIMEDIA 
                FROM PLAYLISTCONFIMADO
                WHERE FECHA = CAST(? AS DATE) AND BLOQUE = CAST(? AS INTEGER)
                ORDER BY HORA"""
        
        cursor.execute(query, (f'{fecha}', nroBloque))  # Cuando se ejecuta la query, la librería fdb guarda el resultado en un buffer interno de su clase. Con el cursor se fetchea.
        queryRes = cursor.fetchall() # Devuelve una lista de tuplas, cada tupla es una fila del resultado de la query.
        self.conn.commit() # Al final de la transacción se commitea para "avisar" que no vamos a pedir más nada hasta la próxima query
        
        # Formateo correctamente para scheduler.py

        listaCont = []
        for fila in queryRes:
            hora, path, nombre, tipo = fila # fila es una tupla -> hacemos unpacking de esta manera que python lo permite, gracias python.
            listaCont.append(Contenido(id_playlist = None, 
                                       fecha = fecha, 
                                       hora = hora, bloque = 
                                       nroBloque, tipo = tipo, 
                                       id_mult = None, dura = None,
                                       nombre = nombre, path = path, 
                                       orden = None, es_publi = None)) # Creo objeto de la clase Contenido

        cursor.close()
        return listaCont
    
    def getDatos_placas(self, fecha = None):
        """
        Devuelve un diccionario de diccionarios que contiene los datos de las placas.
        La fecha se usa para las placas de sol y mareas que la necesitan en la query.
        """
        if fecha is None: # Valor por defecto para fecha
            fecha = datetime.now().strftime('%d.%m.%Y')

        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida a la Database para pedir datos de placas.\n")
            return
        
        self.conn.begin() # Arranca la conxión y crea cursor para managearla
        cursor: fdb.Cursor = self.conn.cursor()

        # --- Pido placas 1 ---

        query = "SELECT * FROM CLIMA"
        cursor.execute(query) # Ejecuta la query y busca el resultado del buffer.
        queryRes = cursor.fetchone()

        if queryRes is not None:
            columnas = [col[0] for col in cursor.description] # Creo una lista de nombres
            dictPlacas = dict(zip(columnas, queryRes)) # Crea diccionario para devoler
        else:
            print("[ERROR]: No se encontraron datos para cargar las placas. SELECT * FROM CLIMA no devolvió nada.\n")

        # --- Pido placa sol ---

        query = "SELECT * FROM SOL WHERE (FECHA = CAST(? AS DATE))"
        cursor.execute(query, (fecha,))
        queryRes = cursor.fetchone()

        if queryRes is not None:        
            columnas = [col[0] for col in cursor.description]
            dictSol = dict(zip(columnas,queryRes))
            dictPlacas.update(dictSol) # Concateno diccionarios
            print("actualice salida sol iupi")
        else:
            print(f"[ERROR]: No se encontraron datos para cargar la placa Salida Sol. SELECT * FROM SOL con la fecha {fecha} no devolvió nada.\n")

        # --- Pido placa mareas ---

        query = "SELECT * FROM MAREAS WHERE (FECHA = CAST(? AS DATE))"
        cursor.execute(query, (fecha,))
        queryRes = cursor.fetchone()

        if queryRes is not None:        
            columnas = [col[0] for col in cursor.description]
            dictMareas = dict(zip(columnas, queryRes))
            dictPlacas.update(dictMareas)
            print("actualice placa mareas iupi")
        else:
            print(f"[ERROR]: No se encontraron datos para cargar la placa Mareas. SELECT * FROM MAREAS con la fecha {fecha} no devolvió nada.\n")

        #dictPlacas no tiene formato correcto. Es 1 diccionario gigante con todos los campos de todas las placas.
        cursor.close()
        return self._formatoDict(dictPlacas)
    
    def _actualizaJson(self, dictPlacas: dict):
            """
            Recibe un diccionario de diccionarios (dictPlacas).
            Itera sobre él, creando o sobreescribiendo archivos .json 
            de forma atómica en ../resources/json_placas/
            """
            base_dir = Path(__file__).resolve().parent.parent
            ruta_carpeta = base_dir / "resources" / "json_placas"
            ruta_carpeta.mkdir(parents=True, exist_ok=True) # Si no existe la carpeta la crea

            for nombre_archivo, contenido in dictPlacas.items(): # Itera por el diccionario dumpeando el contenido de cada diccionario en un .json
                ruta_final = ruta_carpeta / f"{nombre_archivo}.json"
                ruta_temp = ruta_final.with_suffix(".tmp")

                try:
                    with open(ruta_temp, 'w', encoding='utf-8') as f:
                        # Convierte diccionario a texto con el formato correcto para el json
                        json.dump([contenido], f, indent=4, ensure_ascii=False, default=self.__formatoFecha) # el default significa "a que tipo convierto si no sé a que tengo que convertir lo que me pasaron"

                    os.replace(ruta_temp, ruta_final)
                    
                except Exception as e:
                    print(f"[ERROR]: No se pudo actualizar {nombre_archivo}.json: {e}")

    def _formatoDict(self,dictPlacas: dict):
        """
        Método "privado" para que el json tenga un formato más fácil de trabajar en _actualizaJson.
        """
        dictFormato = {
            "actualdatos": {
                "temp": dictPlacas.get('TEMP_ACTUAL'),
                "humedad": dictPlacas.get('HUMEDAD'),
                "presion": dictPlacas.get('PRESION'),
                "termica": dictPlacas.get('TERMICA'),
                "viento": dictPlacas.get('VIENTO'),
                "desc": dictPlacas.get('DESCRIPCION'),
                "logo": dictPlacas.get('PATH_ISOLOGO')
            },
            "actualdetalle": {
                "detalle": dictPlacas.get('DETALLE'),
                "max": dictPlacas.get('ACT_MAX'),
                "min": dictPlacas.get('ACT_MIN')
            },
            "extendidomanana": {
                "dia": dictPlacas.get('EM_DIA'),
                "min": dictPlacas.get('EM_TEMP_MIN'),
                "max": dictPlacas.get('EM_TEMP_MAX'),
                "desc_min": dictPlacas.get('EM_DESCRIP_MIN'),
                "desc_max": dictPlacas.get('EM_DESCRIP_MAX'),
                "logo_min": dictPlacas.get('EM_LOGO_MIN'),
                "logo_max": dictPlacas.get('EM_LOGO_MAX')
            },
            "extendido2dias": {
                "ex1_dia": dictPlacas.get('EX1_DIA'),
                "ex1_min": dictPlacas.get('EX1_MIN'),
                "ex1_max": dictPlacas.get('EX1_MAX'),
                "ex1_logo": dictPlacas.get('EX1_LOGO'),
                "ex2_dia": dictPlacas.get('EX2_DIA'),
                "ex2_min": dictPlacas.get('EX2_MIN'),
                "ex2_max": dictPlacas.get('EX2_MAX'),
                "ex2_logo": dictPlacas.get('EX2_LOGO')
            },
            "aux": {
                "actualizacion": dictPlacas.get('ACTUALIZACION'),
                "uv": dictPlacas.get('INDICEUV'),
                "ciudad": dictPlacas.get('CIUDAD'),
                "hora_clima": dictPlacas.get('HORA_CLIMA')
            },
            "salidadesol":{
                "idsol": dictPlacas.get('IDSOL'),  
                "fechasol": dictPlacas.get('FECHA'),
                "salida": dictPlacas.get('SALIDA'),  
                "puesta": dictPlacas.get('PUESTA')    
            },
            "mareas": {
                "fecha": dictPlacas.get('FECHA'),
                "hora1": dictPlacas.get('HORA1'),
                "marea1": dictPlacas.get('MAREA1'),
                "hora2": dictPlacas.get('HORA2'),
                "marea2": dictPlacas.get('MAREA2'),
                "hora3": dictPlacas.get('HORA3'),
                "marea3": dictPlacas.get('MAREA3'),
                "hora4": dictPlacas.get('HORA4'),
                "marea4": dictPlacas.get('MAREA4')
            },
        }
        return dictFormato

    def __formatoFecha(self, obj):
        match obj:
            case datetime() | date():
                return obj.strftime("%d.%m.%Y")
            case time():
                return obj.strftime("%H:%M")
            case Decimal():
                return float(obj)
            case _:
                raise TypeError(f"Tipo {type(obj)} no es serializable")
            
        
if __name__ == "__main__":
    pathDB = r"C:\Canal79\DB\CANAL79_DB.FDB"
    DB = Database()