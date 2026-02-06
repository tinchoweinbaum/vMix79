"""
Wrapper de la conexión a la DB de firebird para el proyecto.
IMPORTANTE: Para que funcione tiene que estar corriendo el servicio de FirebirdDB en windows. También tiene que tener fbclient.dll de 64 bits en la carpeta resources del proyecto.
"""
import fdb
from pathlib import Path

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
            else:
                return False
        except Exception as e:
            print(f"[ERROR]: No se pudo conectar con la base de datos de Firebird. {e}")
            return False
        
        return True
    
    def getBloque_num(self, fecha, nroBloque):
        if self.conn is None:
            print("[ERROR]: No se encontró una conexión válida a la Database para pedir un bloque.")
            return
        
        self.conn.begin()
        cursor: fdb.Cursor = self.conn.cursor()

        query = """SELECT HORA, PATH, NOMBRE, TIPOMULTIMEDIA 
                FROM PLAYLISTCONFIMADO
                WHERE FECHA = CAST(? AS DATE) AND BLOQUE = CAST(? AS INTEGER)
                ORDER BY HORA"""
        
        cursor.execute(query, (fecha, nroBloque))  # Cuando se ejecuta la query, la librería fdb guarda el resultado en un buffer interno de su clase. Con el cursor se fetchea.
        resultado = cursor.fetchall()
        self.conn.commit() # Al final de la transacción se commitea para "avisar" que no vamos a pedir más nada hasta la próxima query

        return resultado
    
if __name__ == "__main__":
    DB = Database(path = r"C:\Users\marti\OneDrive\Desktop\proyectosXD\vMix79\CANAL79_DB.FDB")
    print("[INFO]: Conexión con la DB establecida" if DB.conn is not None else "[ERROR]: No se pudo conectar con la DB")
    filas = DB.getBloque_num("03.03.2025",1)
    print(filas)