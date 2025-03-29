import pandas as pd
import os

class CargaDatos:
    """
    Clase para la carga y preprocesamiento de datos desde un archivo CSV.
    """

    def __init__(self):
        """
        Inicializa la clase con atributos para almacenar los datos originales y los datos procesados.
        """
        self.datos = None  # Dataset original
        self.datos_limpiados = None  # Dataset limpio después del preprocesamiento

    def cargar_datos(self, archivo: str):
        """
        Carga los datos desde un archivo CSV.

        :param archivo: Ruta del archivo CSV a cargar.
        """
        try:
            if not os.path.exists(archivo):
                raise FileNotFoundError("Error: El archivo no se encuentra.")

            self.datos = pd.read_csv(archivo)
            print("Datos cargados correctamente.")
        except Exception as e:
            print(f"Ha ocurrido un error al cargar el archivo: {e}")

    def mostrar_datos(self, n: int = 5):
        """
        Muestra las primeras n filas del dataset cargado.

        :param n: Número de filas a mostrar (por defecto 5).
        """
        if self.datos is not None:
            print("\nMostrando primeras filas del dataset:")
            print(self.datos.head(n))
        else:
            print("No hay datos cargados. Usa el método 'cargar_datos' primero.")

    def preprocesar_datos(self):
        """
        Realiza el preprocesamiento de los datos, eliminando valores nulos
        y convirtiendo la columna 'Age' a tipo entero si es necesario.
        """
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
        """
        Exporta los datos preprocesados a un archivo CSV.

        :param archivo_salida: Ruta del archivo CSV de salida.
        """
        if self.datos_limpiados is not None:
            self.datos_limpiados.to_csv(archivo_salida, index=False)
            print("Datos limpios exportados.")
        else:
            print("No hay datos limpios para exportar. Realiza la limpieza primero.")
