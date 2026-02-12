"""
Wrapper de la conexión a la DB de firebird para el proyecto.
IMPORTANTE: Para que funcione tiene que estar corriendo el servicio de FirebirdDB en windows. También tiene que tener fbclient.dll de 64 bits en la carpeta resources del proyecto.
"""
import fdb
from pathlib import Path
from utilities import Contenido

class Database:
    def __init__(self, path, user = "SYSDBA", password = "masterkey"):
        self.path = path
        self.user = user
        self.password = password
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
                print("[INFO]: Conexión con la DB establecida" if self.conn is not None else "[ERROR]: No se pudo conectar con la DB")
            else:
                return False
        except Exception as e:
            print(f"[ERROR]: No se pudo conectar con la base de datos de Firebird. {e}")
            return False
        
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
        
        cursor.execute(query, ("12.02.2026", nroBloque))  # Cuando se ejecuta la query, la librería fdb guarda el resultado en un buffer interno de su clase. Con el cursor se fetchea.
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

        return listaCont
    
if __name__ == "__main__":
    pathDB = r"C:\Canal79\DB\CANAL79_DB.FDB"
    DB = Database(path = pathDB)
    filas = DB.getBloque_num("03.03.2025",1)
    for cont in filas:
        print("FECHA: " + cont.fecha)
        print("HORA " + str(cont.hora))
        print("NOMBRE: " + cont.nombre)
        print("PATH: " + cont.path)
        print("\n")