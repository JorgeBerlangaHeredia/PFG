# --- main.py ---

import pandas as pd
from pathlib import Path
import sys # Para salir limpiamente si es necesario

# Importa tus clases
from CargaDatos import CargaDatos
from IndicadoresDesempeño import IndicadoresDesempeño
from Alineación import Alineación
from OptimizadorAlineacion import OptimizadorAlineacion

def obtener_eleccion_usuario():
    """Solicita al usuario el tipo de alineación deseado y valida la entrada."""
    valid_choices = {
        '1': 'ofensiva',
        '2': 'defensiva',
        '3': 'equilibrada'
    }
    prompt = """
Seleccione el tipo de alineación a generar:
1. Ofensiva (Prioriza Off_Rating_Simple)
2. Defensiva (Prioriza Def_Rating_Placeholder - ¡Asegúrate que sea representativa!)
3. Equilibrada (Prioriza EFF/MIN)
Ingrese el número (1, 2, o 3): """

    while True:
        choice = input(prompt).strip()
        if choice in valid_choices:
            return valid_choices[choice]
        else:
            print("Entrada no válida. Por favor, ingrese 1, 2, o 3.")

def run_pipeline():
    """Ejecuta el flujo completo del análisis, permitiendo al usuario elegir el tipo de alineación."""
    print("--- Iniciando Pipeline de Análisis de Baloncesto ---")

    # --- PASO 1: Carga y Preprocesamiento ---
    print("\n[PASO 1: Cargando y Preprocesando Datos...]")
    datos_limpios = None
    try:
        script_dir = Path(__file__).resolve().parent
        # ****** ¡¡¡ AJUSTA 'Data' si tu carpeta se llama diferente !!! ******
        nombre_carpeta_csv = 'Datos'
        ruta_csv_completa = script_dir.parent / nombre_carpeta_csv / 'NBA_2024_per_game(03-01-2024).csv'
        ruta_csv = str(ruta_csv_completa)
    except NameError:
        print("Advertencia: __file__ no está definido. Usando ruta relativa '../Data/...'")
        # ****** ¡¡¡ AJUSTA 'Data' aquí también si es diferente !!! ******
        nombre_carpeta_csv = 'Datos'
        ruta_csv = f'../{nombre_carpeta_csv}/NBA_2024_per_game(03-01-2024).csv'

    print(f"Intentando cargar desde: {ruta_csv}")

    try:
        cargador = CargaDatos()
        cargador.cargar_datos(ruta_csv)
        if cargador.datos is None: raise FileNotFoundError("Carga inicial falló.")
        cargador.preprocesar_datos()
        datos_limpios = cargador.obtener_datos_limpiados()
        if datos_limpios is None: raise RuntimeError("Preprocesamiento no generó datos limpios.")
        print("Datos limpios obtenidos con éxito.")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
         print(f"Error crítico en PASO 1: {e}")
         sys.exit(1) # Salir del script
    except Exception as e:
         print(f"Error inesperado en PASO 1: {e}")
         sys.exit(1)

    # --- PASO 2: Cálculo de Indicadores ---
    print("\n[PASO 2: Calculando Indicadores de Desempeño...]")
    datos_con_metricas = None
    try:
        calculador_kpi = IndicadoresDesempeño(datos_limpios)
        datos_con_metricas = calculador_kpi.calcular_metricas()
        if datos_con_metricas is None: raise RuntimeError("Cálculo de métricas no generó datos.")
        print("Métricas calculadas con éxito.")
        # Opcional: Descomenta para ver una muestra
        # print("Primeras filas de datos con métricas:")
        # if datos_con_metricas.index.name == 'Player':
        #     print(datos_con_metricas.reset_index().head().to_string())
        # else:
        #     print(datos_con_metricas.head().to_string())
    except (ValueError, RuntimeError, KeyError) as e:
        print(f"Error crítico en PASO 2: {e}")
        sys.exit(1)
    except Exception as e:
         print(f"Error inesperado en PASO 2: {e}")
         sys.exit(1)

    # --- SELECCIÓN DE ESTRATEGIA ---
    print("\n[SELECCIÓN DE ESTRATEGIA]")
    chosen_tipo_ali = obtener_eleccion_usuario()
    print(f"Ha seleccionado generar alineaciones con enfoque: '{chosen_tipo_ali.upper()}'")

    # --- Definir métrica correspondiente para optimización ---
    metric_map = {
        'ofensiva': 'Off_Rating_Simple',
        'defensiva': 'Def_Rating_Placeholder', # ¡CUIDADO con esta métrica!
        'equilibrada': 'EFF/MIN'
    }
    metrica_para_optimizar = metric_map.get(chosen_tipo_ali)
    if not metrica_para_optimizar:
        print(f"Advertencia: No se pudo mapear '{chosen_tipo_ali}' a una métrica. Usando 'EFF/MIN'.")
        metrica_para_optimizar = 'EFF/MIN'
        chosen_tipo_ali = 'equilibrada'

    if metrica_para_optimizar not in datos_con_metricas.columns:
         print(f"Error crítico: La métrica '{metrica_para_optimizar}' para optimización no existe.")
         sys.exit(1)

    # --- Definir umbrales de tiempo de juego ---
    min_games_played = 15
    min_total_minutes = 300
    print(f"\nAplicando filtros para selección: G >= {min_games_played}, MP_Total >= {min_total_minutes}")

    # --- PASO 3: Generación de Alineación Simple/Greedy (Titulares y Suplentes) ---
    # <<<--- TÍTULO MÁS CLARO --->>>
    print(f"\n[PASO 3: Generando Alineación Simple/Greedy ({chosen_tipo_ali.capitalize()}) - (Incluye Titulares y Suplentes)]")
    try:
        alineador_simple = Alineación(
            datos_con_metricas,
            tipo_ali=chosen_tipo_ali,
            min_g=min_games_played,
            min_mp_total=min_total_minutes
        )
        # crear_alineacion calcula Titulares y Suplentes
        titulares_simple, suplentes_simple = alineador_simple.crear_alineacion()
        # mostrar_alineacion_df DEBE imprimir la tabla con Titulares Y Suplentes,
        # seguido de las métricas para ambos grupos.
        alineador_simple.mostrar_alineacion_df(titulares_simple, suplentes_simple)
    except (ValueError, KeyError) as e:
         print(f"Error durante la generación de alineación simple: {e}")
    except Exception as e:
         print(f"Error inesperado durante la generación de alineación simple: {e}")

    # --- PASO 4: Optimización de Quinteto Titular (SOLO Titulares Óptimos) ---
    # <<<--- TÍTULO MÁS CLARO --->>>
    print(f"\n[PASO 4: Optimizando Quinteto Titular (Maximizando {metrica_para_optimizar}) - (SOLO 5 Titulares Óptimos)]")
    try:
        optimizador = OptimizadorAlineacion(
            datos_con_metricas,
            min_g=min_games_played,
            min_mp_total=min_total_minutes
        )
        quinteto_optimo_df, valor_optimo = optimizador.optimizar_quinteto(metrica_objetivo=metrica_para_optimizar)

        if quinteto_optimo_df is not None:
            # visualizar_alineacion_basico solo muestra la tabla de los 5 optimizados.
            optimizador.visualizar_alineacion_basico(quinteto_optimo_df, valor_optimo, metrica_para_optimizar)
        else:
            print(f"No se encontró una alineación óptima para la métrica '{metrica_para_optimizar}' con los filtros aplicados.")

    except (ValueError, KeyError) as e:
         print(f"Error durante la optimización: {e}")
    except ImportError:
         print("Error: La librería PuLP no está instalada. Ejecuta 'pip install pulp'")
         sys.exit(1)
    except Exception as e:
         print(f"Error inesperado durante la optimización: {e}")

    print("\n--- Pipeline Completado ---")

# --- Ejecutar el pipeline ---
if __name__ == "__main__":
    run_pipeline()