"""
Test del driver de python para FirebirdDB.
IMPORTANTE: Para que funcione tiene que estar corriendo el servicio de la DB en windows. También tiene que tener el .dll disponible (el que está en self.__connectDB). La ruta de ese archivo tiene que existir
"""

import fdb
from datetime import datetime

class Database:
    def __init__(self, path, user = "SYSDBA", password = "masterkey"):
        self.path = path
        self.user = user
        self.password = password
        self.charset = "UTF8"
        self.conn = None # Este atributo es el que tiene la conexión como tal guardada en memoria.

        self.__connectDB()

    def __connectDB(self):  
        """
        Abre la conexión con la DB. Si ya existía esta conexión, no hace nada.
        Devuelve True si se pudo conectar y False si no.
        """
        try:
            fdb.load_api(r"C:\Users\marti\OneDrive\Desktop\proyectosXD\vMix79\FB zip kit\bin\fbclient.dll")
            print("DLL cargada correctamente")
        except Exception as e:
            print(f"Error cargando DLL: {e}")

        try:
            if self.conn is None:
                self.conn = fdb.connect(dsn = self.path, user = self.user, password = self.password, charset = self.charset) # Metodo de la DB para conectar con python.
            else:
                return False
        except Exception as e:
            print(f"No se pudo conectar con la base de datos de Firebird. {e}")
            return False
        
        return True
    
    def getBloque_num(self, nroBloque):
        if self.conn is None:
            return
        
        fechaHoy = datetime.now().strftime('%Y-%m-%d')
        self.conn.begin() # ARRANCA LA CONEXION KEMOSIONN
        cursor: fdb.Cursor = self.conn.cursor()

        query = """select * from PLAYLISTCONFIMADO
                    WHERE (FECHA=: ?) AND (BLOQUE=: ?)
                    ORDER BY HORA"""
        
        cursor.execute(query, (fechaHoy, 7)) # Para testear uso el bloque n°7. Después hay que hacer la funcion getNum_bloque
        # Cuando se ejecuta la query, la librería fdb guarda el resultado en un buffer interno de su clase. Con el cursor se fetchea.
        return cursor.fetchall
    
if __name__ == "__main__":
    DB = Database(path = r"C:\Users\marti\OneDrive\Desktop\proyectosXD\vMix79\CANAL79_DB.FDB")
    print(DB.conn is None)
    filas = DB.getBloque_num(2)
    for fila in filas:
        print(fila)