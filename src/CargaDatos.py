import pandas as pd
import os


class CargaDatos:
    def __init__(self):
        self.datos = None  # Dataset original
        self.datos_limpiados = None  # Dataset limpio

    def cargar_datos(self, archivo: str):
        try:
            if not os.path.exists(archivo):
                raise FileNotFoundError(f"Error: El archivo no se encuentra.")

            self.datos = pd.read_csv(archivo)
            print(f"Datos cargados correctamente")
        except Exception as e:
            print(f"Ha ocurrido un error al cargar el archivo: {e}")

    def mostrar_datos(self, n: int = 5):
        if self.datos is not None:
            print("\nMostrando primeras filas del dataset:")
            print(self.datos.head(n))
        else:
            print("No hay datos cargados. Usa el método 'cargardatos' primero.")

    def preprocesar_datos(self):
        if self.datos is not None:
            self.datos_limpiados = self.datos.copy()

            # Eliminar filas con valores nulos
            self.datos_limpiados = self.datos_limpiados.dropna()
            print("Filas con valores nulos eliminadas.")

            # Convertir la columna 'Age' a enteros si existe y no es tipo int64
            if 'Age' in self.datos_limpiados.columns and self.datos_limpiados['Age'].dtype != 'int64':
                self.datos_limpiados['Age'] = self.datos_limpiados['Age'].astype(int)
                print("La columna 'Age' ha sido convertida a tipo entero.")
        else:
            print("No hay datos cargados. Usa el método 'cargar_datos' primero.")

    def exportar_datos_limpiados(self, archivo_salida: str):
        if self.datos_limpiados is not None:
            self.datos_limpiados.to_csv(archivo_salida, index=False)
            print(f"Datos limpios exportados")
        else:
            print("No hay datos limpios para exportar. Realiza la limpieza primero.")