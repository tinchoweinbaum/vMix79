"""
Wrapper de la conexión a la DB de firebird para el proyecto.
IMPORTANTE: Para que funcione tiene que estar corriendo el servicio de FirebirdDB en windows. También tiene que tener fbclient.dll de 64 bits en la carpeta resources del proyecto.
Las fechas las devuelve en formato datetime.datetime

Todas las funciones que tienen el parámetro "Input" pueden funcionar tanto con key como con número o nombre del input.
"""
import fdb
import json
import os
import random
from pathlib import Path
from utilities import Contenido, Camara, Musica
from pathlib import Path
from datetime import date, datetime, time
from dotenv import load_dotenv
from decimal import Decimal

class PathEnum():
    ICONOS = r"C:\Canal79\pronosticos\Iconos"
    ICONOS_NOCHE = r"C:\Canal79\pronosticos\Iconos"
    LUNAS = r"C:\Placas\Lunas"

class HorasDefaultSol():
    # Esta clase tiene los valores default para el horario de cuando se usan los íconos de noche, por si no se puedieron pedir a la db los datos ded la placa de sol. NO afectan a la placa de salida del sol.
    PUESTA = time(19, 0) # 7 de la tarde
    SALIDA = time(6, 0) # 6 de la mañana
class Database:
    def __init__(self):
        """
        Inicia la conexión con la DB. Busca todos los datos que necesita en un archivo db.env, si no encuentra, lo crea.
        """
        BASE_DIR = Path(__file__).resolve().parent.parent
        envPath = BASE_DIR / "config" / "db.env"
        load_dotenv(str(envPath), override = True)

        self.host = os.getenv("DB_HOST","localhost") # El segundo parámetro es el default, por si no existe el .env o no encuentra lo que busca.
        self.path = f"{self.host}:{os.getenv("DB_PATH",r"C:\Users\Operador\Desktop\vMix martin\CANAL79_DB_COPIA_MARZO.FDB")}"
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
            print(f"[ERROR]: Error cargando fbclent.dll, no se podrá intentar conectar a la base de datos: {e}")
            return False

        while self.conn is None:
            try:
                if self.conn is None:
                    self.conn = fdb.connect(dsn = self.path, user = self.user, password = self.password, charset = self.charset) # Metodo de la DB para conectar con python.          
            except Exception as e:
                print(f"[ERROR]: No se pudo conectar con la base de datos de Firebird. Esperando 3 segunos antes de reintentar... {e}")
                time.sleep(3)
            
            print(f"[INFO]: Conexión con la Database en {self.path} establecida.\n")
            return True
    
    def getBloque_num(self, fecha, nroBloque):
        """
        Devuelve un bloque de 5 minutos de programación, representado por una lista
        de objetos de la clase Contenido.
        """

        # Query:

        # test fallback

        # return None
        
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida a la Database para pedir un bloque.")
            return
        
        self.conn.begin()
        cursor: fdb.Cursor = self.conn.cursor()

        query = """SELECT HORA, PATH, NOMBRE, TIPOMULTIMEDIA, DURACION
                FROM PLAYLISTCONFIMADO
                WHERE FECHA = CAST(? AS DATE) AND BLOQUE = CAST(? AS INTEGER)
                ORDER BY HORA"""
        
        cursor.execute(query, ('14.04.2026', nroBloque)) # fecha hardcodeada
        # cursor.execute(query, (f'{fecha}', nroBloque))  # Cuando se ejecuta la query, la librería fdb guarda el resultado en un buffer interno de su clase. Con el cursor se fetchea.
        queryRes = cursor.fetchall() # Devuelve una lista de tuplas, cada tupla es una fila del resultado de la query.
        self.conn.commit() # Al final de la transacción se commitea para "avisar" que no vamos a pedir más nada hasta la próxima query
        
        # Formateo correctamente para scheduler.py

        listaCont = []
        for fila in queryRes:
            hora, path, nombre, tipo, dura = fila # fila es una tupla -> hacemos unpacking de esta manera que python lo permite, gracias python.
            listaCont.append(Contenido(id_playlist = None, 
                                       fecha = fecha, 
                                       hora = hora, bloque = 
                                       nroBloque, tipo = tipo, 
                                       id_mult = None, dura = dura,
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
        else:
            print(f"[ERROR]: No se encontraron datos para cargar la placa Mareas. SELECT * FROM MAREAS con la fecha {fecha} no devolvió nada.\n")

        cursor.close()

        # --- Pido placa luna ---

        query = "SELECT * FROM LUNAS WHERE (FECHAHORA = CAST(? AS DATE))"
        cursor.execute(query, (fecha,))
        queryRes = cursor.fetchone()

        if queryRes is not None:        
            columnas = [col[0] for col in cursor.description]
            dictLuna = dict(zip(columnas,queryRes))
        else:
            print(f"[ERROR]: No se encontraron datos para cargar la placa Fases Lunares. SELECT * FROM LUNAS con la fecha {fecha} no devolvió nada.\n")

        return self._formatoDict(dictPlacas,dictLuna) # Junta los dos diccionarios en 1 diccionario de diccionarios

    def getDatos_fuente(self, placa):
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida para pedir la fuente de los datos actuales.")
            return

        self.conn.begin() # Arranca la conxión y crea cursor para managearla
        cursor: fdb.Cursor = self.conn.cursor()
        
        match placa:
            case "Actual Datos" | "Actual Detalle":
                campo = "USA_ACTUAL"
            case "Extendido Manana" | "Extendido Tarde":
                campo = "USA_EXTENDIDO"
            case "Extendido 2 Dias":
                campo = "USA_PROXHORAS"

        query = f"SELECT {campo} FROM CONFIG_CLIMA"

        try:
            cursor.execute(query)
            queryRes = cursor.fetchone()

            cursor.close()
            self.conn.commit()
        except Exception as e:
            print(f"[ERROR]: Error al pedir de la tabla CLIMA_CONFIG en la base de datos. {e}")

        return queryRes[0] if queryRes else None
    
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

            

    def _formatoDict(self,dictPlacas: dict, dictLuna: dict):
        """
        Método "privado" para que el json tenga un formato más fácil de trabajar en _actualizaJson. Transforma un diccionario gigante que tiene todos los datos de todas las placas en un diccionario de 
        diccionarios, donde cada sub-diccionario representa una placa.
        """
        horaAct = datetime.now().time()
        if dictPlacas.get("salidadelsol") is not None:
            horaSalida  = dictPlacas.get('SALIDA')
            horaPuesta = dictPlacas.get('PUESTA')
        else:
            horaSalida = HorasDefaultSol.SALIDA
            horaPuesta = HorasDefaultSol.PUESTA

        if horaAct >= horaSalida and horaAct <= horaPuesta:
            pathAct = PathEnum.ICONOS
        else:
            pathAct = PathEnum.ICONOS_NOCHE

        dictFormato = {
            "actualdatos": {
                "temp": dictPlacas.get('TEMP_ACTUAL'),
                "humedad": dictPlacas.get('HUMEDAD'),
                "presion": dictPlacas.get('PRESION'),
                "termica": dictPlacas.get('TERMICA'),
                "viento": dictPlacas.get('VIENTO'),
                "desc": dictPlacas.get('DESCRIPCION'),
                "logo": os.path.join(pathAct, dictPlacas.get('PATH_ISOLOGO')).replace("/", "\\")
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
                "logo_min": os.path.join(PathEnum.ICONOS, dictPlacas.get('EM_LOGO_MIN')).replace("/", "\\"),
                "logo_max": os.path.join(PathEnum.ICONOS,  dictPlacas.get('EM_LOGO_MAX')).replace("/", "\\")
            },
            "extendido2dias": {
                "ex1_dia": dictPlacas.get('EX1_DIA'),
                "ex1_min": dictPlacas.get('EX1_MIN'),
                "ex1_max": dictPlacas.get('EX1_MAX'),
                "ex1_logo": os.path.join(PathEnum.ICONOS,  dictPlacas.get('EX1_LOGO')).replace("/", "\\"),
                "ex2_dia": dictPlacas.get('EX2_DIA'),
                "ex2_min": dictPlacas.get('EX2_MIN'),
                "ex2_max": dictPlacas.get('EX2_MAX'),
                "ex2_logo": os.path.join(PathEnum.ICONOS,  dictPlacas.get('EX2_LOGO')).replace("/", "\\")
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
                "marea1": str(dictPlacas.get('MAREA1')) + " mt.", # Agrega mt. al final de la altura de las mareas.
                "hora2": str(dictPlacas.get('HORA2')),
                "marea2": str(dictPlacas.get('MAREA2')) + " mt.",
                "hora3": str(dictPlacas.get('HORA3')),
                "marea3": str(dictPlacas.get('MAREA3')) + " mt.",
                "hora4": str(dictPlacas.get('HORA4')),
                "marea4": str(dictPlacas.get('MAREA4')) + " mt."
            },
            "lunas":{
                "idluna": dictLuna.get('IDLUNA'),
                "fecha": dictLuna.get('FECHAHORA'),
                "tipoluna": dictLuna.get('TIPOLUNA'),
                "salida": dictLuna.get('SALIDA'),
                "puesta": dictLuna.get('PUESTA'),
                "tipo": os.path.join(PathEnum.LUNAS,  dictLuna.get('TIPO')).replace("/", "\\"), # Por algún motivo en la db el ícono de la luna se llama TIPO.
            },
        }
        return dictFormato

    def __formatoFecha(self, obj):
        """
        Método "privado" que se encarga de serializar los objetos de hora y dia y los numeros decimales para que el json los pueda guardar
        """
        match obj:
            case datetime() | date():
                return obj.strftime("%d.%m.%Y")
            case time():
                return obj.strftime("%H:%M")
            case Decimal():
                return float(obj)
            case _:
                raise TypeError(f"Tipo {type(obj)} no es serializable")

    def get_Noticias(self):
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida con la base de datos para pedir las noticias RSS.")
            return
        
        self.conn.begin() # Arranca la conxión y crea cursor para managearla
        cursor: fdb.Cursor = self.conn.cursor()

        query = "select TITULO, DETALLE from NOTICIASDETAIL WHERE (aire = 1) AND  (current_timestamp >= FECHAINICIO ) and (current_timestamp < FECHAfin)"
        cursor.execute(query)
        queryRes = cursor.fetchall() # Ejecuta query

        if queryRes is None:
            print("[INFO]: No se encontraron noticias para actualizar, 'SELECT * FROM NOTICIASDETAIL' devolvió None")
            return
        
        noticias_texto = []
        for fila in queryRes:
                titulo, copete = fila
                texto_noticia = f"{titulo}: {copete} /// "
                noticias_texto.append(texto_noticia)

        random.shuffle(noticias_texto) # Orden aleatorio de noticias cada vez que se actualizan.     

        cursor.close()
        self.conn.commit()

        # Retornamos el diccionario que irá al JSON
        return [{"mensaje": "".join(noticias_texto)}]

    def get_Camaras(self):
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida con la base de datos para pedir las cámaras.")
            return None
        
        self.conn.begin()
        cursor: fdb.Cursor = self.conn.cursor() # Arranca la conxión y crea cursor para managearla

        query = """
            SELECT * FROM CAMARAS
            WHERE (ACTIVO = 1)
            AND (
                (HORA_DESDE = '00:00' AND HORA_HASTA = '00:00') OR
                (HORA_DESDE < CAST(? AS TIME) AND HORA_HASTA > CAST(? AS TIME))
            )
            ORDER BY ORDEN ASC
        """
        # Ojo con esta query porque creo que devuelve mal, una camara viene a través de las 00:00 se rompe la condición booleana
        horaAct = datetime.now().time()
        cursor.execute(query,(horaAct, horaAct))
        queryRes = cursor.fetchall()

        if not queryRes:
            print("[ERROR]: No se pudo obtener el playlist de cámaras, o este no existe.")
            return None

        cursor.close()
        self.conn.commit()

        listaCamaras = []
        for fila in queryRes:
            # Unpacking de la tupla fila
            id_camara, nombre, desc, es_default, dir_conexion, tiempo, orden, activo, escalar, mensaje, dir_verificada, hora_desde, hora_hasta, user, clave, controla_sol = fila   
            # Llamado al constructor con todas las variables en orden
            nueva_camara = Camara(
                id_camara, 
                nombre.strip(), 
                desc, 
                es_default, 
                dir_conexion, 
                tiempo, 
                orden, 
                activo, 
                escalar, 
                mensaje, 
                dir_verificada, 
                hora_desde, 
                hora_hasta, 
                user, 
                clave, 
                controla_sol
            )
            listaCamaras.append(nueva_camara)
        return listaCamaras

    def get_Musicas(self):
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida a la base de datos para pedir las músicas.")
            return None
        
        self.conn.begin()
        cursor: fdb.Cursor = self.conn.cursor() # Arranca la conxión y crea cursor para managearla

        query = "SELECT MAX(ORDEN), MIN(ORDEN) FROM PLAYLISTMUSICADETAIL"
        cursor.execute(query)

        res = cursor.fetchone()
        if not res or res[0] is None:
            return None
        max, min = res 
        entry = random.randint(min, max)


        query = f"SELECT FIRST {Musica.temasPorReporte} * FROM PLAYLISTMUSICADETAIL WHERE ORDEN >= ? ORDER BY ORDEN ASC"
        cursor.execute(query,(entry,))
        bloqueMusica = cursor.fetchall()

        if len(bloqueMusica) < Musica.temasPorReporte: # Si agarré desde el final de la tabla y no llegué a completar los 5, pido desde atrás del entry
            restoTemas = Musica.temasPorReporte - len(bloqueMusica)
            query = f"SELECT FIRST {restoTemas} * FROM PLAYLISTMUSICADETAIL WHERE ORDEN < ? ORDER BY ORDEN DESC"
            cursor.execute(query, (entry,))
            bloqueMusicaResto = cursor.fetchall()

            bloqueMusicaResto.reverse() # Invierto para que la lista final de temas respete el orden de la tabla de musicas
            bloqueMusica = bloqueMusicaResto + bloqueMusica

        cursor.close()
        self.conn.commit()

        listaMusica = []
        for fila in bloqueMusica: # Lo devuelve en formato de la clase Musica
            listaMusica.append(Musica(*fila))
        return listaMusica

        
if __name__ == "__main__":
    pathDB = r"C:\Canal79\DB\CANAL79_DB.FDB"
    DB = Database()
    listaMusica = DB.get_Musicas()
    for musica in listaMusica:
        print(musica.nombre)
