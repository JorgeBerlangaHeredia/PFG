# --- main.py (Fase 4: Sin Correlación Equipo, Añadir Pasos 7 y 8) ---

import pandas as pd
from pathlib import Path
import sys
import matplotlib.pyplot as plt # Para visualizaciones
import seaborn as sns       # Para heatmap
from collections import defaultdict # Para análisis de sensibilidad

# --- Importa tus clases ---
try:
    from CargaDatos import CargaDatos
    from IndicadoresDesempeño import IndicadoresDesempeño
    from Alineación import Alineación # Asume versión Multi-Pos
    from OptimizadorAlineacion import OptimizadorAlineacion # Asume versión Solo 5 Titulares
except ImportError as e: print(f"Error importando clases: {e}"); sys.exit(1)

# --- Funciones helper ---
def obtener_eleccion_usuario_metrica():
    valid_choices = {'1': ('Ofensiva', 'Off_Rating_Simple'), '2': ('Defensiva', 'Def_Rating_Placeholder'), '3': ('Equilibrada', 'EFF/MIN')}
    prompt = "\nSeleccione métrica para optimizar y comparar:\n1. Ofensiva\n2. Defensiva\n3. Equilibrada\nIngrese número: "
    while True:
        choice = input(prompt).strip();
        if choice in valid_choices: return valid_choices[choice]
        else: print("Entrada inválida.")

# Ya no necesitamos cargar_datos_equipo si eliminamos el Paso 6 (OE-2 por correlación)

def cargar_datos_alineaciones_reales(ruta_archivo_reales):
     """Carga datos de alineaciones reales."""
     print(f"\nIntentando cargar alineaciones reales desde: {ruta_archivo_reales}")
     try:
        df = pd.read_csv(ruta_archivo_reales)
        if 'Tm' not in df.columns or len(df.columns) < 6:
             print("  Error: Formato inesperado (faltan columnas 'Tm' o jugadores).")
             return None
        print(f"  Alineaciones reales cargadas ({len(df)} equipos).")
        return df
     except FileNotFoundError: print(f"  Advertencia: Archivo no encontrado en {ruta_archivo_reales}. Se omitirá comparación OE-3/OE-5."); return None
     except Exception as e: print(f"  Error al cargar alineaciones reales: {e}."); return None
# --- Fin Funciones Helper ---


def run_pipeline_combinado():
    print("--- Iniciando Pipeline (Enfoque Combinado - Sin Correlación Equipo) ---")

    # --- PASO 1 & 2: Carga, Preproc, KPIs ---
    print("\n[PASO 1 & 2: Carga, Preprocesamiento y Cálculo de KPIs...]")
    datos_con_metricas = None; datos_limpios = None
    try:
        script_dir = Path(__file__).resolve().parent; nombre_carpeta_csv = 'Datos'
        ruta_csv = str(script_dir.parent / nombre_carpeta_csv / 'NBA_2024_per_game(03-01-2024).csv')
        print(f"Intentando cargar desde: {ruta_csv}")
        cargador = CargaDatos(); cargador.cargar_datos(ruta_csv)
        if cargador.datos is None: raise FileNotFoundError(f"Fallo carga {ruta_csv}")
        cargador.preprocesar_datos(); datos_limpios = cargador.obtener_datos_limpiados()
        if datos_limpios is None: raise RuntimeError("Preproc falló.")
        calculador_kpi = IndicadoresDesempeño(datos_limpios); datos_con_metricas = calculador_kpi.calcular_metricas()
        if datos_con_metricas is None: raise RuntimeError("KPIs falló.")
        if datos_con_metricas.index.name != 'Player': datos_con_metricas.set_index('Player', inplace=True)
        print("Pasos 1 y 2 completados.")
    except Exception as e: print(f"Error crítico en Pasos 1/2: {e}"); sys.exit(1)

    # --- SELECCIÓN MÉTRICA PRINCIPAL ---
    nombre_enfoque, metrica_principal = obtener_eleccion_usuario_metrica()
    print(f"\nEnfoque principal seleccionado: {nombre_enfoque} (Métrica: {metrica_principal})")
    if metrica_principal not in datos_con_metricas.columns: print(f"Error: Métrica '{metrica_principal}' no existe."); sys.exit(1)

    # --- Definir umbrales ---
    min_games_played = 15; min_total_minutes = 300
    print(f"Filtros aplicados: G >= {min_games_played}, MP_Total >= {min_total_minutes}")

    # --- PASO 3: Generación Alineación Simple/Greedy (Baseline) ---
    print(f"\n[PASO 3: Generando Alineación Simple/Greedy ({nombre_enfoque}) - (Multi-Pos)]")
    titulares_simple = None; suplentes_simple = None
    try:
        alineador_simple = Alineación(datos_con_metricas, tipo_ali=nombre_enfoque.lower(), min_g=min_games_played, min_mp_total=min_total_minutes)
        titulares_simple, suplentes_simple = alineador_simple.crear_alineacion()
        alineador_simple.mostrar_alineacion_df(titulares_simple, suplentes_simple)
    except Exception as e: print(f"Error en Paso 3 (Alineación Simple): {e}")

    # --- PASO 4: Optimización Quinteto Titular (PuLP) ---
    print(f"\n[PASO 4: Optimizando Quinteto Titular ({nombre_enfoque}, Métrica: {metrica_principal}) - (PuLP)]")
    quinteto_optimo_df = None; valor_optimo_titulares = None
    optimizador = None # Inicializar por si falla la instanciación
    try:
        optimizador = OptimizadorAlineacion(datos_con_metricas, min_g=min_games_played, min_mp_total=min_total_minutes)
        quinteto_optimo_df, valor_optimo_titulares = optimizador.optimizar_quinteto(metrica_objetivo=metrica_principal)
        if quinteto_optimo_df is not None:
            optimizador.visualizar_alineacion_basico(quinteto_optimo_df, valor_optimo_titulares, metrica_principal)
        else: print("  No se encontró alineación óptima.")
    except ImportError: print("Error: PuLP no instalado."); sys.exit(1)
    except Exception as e: print(f"Error en Paso 4 (Optimización Titulares): {e}")

    # --- PASO 5: Comparación Numérica Titulares (Simple vs Óptimo) ---
    print(f"\n[PASO 5: Comparando Titulares Simple vs. Óptimo para '{metrica_principal}']")
    # ... (Código de comparación como antes) ...
    if quinteto_optimo_df is not None and titulares_simple is not None:
        try:
             # ... (Lógica de comparación y print de mejora_tit) ...
             jugadores_optimos_tit = quinteto_optimo_df['Player'].tolist()
             jugadores_simple_tit = [p for p in titulares_simple.values() if p is not None]
             if len(jugadores_optimos_tit) == 5 and len(jugadores_simple_tit) == 5:
                  missing_opt_t=[p for p in jugadores_optimos_tit if p not in datos_con_metricas.index]
                  missing_simple_t=[p for p in jugadores_simple_tit if p not in datos_con_metricas.index]
                  if not missing_opt_t and not missing_simple_t:
                       valor_total_simple_tit = datos_con_metricas.loc[jugadores_simple_tit, metrica_principal].sum()
                       print(f"  - Valor Total Titulares ({metrica_principal}) - Óptimo (PuLP): {valor_optimo_titulares:.2f}")
                       print(f"  - Valor Total Titulares ({metrica_principal}) - Simple (Greedy): {valor_total_simple_tit:.2f}")
                       mejora_tit = valor_optimo_titulares - valor_total_simple_tit
                       print(f"  - Mejora Titulares por Optimización: {mejora_tit:.2f}")
                       if abs(mejora_tit) < 1e-6: print("    (Nota: Titulares coinciden o son numéricamente equivalentes).")
                       elif mejora_tit < -1e-6: print("    (Advertencia: Titulares Simples superan a Óptimos - revisar).")
                  else: print("  - No se puede comparar (faltan datos jugadores).")
             else: print(f"  - No se puede comparar (Simple: {len(jugadores_simple_tit)}, Óptimo: {len(jugadores_optimos_tit)}).")
        except Exception as e: print(f"  - Error comparando titulares: {e}")
    else: print("  - No se puede comparar (falta una alineación).")


    # --- PASO 6 (antes 7): Comparación vs. Realidad (OE-3 / OE-5) ---
    print("\n[PASO 6: Comparación con Alineaciones Reales (OE-3, OE-5)]")
    # >>>>> ¡¡¡ ACTUALIZA ESTA RUTA !!! <<<<<
    ruta_reales_csv = 'Datos/alineaciones_reales_nba_2024_placeholder.csv' # EJEMPLO
    df_reales = cargar_datos_alineaciones_reales(ruta_reales_csv)
    if df_reales is not None and quinteto_optimo_df is not None:
        try:
            equipo_ejemplo = 'DEN' # Cambia equipo
            lineup_real_series = df_reales[df_reales['Tm'] == equipo_ejemplo]
            if not lineup_real_series.empty:
                 lineup_real_series = lineup_real_series.iloc[0]
                 col_jugadores_reales = [c for c in df_reales.columns if c != 'Tm']
                 jugadores_reales_list = set(lineup_real_series[col_jugadores_reales].dropna().astype(str))
                 jugadores_optimos_list = set(quinteto_optimo_df['Player'])
                 interseccion = len(jugadores_optimos_list.intersection(jugadores_reales_list)); union = len(jugadores_optimos_list.union(jugadores_reales_list)); jaccard = interseccion / union if union > 0 else 0
                 print(f"\nComparación para {equipo_ejemplo}:")
                 print(f"  Quinteto Óptimo ({metrica_principal}): {sorted(list(jugadores_optimos_list))}")
                 print(f"  Quinteto Real Frecuente: {sorted(list(jugadores_reales_list))}")
                 print(f"  Jugadores en común: {interseccion}"); print(f"  Índice de Jaccard: {jaccard:.2f}")
                 jugadores_reales_validos = [p for p in jugadores_reales_list if p in datos_con_metricas.index]
                 if len(jugadores_reales_validos) == len(jugadores_reales_list) and len(jugadores_reales_validos) > 0 :
                      valor_real = datos_con_metricas.loc[list(jugadores_reales_validos), metrica_principal].sum()
                      print(f"  Valor ({metrica_principal}) Óptimo: {valor_optimo_titulares:.2f}"); print(f"  Valor ({metrica_principal}) Real: {valor_real:.2f}"); print(f"  Mejora Teórica Óptimo vs Real: {valor_optimo_titulares - valor_real:.2f}")
                 else: print(f"  No se comparan valores (faltan datos jugadores reales: {len(jugadores_reales_validos)}/{len(jugadores_reales_list)} encontrados).")
            else: print(f"  No hay datos reales para {equipo_ejemplo}.")
        except Exception as e: print(f"  Error comparando con reales: {e}")
    else:
         print("  Se omite comparación con reales (falta archivo o quinteto óptimo).")


    # --- PASO 7 (antes 8): Análisis de Sensibilidad (OE-6) ---
    print("\n[PASO 7: Análisis de Sensibilidad del Optimizador (OE-6)]")
    print("Generando quintetos óptimos para diferentes métricas objetivo...")
    resultados_sensibilidad = {}
    metricas_sensibilidad = {'Ofensiva': 'Off_Rating_Simple','Defensiva': 'Def_Rating_Placeholder','Equilibrada': 'EFF/MIN'}

    # Reutilizar instancia del optimizador si se creó correctamente en Paso 4
    if optimizador:
        for nombre_enf, metrica_sens in metricas_sensibilidad.items():
             print(f"\n--- Optimizando para Enfoque: {nombre_enf} (Métrica: {metrica_sens}) ---")
             if metrica_sens not in datos_con_metricas.columns: print(f"  Métrica no encontrada."); continue
             try:
                  # Usar la instancia existente de optimizador
                  q_sens_df, v_sens = optimizador.optimizar_quinteto(metrica_objetivo=metrica_sens)
                  if q_sens_df is not None:
                       resultados_sensibilidad[nombre_enf] = q_sens_df['Player'].tolist()
                       print(f"  Quinteto: {sorted(resultados_sensibilidad[nombre_enf])} (Valor: {v_sens:.2f})")
                       # optimizador.visualizar_alineacion_basico(q_sens_df, v_sens, metrica_sens) # Opcional
                  else: resultados_sensibilidad[nombre_enf] = []
             except Exception as e: print(f"  Error optimizando para {nombre_enf}: {e}"); resultados_sensibilidad[nombre_enf] = []

        # Análisis de apariciones
        if resultados_sensibilidad:
             print("\nAnálisis Apariciones (Sensibilidad):")
             apariciones = defaultdict(int); jugadores_totales = set()
             for quinteto in resultados_sensibilidad.values():
                 jugadores_totales.update(quinteto)
                 for jugador in quinteto: apariciones[jugador] += 1
             print("  Jugadores en >1 quinteto óptimo:"); [print(f"    - {j}: {c} veces") for j, c in sorted(apariciones.items(), key=lambda item: item[1], reverse=True) if c > 1] or print("    (Ninguno)")
             print(f"\n  Total jugadores únicos en quintetos: {len(jugadores_totales)}")
        print("Análisis de Sensibilidad Completado.")
    else: print("  Se omite sensibilidad (optimizador no disponible por error previo).")


    # --- PASO 8 (antes 9): Visualización Final (OE-4) ---
    print("\n[PASO 8: Visualización (OE-4)]")
    print("  (Implementar gráficos/tablas finales aquí)")
    # Ejemplo: Podrías generar un gráfico de barras de la 'Mejora Teórica Óptimo vs Real'
    # si haces la comparación para varios equipos.


    print("\n--- Pipeline Completado ---")

# --- Ejecutar el pipeline ---
if __name__ == "__main__":
    run_pipeline_combinado()