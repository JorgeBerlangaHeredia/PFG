import pandas as pd

class CargaDatos:
    def __init__(self):
        self.datos = None  # Inicializamos los datos como None

    def cargar_datos(self, archivo: str):

        try:
            # Cargar el archivo CSV usando pandas
            self.datos = pd.read_csv(archivo)
            print(f"Datos cargados correctamente desde {archivo}")
        except FileNotFoundError:
            print(f"Error: El archivo {archivo} no se encuentra en la ruta especificada.")
        except Exception as e:
            print(f"Ha ocurrido un error al cargar el archivo: {e}")

    def mostrar_datos(self, n: int = 5):

        if self.datos is not None:
            print(self.datos.head(n))  # Mostrar las primeras 'n' filas
        else:
            print("No hay datos cargados. Usa el método 'cargar_datos' primero.")

    def preprocesar_datos(self):

        if self.datos is not None:
            # Eliminar filas con valores nulos
            self.datos = self.datos.dropna()
            print("Datos preprocesados: filas con valores nulos eliminadas.")

            # Convertir la columna 'Age' a enteros, si no lo es
            if self.datos['Age'].dtype != 'int64':
                self.datos['Age'] = self.datos['Age'].astype(int)
                print("La columna 'Age' ha sido convertida a tipo entero.")
        else:
            print("No hay datos cargados. Usa el método 'cargar_datos' primero.")