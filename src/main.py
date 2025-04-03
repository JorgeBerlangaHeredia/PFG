# --- main.py ---

import pandas as pd
from pathlib import Path
import sys # Para salir limpiamente si es necesario
# Opcional: Importar matplotlib para gráficos futuros, aunque no se usa en esta versión
# import matplotlib.pyplot as plt

# Importa tus clases
from CargaDatos import CargaDatos
from IndicadoresDesempeño import IndicadoresDesempeño
# Asegúrate que Alineación.py es la versión que usa MULTI-POSICIÓN ahora
from Alineación import Alineación
# Asegúrate que OptimizadorAlineacion.py es la versión con DOBLE OPTIMIZACIÓN
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
        sys.exit(1)
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

    metric_map = { 'ofensiva': 'Off_Rating_Simple', 'defensiva': 'Def_Rating_Placeholder', 'equilibrada': 'EFF/MIN' }
    metrica_objetivo = metric_map.get(chosen_tipo_ali, 'EFF/MIN') # Usar métrica elegida como objetivo
    if metrica_objetivo == metric_map.get(chosen_tipo_ali):
        print(f"Métrica objetivo seleccionada: '{metrica_objetivo}'")
    else:
        print(f"Advertencia: Mapeo de '{chosen_tipo_ali}' falló. Usando métrica por defecto: '{metrica_objetivo}'")
        chosen_tipo_ali = 'equilibrada' # Resetear tipo si falla mapeo

    if metrica_objetivo not in datos_con_metricas.columns:
         print(f"Error crítico: La métrica objetivo '{metrica_objetivo}' no existe en los datos.")
         sys.exit(1)

    # --- Definir umbrales de tiempo de juego ---
    min_games_played = 15
    min_total_minutes = 300
    print(f"\nAplicando filtros para selección: G >= {min_games_played}, MP_Total >= {min_total_minutes}")

    # --- PASO 3: Generación de Alineación Simple/Greedy (Usando Multi-Pos) ---
    print(f"\n[PASO 3: Generando Alineación Simple/Greedy ({chosen_tipo_ali.capitalize()}) - (Multi-Pos, Titulares y Suplentes)]")
    titulares_simple = None
    suplentes_simple = None # Diccionario de suplentes
    try:
        # Asegúrate que Alineación.py usa la versión MULTI-POSICIÓN
        alineador_simple = Alineación(
            datos_con_metricas,
            tipo_ali=chosen_tipo_ali,
            min_g=min_games_played,
            min_mp_total=min_total_minutes
        )
        titulares_simple, suplentes_simple = alineador_simple.crear_alineacion()
        alineador_simple.mostrar_alineacion_df(titulares_simple, suplentes_simple)
    except (ValueError, KeyError) as e:
         print(f"Error durante la generación de alineación simple: {e}")
    except Exception as e:
         print(f"Error inesperado durante la generación de alineación simple: {e}")

    # --- PASO 4: Doble Optimización (Titulares Óptimos + Suplentes Óptimos) ---
    print(f"\n[PASO 4: Generando Equipo Completo con Doble Optimización (Maximizando {metrica_objetivo})...]")
    titulares_opt_df = None # DataFrame
    suplentes_opt_df = None # DataFrame
    valor_opt_titulares = None
    valor_opt_suplentes = None
    try:
        # Asegúrate que OptimizadorAlineacion.py tiene generar_equipo_completo_doble_optimizado
        optimizador = OptimizadorAlineacion(
            datos_con_metricas,
            min_g=min_games_played,
            min_mp_total=min_total_minutes
        )
        # Llamar al método de doble optimización
        titulares_opt_df, suplentes_opt_df, valor_opt_titulares, valor_opt_suplentes = optimizador.generar_equipo_completo_doble_optimizado(
            metrica_objetivo=metrica_objetivo
        )

        # Visualizar el resultado de la doble optimización
        if titulares_opt_df is not None:
             # Asumiendo que tienes visualizar_equipo_doble_optimizado en la clase
             optimizador.visualizar_equipo_doble_optimizado(
                  titulares_opt_df,
                  suplentes_opt_df, # Puede ser None
                  valor_opt_titulares,
                  valor_opt_suplentes, # Puede ser None
                  metrica_objetivo
             )
        else:
             print(f"No se encontró una alineación óptima para titulares con la métrica '{metrica_objetivo}' y filtros.")

    except AttributeError as ae:
         print(f"Error: Método no encontrado en OptimizadorAlineacion (¿Falta 'generar_equipo_completo_doble_optimizado' o 'visualizar_equipo_doble_optimizado'?): {ae}")
    except (ValueError, KeyError) as e:
         print(f"Error durante la doble optimización: {e}")
    except ImportError:
         print("Error: La librería PuLP no está instalada. Ejecuta 'pip install pulp'")
         sys.exit(1)
    except Exception as e:
         print(f"Error inesperado durante la doble optimización: {e}")

    # --- PASO 5: Evaluación Cuantitativa - Comparación de TITULARES ---
    print(f"\n[PASO 5: Comparando Quintetos Titulares Simple vs. Óptimo para '{metrica_objetivo}']")
    if titulares_opt_df is not None and titulares_simple is not None:
        try:
            jugadores_optimos_tit = titulares_opt_df['Player'].tolist()
            jugadores_simple_tit = [p for p in titulares_simple.values() if p is not None]

            if len(jugadores_optimos_tit) == 5 and len(jugadores_simple_tit) == 5:
                if datos_con_metricas.index.name != 'Player': df_comp = datos_con_metricas.set_index('Player')
                else: df_comp = datos_con_metricas
                missing_opt_t = [p for p in jugadores_optimos_tit if p not in df_comp.index]
                missing_simple_t = [p for p in jugadores_simple_tit if p not in df_comp.index]

                if not missing_opt_t and not missing_simple_t:
                     # valor_opt_titulares ya lo tenemos calculado por el optimizador
                     valor_total_simple_tit = df_comp.loc[jugadores_simple_tit, metrica_objetivo].sum()
                     print(f"  - Valor Total Titulares ({metrica_objetivo}) - Óptimo (PuLP): {valor_opt_titulares:.2f}")
                     print(f"  - Valor Total Titulares ({metrica_objetivo}) - Simple (Greedy): {valor_total_simple_tit:.2f}")
                     mejora_tit = valor_opt_titulares - valor_total_simple_tit
                     print(f"  - Mejora Titulares por Optimización: {mejora_tit:.2f}")
                     if mejora_tit < -1e-6: print("    (Advertencia: Titulares Simples superan a Óptimos.)")
                else: print("  - No se puede comparar titulares (faltan datos de jugadores).")
            else: print(f"  - No se puede comparar titulares (Simple: {len(jugadores_simple_tit)}, Óptimo: {len(jugadores_optimos_tit)}).")
        except Exception as e: print(f"  - Error inesperado comparando titulares: {e}")
    else: print("  - No se puede realizar la comparación de titulares (falta una de las alineaciones).")

    # --- PASO 6: Evaluación Cuantitativa - Comparación de SUPLENTES y TOTAL ---
    print(f"\n[PASO 6: Comparando Unidades Suplentes y Equipo Total Simple vs. Doble Óptimo]")
    if suplentes_opt_df is not None and suplentes_simple is not None:
        try:
            jugadores_optimos_sup = suplentes_opt_df['Player'].tolist()
            jugadores_simple_sup = [p for p in suplentes_simple.values() if p is not None]

            if len(jugadores_optimos_sup) == 5 and len(jugadores_simple_sup) == 5:
                if datos_con_metricas.index.name != 'Player': df_comp = datos_con_metricas.set_index('Player')
                else: df_comp = datos_con_metricas
                missing_opt_s = [p for p in jugadores_optimos_sup if p not in df_comp.index]
                missing_simple_s = [p for p in jugadores_simple_sup if p not in df_comp.index]

                if not missing_opt_s and not missing_simple_s:
                    # valor_opt_suplentes ya lo tenemos calculado por el optimizador
                    valor_total_simple_sup = df_comp.loc[jugadores_simple_sup, metrica_objetivo].sum()
                    print(f"  - Valor Total Suplentes ({metrica_objetivo}) - Óptimo (PuLP): {valor_opt_suplentes:.2f}")
                    print(f"  - Valor Total Suplentes ({metrica_objetivo}) - Simple (Greedy): {valor_total_simple_sup:.2f}")
                    mejora_sup = valor_opt_suplentes - valor_total_simple_sup
                    print(f"  - Mejora Suplentes por Optimización: {mejora_sup:.2f}")
                    if mejora_sup < -1e-6: print("    (Advertencia: Suplentes Simples superan a Óptimos.)")

                    # Comparación Total Equipo (solo si tenemos todos los valores)
                    if valor_opt_titulares is not None and 'valor_total_simple_tit' in locals():
                         total_opt = valor_opt_titulares + valor_opt_suplentes
                         total_simple = valor_total_simple_tit + valor_total_simple_sup
                         print(f"\n  - Valor Total Equipo ({metrica_objetivo}) - Doble Óptimo: {total_opt:.2f}")
                         print(f"  - Valor Total Equipo ({metrica_objetivo}) - Simple/Greedy: {total_simple:.2f}")
                         mejora_total = total_opt - total_simple
                         print(f"  - Mejora Total Equipo por Doble Optimización: {mejora_total:.2f}")
                         if mejora_total < -1e-6: print("    (Advertencia: Equipo Simple supera a Doble Óptimo.)")

                else: print("  - No se pueden comparar suplentes (faltan datos de jugadores).")
            else: print(f"  - No se puede comparar suplentes (Simple: {len(jugadores_simple_sup)}, Óptimo: {len(jugadores_optimos_sup)}).")
        except Exception as e: print(f"  - Error inesperado comparando suplentes/total: {e}")
    else: print("  - No se puede realizar la comparación de suplentes (falta una de las unidades suplentes).")

    print("\n--- Pipeline Completado ---")

# --- Ejecutar el pipeline ---
if __name__ == "__main__":
    run_pipeline()