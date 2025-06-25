# --- START OF FILE CargaDatos.py ---

import pandas as pd
import os

class CargaDatos:
    """
    Clase para cargar y preprocesar datos de jugadores desde un archivo CSV.
    Se encarga de la limpieza inicial de los datos.
    """

    def __init__(self):
        self.datos = None # Almacena los datos crudos cargados
        self.datos_limpiados = None # Almacena los datos después del preprocesamiento
        # Lista de columnas que se consideran esenciales para el análisis
        self.required_cols = ['Player', 'Pos', 'PTS', 'AST', 'TRB', 'MP', 'G', 'FG', 'FGA', 'FT', 'FTA', '3P', 'TOV', 'STL', 'BLK']

    def cargar_datos(self, archivo: str):
        """Carga datos desde un archivo CSV y los guarda en self.datos."""
        try:
            # Comprueba si el archivo existe antes de intentar leerlo
            if not os.path.exists(archivo):
                raise FileNotFoundError(f"Error: El archivo '{archivo}' no se encuentra.")
            self.datos = pd.read_csv(archivo)
            print(f"Datos cargados desde '{archivo}'. Filas: {len(self.datos)}")
            # Intenta convertir algunas columnas a numérico, ignorando errores
            for col in ['Age', 'G', 'GS']:
                 if col in self.datos.columns:
                     self.datos[col] = pd.to_numeric(self.datos[col], errors='coerce')
        except Exception as e:
            print(f"Error al cargar el archivo: {e}")
            self.datos = None

    def preprocesar_datos(self):
        """
        Aplica una serie de pasos de limpieza a los datos cargados.
        - Maneja duplicados de jugadores.
        - Elimina filas con datos faltantes en columnas críticas.
        - Ajusta tipos de datos.
        - Filtra jugadores con tiempo de juego nulo.
        """
        if self.datos is None:
            print("No hay datos cargados para preprocesar.")
            return

        self.datos_limpiados = self.datos.copy() # Trabaja sobre una copia para no alterar los datos originales
        print(f"Preprocesamiento - Filas iniciales: {len(self.datos_limpiados)}")

        # Comprueba si todas las columnas requeridas están presentes
        missing_cols = [col for col in self.required_cols if col not in self.datos_limpiados.columns]
        if missing_cols:
            raise ValueError(f"Faltan columnas requeridas en el CSV: {', '.join(missing_cols)}")

        # --- Manejo de duplicados ---
        # Si un jugador aparece varias veces (por un traspaso), se prioriza la fila con 'Tm' = 'TOT' (total de la temporada).
        self.datos_limpiados['Tm_Priority'] = self.datos_limpiados['Tm'].apply(lambda x: 0 if x == 'TOT' else 1)
        self.datos_limpiados = self.datos_limpiados.sort_values(by=['Player', 'Tm_Priority'])
        # Elimina duplicados por 'Player', quedándose con la primera aparición (que será 'TOT' si existe).
        self.datos_limpiados = self.datos_limpiados.drop_duplicates(subset='Player', keep='first').drop(columns=['Tm_Priority'])
        print(f"Preprocesamiento - Filas tras manejar duplicados: {len(self.datos_limpiados)}")

        # Elimina filas que tengan valores nulos (NaN) en cualquiera de las columnas requeridas.
        self.datos_limpiados = self.datos_limpiados.dropna(subset=self.required_cols)
        print(f"Preprocesamiento - Filas tras dropna en columnas requeridas: {len(self.datos_limpiados)}")

        # --- Conversión y limpieza de tipos de datos ---
        if 'Age' in self.datos_limpiados.columns:
             self.datos_limpiados = self.datos_limpiados.dropna(subset=['Age'])
             if self.datos_limpiados['Age'].dtype != 'int64':
                self.datos_limpiados['Age'] = self.datos_limpiados['Age'].astype(int)

        stats_cols = [col for col in self.required_cols if col not in ['Player', 'Pos']]
        for col in stats_cols:
            if col in self.datos_limpiados.columns:
                self.datos_limpiados[col] = pd.to_numeric(self.datos_limpiados[col], errors='coerce')
        # Vuelve a eliminar NaNs por si la conversión a numérico creó alguno
        self.datos_limpiados = self.datos_limpiados.dropna(subset=stats_cols)

        # Filtra jugadores que no han jugado (MP=0 o G=0)
        self.datos_limpiados = self.datos_limpiados[(self.datos_limpiados['MP'] > 0) & (self.datos_limpiados['G'] > 0)]
        print(f"Preprocesamiento - Filas finales: {len(self.datos_limpiados)}")

        # Llama a la verificación de objetivos del TFG
        self._verificar_objetivo_1()

        print("Preprocesamiento completado.")

    def _verificar_objetivo_1(self):
         """Verifica si los datos limpios cumplen los criterios del OE-1 del TFG."""
         if self.datos_limpiados is None:
             print("OE-1 Verificación: No hay datos limpios.")
             return

         num_jugadores = len(self.datos_limpiados)
         print(f"\n--- Verificación OE-1 ---")
         print(f"Número total de jugadores únicos procesados: {num_jugadores}")
         print(f"-> {'Cumple' if num_jugadores >= 150 else 'No Cumple'}: Número de jugadores {' >=' if num_jugadores >= 150 else ' <'} 150.")

         # Calcula el porcentaje de celdas no nulas en las columnas requeridas
         total_celdas_req = len(self.datos_limpiados) * len(self.required_cols)
         celdas_no_nulas_req = self.datos_limpiados[self.required_cols].notna().sum().sum()
         cobertura_req = (celdas_no_nulas_req / total_celdas_req) * 100 if total_celdas_req > 0 else 0

         print(f"Cobertura de datos para columnas requeridas ({len(self.required_cols)}): {cobertura_req:.2f}%")
         print(f"-> {'Cumple' if cobertura_req >= 95.0 else 'No Cumple'}: Cobertura >= 95%.")
         print("-------------------------\n")


    def obtener_datos_limpiados(self):
        """Devuelve una copia del DataFrame limpio y preprocesado."""
        if self.datos_limpiados is not None:
            return self.datos_limpiados.copy()
        else:
            print("No hay datos limpios disponibles.")
            return None

    def exportar_datos_limpiados(self, archivo_salida: str):
        """Guarda los datos limpios en un nuevo archivo CSV."""
        datos_limpios = self.obtener_datos_limpiados()
        if datos_limpios is not None:
            try:
                datos_limpios.to_csv(archivo_salida, index=False)
                print(f"Datos limpios exportados a '{archivo_salida}'.")
            except Exception as e:
                print(f"Error al exportar datos limpios: {e}")
        else:
            print("No hay datos limpios para exportar.")