# --- INICIO DEL ARCHIVO main.py (ubicado en src/) ---

import sys
import os
import pandas as pd

# --- Ajuste de Rutas para Datos/ desde src/ ---
script_dir = os.path.dirname(os.path.abspath(__file__))
carpeta_padre = os.path.dirname(script_dir)
datos_dir = os.path.join(carpeta_padre, 'Datos')
ARCHIVO_JUGADORES = os.path.join(datos_dir, "NBA_2024_per_game(03-01-2024).csv")
ARCHIVO_REALES = os.path.join(datos_dir, "ruta_reales_csv.csv")

# Importa las clases
try:
    from CargaDatos import CargaDatos
    from IndicadoresDesempeño import IndicadoresDesempeño
    from OptimizadorAlineacion import OptimizadorAlineacion
    from AnalisisResultados import AnalisisResultados
except ImportError as e: sys.exit(f"Error importando clase: {e}")

# --- Configuración ---
MIN_G = 20
MIN_MP_TOTAL = 500
METRICAS_REFERENCIA = {
    'ofensiva': 'PTS_Total', 'defensiva': 'DEF_VOLUME_Total', 'equilibrada': 'EFF/MIN',
    'eficiencia_total': 'EFF', 'rating_ofensivo': 'Off_Rating_Simple'
}
OPCIONES_USUARIO = {1: 'ofensiva', 2: 'defensiva', 3: 'equilibrada'}
METRICAS_COMPARACION = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total', 'EFF', 'EFF/MIN', 'Off_Rating_Simple', 'Net_Rating_Simple']
METRICAS_COMPARACION_VISUAL = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total', 'EFF']
METRICAS_SENSIBILIDAD = {'Ofensivo (Puntos)': 'PTS_Total', 'Defensivo (Volumen)': 'DEF_VOLUME_Total', 'Equilibrado (EFF/MIN)': 'EFF/MIN', 'Eficiencia Total (EFF)': 'EFF', 'Rating Ofensivo Simple': 'Off_Rating_Simple'}

def main():
    """Orquesta el proceso, mostrando principalmente la comparación visual."""
    print("--- Iniciando Sistema de Optimización y Análisis de Alineaciones NBA ---")
    print(f"--- Filtros aplicados: G >= {MIN_G}, MP_Total >= {MIN_MP_TOTAL} ---")

    # --- PASO 1: Carga y Preprocesamiento ---
    print("\n[PASO 1] Cargando y Preprocesando Datos...")
    cargador = CargaDatos(); datos_limpios = None; datos_limpios_con_tm = None
    try:
        cargador.cargar_datos(ARCHIVO_JUGADORES)
        if cargador.datos is None: sys.exit("Error carga datos")
        cargador.preprocesar_datos()
        datos_limpios = cargador.obtener_datos_limpiados()
        if datos_limpios is None or datos_limpios.empty: sys.exit("Error preprocesamiento")
        print(" -> Datos cargados y preprocesados.")
        datos_limpios_con_tm = datos_limpios.copy()
    except Exception as e: sys.exit(f"Error Paso 1: {e}")

    # --- PASO 2: Cálculo de Indicadores ---
    print("\n[PASO 2] Calculando Indicadores de Desempeño...")
    datos_con_metricas_idx = None
    try:
        calculador = IndicadoresDesempeño(datos_limpios)
        datos_con_metricas_df = calculador.calcular_metricas()
        if datos_con_metricas_df is None or datos_con_metricas_df.empty: sys.exit("Error cálculo métricas")
        if METRICAS_REFERENCIA['defensiva'] not in datos_con_metricas_df.columns: print(f"ADVERTENCIA: Métrica defensiva '{METRICAS_REFERENCIA['defensiva']}' no encontrada.")
        if 'Player' in datos_con_metricas_df.columns: datos_con_metricas_idx = datos_con_metricas_df.set_index('Player')
        elif datos_con_metricas_df.index.name == 'Player': datos_con_metricas_idx = datos_con_metricas_df
        else: temp_df=datos_con_metricas_df.reset_index(); datos_con_metricas_idx=temp_df.set_index('Player') if 'Player' in temp_df.columns else sys.exit("Error índice Player")
        print(" -> Indicadores calculados.")
    except Exception as e: sys.exit(f"Error Paso 2: {e}")

    # --- PASO 3: Selección de Métrica Principal ---
    print("\n[PASO 3] Selección de Métrica Principal...")
    opciones_validas_usuario = {}
    print("Elige el enfoque para optimizar:")
    for num, clave in OPCIONES_USUARIO.items():
        metrica = METRICAS_REFERENCIA.get(clave)
        if metrica and metrica in datos_con_metricas_idx.columns and pd.api.types.is_numeric_dtype(datos_con_metricas_idx[metrica]):
            print(f"  {num}: {clave.capitalize()} ('{metrica}')")
            opciones_validas_usuario[num] = clave
        else: print(f"  {num}: {clave.capitalize()} (NO DISPONIBLE)")
    if not opciones_validas_usuario: sys.exit("Error: Ninguna métrica principal válida.")
    metrica_principal = None
    while metrica_principal is None:
        try:
            choice = int(input(f"Ingresa número ({', '.join(map(str, opciones_validas_usuario.keys()))}): "))
            if choice in opciones_validas_usuario:
                metrica_principal = METRICAS_REFERENCIA[opciones_validas_usuario[choice]]
                print(f" -> Optimizando por: '{metrica_principal}'")
            else: print("Número no válido.")
        except ValueError: print("Entrada inválida.")

    # --- PASO 4: Optimización y Visualización Básica ---
    print(f"\n[PASO 4] Optimizando Alineación para '{metrica_principal}'...")
    quinteto_optimo_df = None; valor_optimo_titulares = None; suplentes_optimo_dict = None; optimizador = None
    try:
        optimizador = OptimizadorAlineacion(datos_con_metricas_idx, min_g=MIN_G, min_mp_total=MIN_MP_TOTAL)
        quinteto_optimo_df, valor_optimo_titulares, suplentes_optimo_dict = optimizador.optimizar_quinteto(metrica_objetivo=metrica_principal)
        if quinteto_optimo_df is not None and valor_optimo_titulares is not None and suplentes_optimo_dict is not None:
            print(" -> Optimización completada.")
            # <<< MANTENER LA VISUALIZACIÓN DE LA ALINEACIÓN GENERADA >>>
            optimizador.visualizar_alineacion_completa(quinteto_optimo_df, valor_optimo_titulares, metrica_principal, suplentes_optimo_dict)
            if 'Player' not in quinteto_optimo_df.columns and quinteto_optimo_df.index.name == 'Player': quinteto_optimo_df = quinteto_optimo_df.reset_index()
        else: print(" -> No se pudo generar la alineación completa.")
    except Exception as e: print(f"Error Paso 4: {e}")

    # --- PASO 5: Carga de Alineaciones Reales ---
    print("\n[PASO 5] Cargando Alineaciones Reales...")
    df_reales = None
    try:
        df_reales = pd.read_csv(ARCHIVO_REALES)
        expected_cols = ['Tm', 'Player1', 'Player2', 'Player3', 'Player4', 'Player5']
        if not all(col in df_reales.columns for col in expected_cols): print("Advertencia: Formato incorrecto archivo reales."); df_reales = None
        elif df_reales.empty: print("Advertencia: Archivo reales vacío."); df_reales = None
        else: print(f" -> {len(df_reales)} alineaciones reales cargadas.")
    except FileNotFoundError: print(f"Advertencia: Archivo reales no encontrado en '{datos_dir}'.")
    except Exception as e: print(f"Error carga reales: {e}")

    # --- PASO 6: Análisis (Ejecución interna, impresión controlada) ---
    print("\n[PASO 6] Realizando Análisis...")
    if quinteto_optimo_df is None or valor_optimo_titulares is None or optimizador is None:
        print(" -> Omitiendo análisis (falta quinteto óptimo u optimizador).")
    else:
        try:
            metricas_comp_real_existentes = [m for m in METRICAS_COMPARACION if m in datos_con_metricas_idx.columns]
            metricas_vis_existentes = [m for m in METRICAS_COMPARACION_VISUAL if m in datos_con_metricas_idx.columns]
            metricas_sens_existentes = {n: m for n, m in METRICAS_SENSIBILIDAD.items() if m in datos_con_metricas_idx.columns}

            analizador = AnalisisResultados(
                datos_con_metricas=datos_con_metricas_idx, metrica_principal=metrica_principal,
                quinteto_optimo_df=quinteto_optimo_df, valor_optimo_titulares=valor_optimo_titulares,
                df_reales=df_reales, optimizador=optimizador, datos_limpios_con_tm=datos_limpios_con_tm
            )

            # 6.a) Comparación Numérica (Ejecutar pero no imprimir tabla aquí)
            if df_reales is not None and metricas_comp_real_existentes:
                print(" -> Ejecutando comparación numérica...")
                # La impresión de la tabla detallada se comentó dentro del método
                analizador.ejecutar_comparacion_optimo_vs_reales(metricas_comp_real_existentes)
            # else: # Mensajes de omisión ya manejados

            # 6.b) Análisis de Sensibilidad (Ejecutar pero no imprimir detalles aquí)
            if metricas_sens_existentes:
                print(" -> Ejecutando análisis de sensibilidad...")
                # La impresión detallada se comentó dentro del método
                analizador.ejecutar_analisis_sensibilidad(metricas_sens_existentes)
            # else: # Mensajes de omisión ya manejados

            # 6.c) Visualización Gráfica (Omitida)
            # analizador.generar_visualizaciones() # LLAMADA ELIMINADA

            # 6.d) Visualización Comparativa Estilo FIFA (MANTENER)
            if df_reales is not None and metricas_vis_existentes:
                # La impresión se hace DENTRO de este método
                analizador.visualizar_comparacion_fifa_style(metricas_vis_existentes)
            elif df_reales is None: print("\n--- Omitiendo Comparación Visual (datos reales no disponibles) ---")
            else: print("\n--- Omitiendo Comparación Visual (métricas no disponibles) ---")

        except Exception as e: print(f"Error inesperado durante el análisis: {e}")

    print("\n--- Proceso Finalizado ---")

if __name__ == "__main__":
    main()

# --- FIN DEL ARCHIVO main.py (ubicado en src/) ---