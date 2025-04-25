# --- INICIO DEL ARCHIVO app.py ---

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from collections import defaultdict

# --- Configuración de Paths ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)
datos_dir = os.path.join(script_dir, 'Datos')
upload_folder = os.path.join(script_dir, 'uploads')
if not os.path.exists(upload_folder): os.makedirs(upload_folder)
archivo_reales_path = os.path.join(datos_dir, "ruta_reales_csv.csv")

# --- Importar Clases del Backend ---
try:
    from CargaDatos import CargaDatos
    from IndicadoresDesempeño import IndicadoresDesempeño
    from OptimizadorAlineacion import OptimizadorAlineacion
    from AnalisisResultados import AnalisisResultados
    print("INFO: Clases del backend parecen estar accesibles.")
except ImportError as e: sys.exit(f"Error CRÍTICO: Importación clase backend: {e}")
except Exception as e: sys.exit(f"Error CRÍTICO: Otro error importación clases: {e}")

# --- Configuración de Flask ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = upload_folder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'tu_clave_secreta_super_segura_aqui_v7' # ¡Cambia esto!

# --- Configuración Subida Archivos ---
ALLOWED_EXTENSIONS = {'csv'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Mapeo de Métricas ---
METRICAS_REFERENCIA = {
    'ofensiva': 'PTS_Total', 'defensiva': 'DEF_VOLUME_Total', 'equilibrada': 'EFF/MIN',
    'eficiencia_total': 'EFF', 'rating_ofensivo': 'Off_Rating_Simple'
}
OPCIONES_USUARIO_MAP = { '1': 'ofensiva', '2': 'defensiva', '3': 'equilibrada'}
METRICAS_COMPARACION = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total', 'EFF', 'EFF/MIN', 'Off_Rating_Simple', 'Net_Rating_Simple'] # Para cálculo numérico
METRICAS_COMPARACION_VISUAL = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total', 'EFF'] # Para gráfico FIFA
METRICAS_SENSIBILIDAD = {
    'Ofensivo (Puntos)': 'PTS_Total', 'Defensivo (Volumen)': 'DEF_VOLUME_Total',
    'Equilibrado (EFF/MIN)': 'EFF/MIN', 'Eficiencia Total (EFF)': 'EFF',
    'Rating Ofensivo Simple': 'Off_Rating_Simple'
}

# --- Rutas de la Aplicación ---

@app.route('/')
def pagina_carga():
    print("INFO: Accediendo a la página de carga ('/')")
    return render_template('upload.html')

@app.route('/procesar', methods=['POST'])
def procesar_datos():
    print("INFO: Recibida petición POST en /procesar")

    if 'archivo_jugadores' not in request.files:
        flash('Error: No se encontró el campo del archivo.', 'error')
        return redirect(url_for('pagina_carga'))
    file = request.files['archivo_jugadores']
    if file.filename == '':
        flash('Error: Ningún archivo seleccionado.', 'error')
        return redirect(url_for('pagina_carga'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            print(f"INFO: Archivo '{filename}' guardado en '{filepath}'")

            try:
                min_g = int(request.form.get('min_g', 20))
                min_mp_total = int(request.form.get('min_mp_total', 500))
                metrica_choice_num = request.form.get('metrica_choice', '3')
                if min_g < 0 or min_mp_total < 0: raise ValueError("Valores negativos no permitidos")
            except ValueError as e:
                flash(f'Error: Valores inválidos para filtros: {e}', 'error')
                return redirect(url_for('pagina_carga'))

            clave_enfoque = OPCIONES_USUARIO_MAP.get(metrica_choice_num, 'equilibrada')
            metrica_principal = METRICAS_REFERENCIA.get(clave_enfoque, 'EFF/MIN')
            enfoque_desc = clave_enfoque.capitalize()
            print(f"INFO: Parámetros - G>={min_g}, MP_Total>={min_mp_total}, Enfoque: {enfoque_desc} ({metrica_principal})")

            # ******** INICIO EJECUCIÓN LÓGICA BACKEND ********
            datos_con_metricas_idx = None; quinteto_opt_df = None; valor_optimo = None
            suplentes_dict = None; suplentes_df = None; comparacion_visual_data = None
            jugadores_robustos = {}; error_procesamiento = None; optimizador = None; analizador = None
            df_comparacion_num = None; jaccard_promedio = None; mejora_promedio_mp = None
            equipos_superados = None; total_comparados_validos_mp = None

            try:
                # PASOS A, B, C (Carga, Métricas, Optimización)
                print("Backend: Cargando y Calculando...")
                cargador=CargaDatos(); cargador.cargar_datos(filepath)
                if cargador.datos is None: raise ValueError("Error carga CSV.")
                cargador.preprocesar_datos(); datos_limpios = cargador.obtener_datos_limpiados()
                if datos_limpios is None or datos_limpios.empty: raise ValueError("Error preproc.")
                calculador=IndicadoresDesempeño(datos_limpios); datos_con_metricas_df = calculador.calcular_metricas()
                if datos_con_metricas_df is None: raise ValueError("Error cálculo métricas.")
                if 'Player' in datos_con_metricas_df.columns: datos_con_metricas_idx = datos_con_metricas_df.set_index('Player')
                elif datos_con_metricas_df.index.name == 'Player': datos_con_metricas_idx = datos_con_metricas_df
                else: temp_df=datos_con_metricas_df.reset_index(); datos_con_metricas_idx=temp_df.set_index('Player') if 'Player' in temp_df.columns else sys.exit("Error índice.")
                if metrica_principal not in datos_con_metricas_idx.columns: raise ValueError(f"Métrica '{metrica_principal}' no encontrada.")
                print(f"Backend: Optimizando para '{metrica_principal}'...")
                optimizador = OptimizadorAlineacion(datos_con_metricas_idx, min_g=min_g, min_mp_total=min_mp_total)
                quinteto_opt_df, valor_optimo, suplentes_dict = optimizador.optimizar_quinteto(metrica_objetivo=metrica_principal)

                # Preparar DF suplentes
                if suplentes_dict:
                    nombres_suplentes = [j for j in suplentes_dict.values() if j and j != 'N/A']
                    if nombres_suplentes:
                        kpis_mostrar_sup_inicial = [metrica_principal,'Pos','G','MP_Total','PTS_Total','AST_Total','TRB_Total','DEF_VOLUME_Total','EFF']
                        kpis_unicos = list(dict.fromkeys(kpis_mostrar_sup_inicial))
                        cols_mostrar_sup = [c for c in kpis_unicos if c in datos_con_metricas_idx.columns]
                        if cols_mostrar_sup:
                            try:
                                temp_sdf = datos_con_metricas_idx.loc[nombres_suplentes, cols_mostrar_sup]
                                suplentes_df = temp_sdf.reset_index() if temp_sdf.index.name == 'Player' else temp_sdf
                                if metrica_principal in suplentes_df.columns: suplentes_df = suplentes_df.sort_values(by=metrica_principal, ascending=False)
                                elif 'EFF' in suplentes_df.columns: suplentes_df = suplentes_df.sort_values(by='EFF', ascending=False)
                            except KeyError as ke: print(f"Adv: Suplentes no hallados: {ke}"); suplentes_df = None

                # PASO D: Cargar Reales
                print("Backend: Cargando datos reales...")
                df_reales = None
                try:
                    df_reales = pd.read_csv(archivo_reales_path)
                    expected_cols = ['Tm', 'Player1', 'Player2', 'Player3', 'Player4', 'Player5']
                    if not all(col in df_reales.columns for col in expected_cols) or df_reales.empty: df_reales = None
                except Exception as e: print(f"Error/Adv carga reales: {e}"); df_reales = None

                # PASO E, F, G: Instanciar Analizador, Comparaciones y Sensibilidad
                if quinteto_opt_df is not None and optimizador is not None:
                    quinteto_temp_analisis = quinteto_opt_df.copy()
                    if 'Player' not in quinteto_temp_analisis.columns:
                        if quinteto_temp_analisis.index.name == 'Player': quinteto_temp_analisis = quinteto_temp_analisis.reset_index()
                        else: raise ValueError("Falta 'Player' en quinteto óptimo.")

                    analizador = AnalisisResultados(
                         datos_con_metricas=datos_con_metricas_idx, metrica_principal=metrica_principal,
                         quinteto_optimo_df=quinteto_temp_analisis, valor_optimo_titulares=valor_optimo,
                         df_reales=df_reales, optimizador=optimizador
                     )

                    # G: Comparación Numérica y Resumen
                    if df_reales is not None:
                        print("Backend: Ejecutando comparación numérica...")
                        metricas_comp_real_existentes = [m for m in METRICAS_COMPARACION if m in datos_con_metricas_idx.columns and pd.api.types.is_numeric_dtype(datos_con_metricas_idx[m])]
                        if metricas_comp_real_existentes:
                             try:
                                 df_comparacion_num = analizador.ejecutar_comparacion_optimo_vs_reales(metricas_comp_real_existentes)
                                 if df_comparacion_num is not None and not df_comparacion_num.empty:
                                     if 'Jaccard' in df_comparacion_num.columns: jaccard_promedio = df_comparacion_num['Jaccard'].mean()
                                     mejora_col = f"{metrica_principal}_Mejora"
                                     if mejora_col in df_comparacion_num.columns:
                                         data = df_comparacion_num[mejora_col].dropna()
                                         if not data.empty:
                                             mejora_promedio_mp = data.mean(); equipos_superados = (data > 1e-9).sum(); total_comparados_validos_mp = len(data)
                                     print("Backend: Resumen numérico calculado.")
                             except Exception as e_comp: print(f"Error en comp. numérica: {e_comp}")

                    # E: Preparar Comparación Visual
                    if df_reales is not None:
                        print("Backend: Preparando comparación visual...")
                        comparacion_visual_data = preparar_datos_comparacion_visual(analizador, METRICAS_COMPARACION_VISUAL)
                        print("Backend: Datos visuales listos.")

                    # F: Ejecutar Análisis de Sensibilidad
                    print("Backend: Ejecutando análisis de sensibilidad...")
                    metricas_sens_existentes = {n: m for n, m in METRICAS_SENSIBILIDAD.items() if m in datos_con_metricas_idx.columns and pd.api.types.is_numeric_dtype(datos_con_metricas_idx[m])}
                    if metricas_sens_existentes:
                        try:
                            resultados_sens = analizador.ejecutar_analisis_sensibilidad(metricas_sens_existentes)
                            if resultados_sens:
                                apariciones = defaultdict(int)
                                for quinteto in resultados_sens.values():
                                    if quinteto and isinstance(quinteto, list) and len(quinteto) == 5:
                                        for j in [str(p) for p in quinteto]: apariciones[j] += 1
                                temp_robustos = {j: c for j, c in apariciones.items() if c > 1}
                                jugadores_robustos = dict(sorted(temp_robustos.items(), key=lambda item: (-item[1], item[0])))
                                print(f"Backend: Jugadores robustos encontrados: {len(jugadores_robustos)}")
                        except Exception as e_sens: print(f"Error en sensibilidad: {e_sens}")
                    else: print("Backend: Sin métricas para sensibilidad.")
                else: print("Backend: Omitiendo Análisis (falta óptimo u optimizador).")

            except Exception as e_backend:
                print(f"Error durante el procesamiento backend: {e_backend}")
                error_procesamiento = str(e_backend)
            # ******** FIN EJECUCIÓN LÓGICA BACKEND ********

            # Renderizar plantilla
            print("INFO: Renderizando página de resultados...")
            return render_template('results.html',
                                   metrica_principal=metrica_principal, enfoque_desc=enfoque_desc,
                                   quinteto_opt_df=quinteto_opt_df, valor_optimo=valor_optimo,
                                   suplentes_dict=suplentes_dict, suplentes_df=suplentes_df,
                                   comparacion_visual_data=comparacion_visual_data,
                                   # Nuevas variables para resumen numérico
                                   jaccard_promedio=jaccard_promedio,
                                   mejora_promedio_mp=mejora_promedio_mp,
                                   equipos_superados=equipos_superados,
                                   total_comparados_validos_mp=total_comparados_validos_mp,
                                   # Variable para robustos
                                   jugadores_robustos=jugadores_robustos,
                                   error=error_procesamiento)

        except Exception as e_outer:
            print(f"Error general en /procesar: {e_outer}")
            flash(f'Error inesperado en el servidor: {e_outer}', 'error')
            return redirect(url_for('pagina_carga'))
    else:
        flash('Error: Tipo de archivo no permitido (solo .csv).', 'error')
        return redirect(url_for('pagina_carga'))


# --- Función Auxiliar para preparar datos de Comparación Visual ---
# (Sin cambios)
def preparar_datos_comparacion_visual(analizador, metricas_visual):
    if analizador.df_reales is None or analizador.df_reales.empty or not analizador.metricas_titulares_optimo: return None
    metricas_validas = [m for m in metricas_visual if m in analizador.datos_metricas.columns and pd.api.types.is_numeric_dtype(analizador.datos_metricas[m])]
    if not metricas_validas: return None
    metricas_reales_todos = {}
    col_jugadores_reales_names = [c for c in analizador.df_reales.columns if c.startswith('Player')]
    if len(col_jugadores_reales_names) != 5: return None
    for index, row_real in analizador.df_reales.iterrows():
        equipo_tm = row_real.get('Tm', f"Equipo_{index+1}")
        jugadores_reales_list = list(row_real[col_jugadores_reales_names].dropna().astype(str))
        if len(jugadores_reales_list) == 5:
            metricas_equipo = analizador._calcular_metricas_quinteto(jugadores_reales_list, metricas_validas)
            if metricas_equipo and any(v is not None for v in metricas_equipo.values()):
                metricas_reales_todos[equipo_tm] = metricas_equipo
    if not metricas_reales_todos: return None
    min_max_global = {}
    for metrica in metricas_validas:
        valores = []
        valor_optimo = analizador.metricas_titulares_optimo.get(metrica)
        if pd.notna(valor_optimo): valores.append(valor_optimo)
        for data_equipo in metricas_reales_todos.values():
            valor_real = data_equipo.get(metrica)
            if pd.notna(valor_real): valores.append(valor_real)
        if valores:
            min_val = min(valores); max_val = max(valores)
            if max_val > min_val: min_max_global[metrica] = {'min': min_val, 'max': max_val}
    def normalizar_local(valor, metrica):
        if metrica not in min_max_global or pd.isna(valor): return 0
        stats = min_max_global[metrica]; min_v = stats['min']; max_v = stats['max']
        if pd.isna(min_v) or pd.isna(max_v): return 0
        try: valor_f = float(valor); min_v_f = float(min_v); max_v_f = float(max_v)
        except (TypeError, ValueError): return 0
        denominador = max_v_f - min_v_f
        if denominador <= 1e-9: return 0 if abs(valor_f - min_v_f) < 1e-9 else 100
        norm_val = ((valor_f - min_v_f) / denominador) * 100
        resultado_int = int(round(norm_val))
        return max(0, min(100, resultado_int))
    output_data = {}
    for equipo_tm, metricas_real in metricas_reales_todos.items():
        equipo_data = []
        for metrica in metricas_validas:
            if metrica in min_max_global:
                val_opt = analizador.metricas_titulares_optimo.get(metrica); val_real = metricas_real.get(metrica)
                norm_opt = normalizar_local(val_opt, metrica); norm_real = normalizar_local(val_real, metrica)
                equipo_data.append( (metrica, norm_opt, norm_real) )
        if equipo_data: output_data[equipo_tm] = equipo_data
    return output_data

# --- Ejecutar la Aplicación ---
if __name__ == '__main__':
    print("INFO: Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5001, debug=True)

# --- FIN DEL ARCHIVO app.py ---