import os

from src.CargaDatos import CargaDatos

if __name__ == "__main__":
    # Obtener la ruta absoluta de la carpeta 'Datos' basada en la ubicación de 'main.py'
    carpeta_datos = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Datos"))

    # Ruta completa al archivo CSV
    archivo_entrada = os.path.join(carpeta_datos, "NBA_2024_per_game(03-01-2024).csv")
    archivo_salida = os.path.join(carpeta_datos, "NBA_2024_per_game_limpiado.csv")

    # Crear objeto y probar funciones
    carga = CargaDatos()
    carga.cargar_datos(archivo_entrada)
    carga.mostrar_datos()
    carga.preprocesar_datos()
    print("\nMostrando dataset limpio:")
    print(carga.datos_limpiados.head())  # Muestra el dataset limpio
    carga.exportar_datos_limpiados(archivo_salida)