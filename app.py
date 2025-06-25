

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from collections import defaultdict

# --- Configuración de Paths ---
# Añade la carpeta 'src' al path para que Python pueda encontrar las clases del backend.
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)
datos_dir = os.path.join(script_dir, 'Datos')
upload_folder = os.path.join(script_dir, 'uploads')  # Carpeta para guardar archivos subidos
if not os.path.exists(upload_folder): os.makedirs(upload_folder)
archivo_reales_path = os.path.join(datos_dir, "ruta_reales_csv.csv")

# --- Importar Clases del Backend ---
# Intenta importar todas las clases necesarias. Si falla, el programa no puede funcionar.
try:
    from CargaDatos import CargaDatos
    from IndicadoresDesempeño import IndicadoresDesempeño
    from OptimizadorAlineacion import OptimizadorAlineacion
    from AnalisisResultados import AnalisisResultados

    print("INFO: Clases del backend parecen estar accesibles.")
except ImportError as e:
    sys.exit(f"Error CRÍTICO: Importación clase backend: {e}")

# --- Configuración de Flask ---
app = Flask(__name__)  # Inicializa la aplicación Flask
app.config['UPLOAD_FOLDER'] = upload_folder  # Configura la carpeta de subidas
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Límite de tamaño de archivo (16MB)

# --- Configuración Subida Archivos ---
ALLOWED_EXTENSIONS = {'csv'}  # Solo permite archivos .csv


def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Mapeo de Métricas ---
# Diccionarios para traducir las opciones del usuario a las métricas reales del backend.
METRICAS_REFERENCIA = {
    'ofensiva': 'PTS_Total', 'defensiva': 'DEF_VOLUME_Total', 'equilibrada': 'EFF/MIN',
    'eficiencia_total': 'EFF', 'rating_ofensivo': 'Off_Rating_Simple'
}
OPCIONES_USUARIO_MAP = {'1': 'ofensiva', '2': 'defensiva', '3': 'equilibrada'}
METRICAS_COMPARACION = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total', 'EFF',
                        'EFF/MIN', 'Off_Rating_Simple', 'Net_Rating_Simple']
METRICAS_COMPARACION_VISUAL = ['PTS_Total', 'AST_Total', 'TRB_Total', 'STL_Total', 'BLK_Total', 'DEF_VOLUME_Total',
                               'EFF']
METRICAS_SENSIBILIDAD = {
    'Ofensivo (Puntos)': 'PTS_Total', 'Defensivo (Volumen)': 'DEF_VOLUME_Total',
    'Equilibrado (EFF/MIN)': 'EFF/MIN', 'Eficiencia Total (EFF)': 'EFF',
    'Rating Ofensivo Simple': 'Off_Rating_Simple'
}


# --- Rutas de la Aplicación ---

@app.route('/')
def pagina_carga():
    """Ruta para la página principal, que muestra el formulario de subida."""
    print("INFO: Accediendo a la página de carga ('/')")
    return render_template('upload.html')


@app.route('/procesar', methods=['POST'])
def procesar_datos():
    """Ruta que maneja la subida del archivo y ejecuta todo el proceso de análisis."""
    print("INFO: Recibida petición POST en /procesar")

    # 1. Validar que el archivo se ha subido correctamente
    if 'archivo_jugadores' not in request.files:
        flash('Error: No se encontró el campo del archivo.', 'error')
        return redirect(url_for('pagina_carga'))
    file = request.files['archivo_jugadores']
    if file.filename == '':
        flash('Error: Ningún archivo seleccionado.', 'error')
        return redirect(url_for('pagina_carga'))

    # 2. Guardar el archivo en el servidor si es un .csv válido
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            print(f"INFO: Archivo '{filename}' guardado en '{filepath}'")

            # 3. Recoger los parámetros del formulario (filtros y métrica)
            try:
                min_g = int(request.form.get('min_g', 20))
                min_mp_total = int(request.form.get('min_mp_total', 500))
                metrica_choice_num = request.form.get('metrica_choice', '3')
            except ValueError:
                flash('Error: Valores inválidos para los filtros.', 'error')
                return redirect(url_for('pagina_carga'))

            clave_enfoque = OPCIONES_USUARIO_MAP.get(metrica_choice_num, 'equilibrada')
            metrica_principal = METRICAS_REFERENCIA.get(clave_enfoque, 'EFF/MIN')
            enfoque_desc = clave_enfoque.capitalize()
            print(f"INFO: Parámetros - G>={min_g}, MP_Total>={min_mp_total}, Enfoque: {enfoque_desc}")

            # 4. --- EJECUCIÓN DE TODA LA LÓGICA DEL BACKEND ---
            # Inicializa todas las variables que se pasarán a la plantilla de resultados
            error_procesamiento = None
            quinteto_opt_df, valor_optimo, suplentes_dict, suplentes_df = None, None, None, None
            jaccard_promedio, mejora_promedio_mp, equipos_superados, total_comparados_validos_mp = None, None, None, None
            jugadores_robustos = {}
            comparacion_visual_data = None

            try:
                # Ejecuta la secuencia: Carga -> Cálculo de Métricas -> Optimización
                print("Backend: Cargando y Calculando...")
                cargador = CargaDatos();
                cargador.cargar_datos(filepath)
                cargador.preprocesar_datos();
                datos_limpios = cargador.obtener_datos_limpiados()
                calculador = IndicadoresDesempeño(datos_limpios);
                datos_con_metricas_df = calculador.calcular_metricas()
                datos_con_metricas_idx = datos_con_metricas_df.set_index('Player')

                print(f"Backend: Optimizando para '{metrica_principal}'...")
                optimizador = OptimizadorAlineacion(datos_con_metricas_idx, min_g=min_g, min_mp_total=min_mp_total)
                quinteto_opt_df, valor_optimo, suplentes_dict = optimizador.optimizar_quinteto(
                    metrica_objetivo=metrica_principal)

                # Prepara el DataFrame de suplentes para mostrarlo en la tabla
                if suplentes_dict:
                    nombres_suplentes = [j for j in suplentes_dict.values() if j and j != 'N/A']
                    if nombres_suplentes:
                        cols_mostrar_sup = [c for c in METRICAS_COMPARACION if c in datos_con_metricas_idx.columns]
                        suplentes_df = datos_con_metricas_idx.loc[nombres_suplentes, cols_mostrar_sup].reset_index()
                        suplentes_df = suplentes_df.sort_values(by=metrica_principal, ascending=False)

                # Carga las alineaciones reales (si el archivo existe)
                df_reales = pd.read_csv(archivo_reales_path) if os.path.exists(archivo_reales_path) else None

                # Ejecuta el análisis de resultados si la optimización fue exitosa
                if quinteto_opt_df is not None and optimizador is not None:
                    analizador = AnalisisResultados(
                        datos_con_metricas=datos_con_metricas_idx, metrica_principal=metrica_principal,
                        quinteto_optimo_df=quinteto_opt_df.set_index('Player'), valor_optimo_titulares=valor_optimo,
                        df_reales=df_reales, optimizador=optimizador
                    )

                    # Ejecuta la comparación numérica y extrae un resumen
                    if df_reales is not None:
                        df_comparacion_num = analizador.ejecutar_comparacion_optimo_vs_reales(METRICAS_COMPARACION)
                        if df_comparacion_num is not None:
                            jaccard_promedio = df_comparacion_num['Jaccard'].mean()
                            mejora_col = f"{metrica_principal}_Mejora"
                            if mejora_col in df_comparacion_num.columns:
                                data = df_comparacion_num[mejora_col].dropna()
                                mejora_promedio_mp = data.mean();
                                equipos_superados = (data > 1e-9).sum();
                                total_comparados_validos_mp = len(data)

                        # Prepara los datos para el gráfico 'estilo FIFA'
                        comparacion_visual_data = preparar_datos_comparacion_visual(analizador,
                                                                                    METRICAS_COMPARACION_VISUAL)

                    # Ejecuta el análisis de sensibilidad para encontrar jugadores 'robustos'
                    resultados_sens = analizador.ejecutar_analisis_sensibilidad(METRICAS_SENSIBILIDAD)
                    if resultados_sens:
                        apariciones = defaultdict(int)
                        for quinteto in resultados_sens.values():
                            if quinteto:
                                for j in quinteto: apariciones[j] += 1
                        temp_robustos = {j: c for j, c in apariciones.items() if c > 1}
                        jugadores_robustos = dict(sorted(temp_robustos.items(), key=lambda item: -item[1]))

            except Exception as e_backend:
                # Captura cualquier error del backend para mostrarlo al usuario
                error_procesamiento = str(e_backend)

            # 5. Renderizar la página de resultados con todos los datos calculados
            print("INFO: Renderizando página de resultados...")
            return render_template('results.html',
                                   metrica_principal=metrica_principal, enfoque_desc=enfoque_desc,
                                   quinteto_opt_df=quinteto_opt_df, valor_optimo=valor_optimo,
                                   suplentes_df=suplentes_df,
                                   comparacion_visual_data=comparacion_visual_data,
                                   jaccard_promedio=jaccard_promedio,
                                   mejora_promedio_mp=mejora_promedio_mp,
                                   equipos_superados=equipos_superados,
                                   total_comparados_validos_mp=total_comparados_validos_mp,
                                   jugadores_robustos=jugadores_robustos,
                                   error=error_procesamiento)

        except Exception as e_outer:
            flash(f'Error inesperado en el servidor: {e_outer}', 'error')
            return redirect(url_for('pagina_carga'))
    else:
        flash('Error: Tipo de archivo no permitido (solo .csv).', 'error')
        return redirect(url_for('pagina_carga'))


def preparar_datos_comparacion_visual(analizador, metricas_visual):
    """Función auxiliar que adapta los datos de comparación a un formato que la plantilla HTML pueda usar."""
    # Esta función replica la lógica de normalización de AnalisisResultados,
    # pero devuelve los datos en una estructura de diccionario/lista para Jinja2.
    if analizador.df_reales is None or not analizador.metricas_titulares_optimo: return None

    # ... (código de cálculo de métricas reales y min/max global) ...
    metricas_validas = [m for m in metricas_visual if m in analizador.datos_metricas.columns]
    if not metricas_validas: return None
    metricas_reales_todos = {}  # Calcula métricas para todos los equipos reales
    for index, row_real in analizador.df_reales.iterrows():
        # ...
        equipo_tm = row_real.get('Tm', f"Equipo_{index + 1}")
        jugadores_reales_list = [row_real[f'Player{i}'] for i in range(1, 6)]
        metricas_equipo = analizador._calcular_metricas_quinteto(jugadores_reales_list, metricas_validas)
        metricas_reales_todos[equipo_tm] = metricas_equipo

    min_max_global = {}  # Encuentra min/max global para normalizar
    for metrica in metricas_validas:
        # ...
        valores = [analizador.metricas_titulares_optimo.get(metrica)]
        for data_equipo in metricas_reales_todos.values():
            valores.append(data_equipo.get(metrica))
        valores = [v for v in valores if pd.notna(v)]
        if valores:
            min_val = min(valores);
            max_val = max(valores)
            if max_val > min_val: min_max_global[metrica] = {'min': min_val, 'max': max_val}

    def normalizar_local(valor, metrica):  # Función de normalización
        # ...
        if metrica not in min_max_global or pd.isna(valor): return 0
        stats = min_max_global[metrica];
        min_v, max_v = stats['min'], stats['max']
        denominador = max_v - min_v
        if denominador <= 1e-9: return 0
        norm_val = ((float(valor) - min_v) / denominador) * 100
        return max(0, min(100, int(round(norm_val))))

    # Formatea los datos de salida
    output_data = {}
    for equipo_tm, metricas_real in metricas_reales_todos.items():
        equipo_data = []
        for metrica in metricas_validas:
            if metrica in min_max_global:
                val_opt = analizador.metricas_titulares_optimo.get(metrica)
                val_real = metricas_real.get(metrica)
                norm_opt = normalizar_local(val_opt, metrica)
                norm_real = normalizar_local(val_real, metrica)
                equipo_data.append((metrica, norm_opt, norm_real))
        if equipo_data: output_data[equipo_tm] = equipo_data
    return output_data


# --- Ejecutar la Aplicación ---
if __name__ == '__main__':
    """Punto de entrada para ejecutar el servidor Flask."""
    print("INFO: Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5001, debug=True)