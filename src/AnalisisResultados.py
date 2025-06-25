# --- INICIO DEL ARCHIVO AnalisisResultados.py ---

import pandas as pd
from collections import defaultdict
import numpy as np  # Importar numpy


class AnalisisResultados:
    """
    Realiza y presenta análisis comparativos de la alineación ÓPTIMA
    (vs. realidad) y análisis de sensibilidad.
    """

    def __init__(self,
                 datos_con_metricas,  # DataFrame con Player como índice
                 metrica_principal,  # Str: Métrica usada en optimización principal
                 quinteto_optimo_df,  # DataFrame o None (solo TITULARES)
                 valor_optimo_titulares,  # Float o None (valor de los TITULARES)
                 df_reales=None,  # DataFrame o None (alineaciones reales)
                 optimizador=None,  # Instancia de OptimizadorAlineacion para rehacer sensibilidad
                 datos_limpios_con_tm=None):  # Para añadir Tm si falta (opcional)
        """
        Inicializa con los datos y resultados necesarios (enfocado en el óptimo titular).
        """
        # Valida que los datos de entrada sean correctos
        if datos_con_metricas is None or datos_con_metricas.empty: raise ValueError("datos_con_metricas vacío.")
        if datos_con_metricas.index.name != 'Player': raise ValueError(
            "datos_con_metricas necesita Player como índice.")

        # Asigna los argumentos a los atributos de la clase
        self.datos_metricas = datos_con_metricas.copy()
        self.metrica_principal = metrica_principal
        self.quinteto_optimo_df = quinteto_optimo_df
        self.valor_optimo_titulares = valor_optimo_titulares
        self.df_reales = df_reales
        self.optimizador = optimizador
        self.datos_limpios_con_tm = datos_limpios_con_tm
        self.resultados_sensibilidad = {}

        # Pre-calcula la suma de métricas para el quinteto óptimo
        self.metricas_titulares_optimo = None
        if self.quinteto_optimo_df is not None and not self.quinteto_optimo_df.empty:
            df_temp_opt = self.quinteto_optimo_df.copy()
            # Busca la columna 'Player' para obtener la lista de jugadores
            player_col_present = 'Player' in df_temp_opt.columns
            player_idx_present = df_temp_opt.index.name == 'Player'
            if not player_col_present and player_idx_present:
                df_temp_opt = df_temp_opt.reset_index()
                player_col_present = True

            # Si se encuentra la lista de jugadores, calcula sus métricas sumadas
            if player_col_present:
                jugadores_optimos_tit = df_temp_opt['Player'].tolist()
                if len(jugadores_optimos_tit) == 5:
                    metricas_numericas_disponibles = [c for c in self.datos_metricas.columns if
                                                      pd.api.types.is_numeric_dtype(self.datos_metricas[c])]
                    self.metricas_titulares_optimo = self._calcular_metricas_quinteto(jugadores_optimos_tit,
                                                                                      metricas_numericas_disponibles)
                    # Si el cálculo falla, lo deja como None
                    if not self.metricas_titulares_optimo or not any(
                            v is not None for v in self.metricas_titulares_optimo.values()):
                        self.metricas_titulares_optimo = None
                else:
                    self.metricas_titulares_optimo = None
            else:
                self.metricas_titulares_optimo = None

        print("AnalisisResultados inicializado (enfocado en óptimo titular).")

    def _calcular_metricas_quinteto(self, quinteto_jugadores, metricas_a_calcular):
        """Calcula la SUMA de varias métricas para una lista de jugadores."""
        resultados = {m: None for m in metricas_a_calcular}
        # Comprueba si la lista es un quinteto válido
        if not quinteto_jugadores or len(quinteto_jugadores) != 5: return resultados
        jugadores_validos_en_datos = [p for p in quinteto_jugadores if p in self.datos_metricas.index]
        if len(jugadores_validos_en_datos) != 5: return resultados

        # Filtra solo las métricas que se pueden sumar
        metricas_existentes = [m for m in metricas_a_calcular if m in self.datos_metricas.columns]
        metricas_calculables = [m for m in metricas_existentes if pd.api.types.is_numeric_dtype(self.datos_metricas[m])]
        if not metricas_calculables: return resultados

        try:
            # Selecciona los datos y calcula la suma
            datos_filtrados = self.datos_metricas.loc[jugadores_validos_en_datos, metricas_calculables]
            sumas = datos_filtrados.sum(numeric_only=True, skipna=True)
            for metrica in metricas_calculables:
                valor_suma = sumas.get(metrica)
                if pd.isna(valor_suma):
                    resultados[metrica] = None
                else:
                    resultados[metrica] = valor_suma
            return resultados
        except KeyError as e:
            print(f"Error KeyError: {e}"); return {m: None for m in metricas_a_calcular}
        except Exception as e:
            print(f"Error _calc: {e}"); return {m: None for m in metricas_a_calcular}

    def ejecutar_comparacion_optimo_vs_reales(self, metricas_comparacion):
        """Compara el quinteto óptimo con las alineaciones reales."""
        print(
            f"\n[Análisis] Comparando Quinteto Óptimo ({self.metrica_principal}) vs. Alineaciones Reales (Multi-Métrica)")

        # Comprueba si hay datos para comparar
        if self.df_reales is None or self.df_reales.empty: print("  No hay datos reales."); return None
        if not self.metricas_titulares_optimo: print("  No hay métricas óptimas."); return None
        if self.quinteto_optimo_df is None or self.quinteto_optimo_df.empty: print("  No hay DF óptimo."); return None

        # Obtiene la lista de jugadores óptimos
        df_temp_opt = self.quinteto_optimo_df.copy();
        players_ok = True
        if 'Player' not in df_temp_opt.columns:
            if df_temp_opt.index.name == 'Player':
                df_temp_opt = df_temp_opt.reset_index()
            else:
                players_ok = False
        if not players_ok: print("  Error: No se puede obtener lista jugadores óptimos."); return None
        jugadores_optimos_list = df_temp_opt['Player'].tolist()
        if len(jugadores_optimos_list) != 5: print("  Advertencia: Óptimo no tiene 5 J."); return None
        jugadores_optimos_set = set(jugadores_optimos_list)

        resultados_comp_real_multi = []
        metricas_calc_validas = [m for m in metricas_comparacion if
                                 m in self.datos_metricas.columns and pd.api.types.is_numeric_dtype(
                                     self.datos_metricas[m])]
        if not metricas_calc_validas: print("  Error: Métricas de comparación no válidas."); return None

        # Itera sobre cada alineación real
        col_jugadores_reales_names = [c for c in self.df_reales.columns if c.startswith('Player')]
        if len(col_jugadores_reales_names) != 5: print(
            f" Error: Columnas PlayerX incorrectas ({len(col_jugadores_reales_names)})."); return None
        for index, row_real in self.df_reales.iterrows():
            equipo_tm = row_real.get('Tm', f"Equipo_{index + 1}")
            jugadores_reales_list = list(row_real[col_jugadores_reales_names].dropna().astype(str))
            if len(jugadores_reales_list) != 5: continue

            # Calcula las métricas del equipo real y el índice de Jaccard
            metricas_equipo_real = self._calcular_metricas_quinteto(jugadores_reales_list, metricas_calc_validas)
            if not metricas_equipo_real or not any(v is not None for v in metricas_equipo_real.values()): continue
            jaccard = len(jugadores_optimos_set.intersection(set(jugadores_reales_list))) / len(
                jugadores_optimos_set.union(set(jugadores_reales_list)))

            # Almacena los resultados de la comparación
            resultado_equipo = {'Tm': equipo_tm, 'Jaccard': jaccard}
            for metrica in metricas_calc_validas:
                val_o = self.metricas_titulares_optimo.get(metrica);
                val_r = metricas_equipo_real.get(metrica)
                resultado_equipo[f"{metrica}_Opt"] = val_o;
                resultado_equipo[f"{metrica}_Real"] = val_r
                if pd.notna(val_o) and pd.notna(val_r):
                    resultado_equipo[f"{metrica}_Mejora"] = val_o - val_r
                else:
                    resultado_equipo[f"{metrica}_Mejora"] = None
            resultados_comp_real_multi.append(resultado_equipo)

        if resultados_comp_real_multi:
            # Crea un DataFrame y lo ordena por la mejora o Jaccard
            df_resumen_real = pd.DataFrame(resultados_comp_real_multi)
            sort_col = f"{self.metrica_principal}_Mejora"
            if sort_col not in df_resumen_real.columns or df_resumen_real[sort_col].isnull().all(): sort_col = 'Jaccard'
            df_sorted = df_resumen_real.sort_values(by=sort_col, ascending=False, na_position='last')

            # La impresión detallada está desactivada
            print(" -> Comparación numérica completada (resumen suprimido).")
            return df_sorted
        else:
            print("No se generaron resultados de comparación con equipos reales.")
            return None

    def ejecutar_analisis_sensibilidad(self, metricas_sensibilidad):
        """Ejecuta la optimización con diferentes métricas para ver cómo cambia el resultado."""
        print("\n[Análisis] Análisis de Sensibilidad del Optimizador (OE-6 - sobre Titulares)")
        if not self.optimizador: print("  Optimizador no disponible."); return None

        print("Generando quintetos titulares óptimos para diferentes métricas objetivo...")
        self.resultados_sensibilidad = {}
        # Itera sobre las métricas de prueba y ejecuta la optimización para cada una
        for nombre_enf, metrica_sens in metricas_sensibilidad.items():
            try:
                q_sens_df, v_sens, _ = self.optimizador.optimizar_quinteto(metrica_objetivo=metrica_sens)
                if q_sens_df is not None and v_sens is not None:
                    q_sens_df_list = []
                    if 'Player' in q_sens_df.columns:
                        q_sens_df_list = q_sens_df['Player'].tolist()
                    elif q_sens_df.index.name == 'Player':
                        q_sens_df_list = q_sens_df.index.tolist()

                    # Guarda el resultado si es un quinteto válido
                    if len(q_sens_df_list) == 5:
                        self.resultados_sensibilidad[nombre_enf] = q_sens_df_list
                    else:
                        self.resultados_sensibilidad[nombre_enf] = []
                else:
                    self.resultados_sensibilidad[nombre_enf] = []
            except Exception as e:
                print(f"  Error inesperado: {e}"); self.resultados_sensibilidad[nombre_enf] = []

        # La impresión detallada está desactivada
        print(" -> Análisis de Sensibilidad completado (detalles suprimidos).")
        return self.resultados_sensibilidad

    def visualizar_comparacion_fifa_style(self, metricas_visual):
        """Genera una comparación visual en texto, normalizando valores de 0 a 100."""
        print("\n[Análisis Visual] Comparación Estilo 'FIFA' (Óptimo vs Reales)")
        print("(Valores normalizados a escala 0-100, basados en min/max de todos los equipos comparados)")
        # Comprueba si hay datos para visualizar
        if self.df_reales is None or self.df_reales.empty: print("  No hay datos reales."); return
        if not self.metricas_titulares_optimo: print("  No hay métricas óptimas."); return

        metricas_validas = [m for m in metricas_visual if
                            m in self.datos_metricas.columns and pd.api.types.is_numeric_dtype(self.datos_metricas[m])]
        if not metricas_validas: print("  Error: Métricas visuales no válidas."); return
        print(f"  Métricas a visualizar: {metricas_validas}")

        # 1. Calcula las métricas para todos los equipos reales
        metricas_reales_todos = {}
        col_jugadores_reales_names = [c for c in self.df_reales.columns if c.startswith('Player')]
        if len(col_jugadores_reales_names) != 5: print("  Error: Formato archivo real."); return
        for index, row_real in self.df_reales.iterrows():
            equipo_tm = row_real.get('Tm', f"Equipo_{index + 1}")
            jugadores_reales_list = list(row_real[col_jugadores_reales_names].dropna().astype(str))
            if len(jugadores_reales_list) == 5:
                metricas_equipo = self._calcular_metricas_quinteto(jugadores_reales_list, metricas_validas)
                if metricas_equipo and any(v is not None for v in metricas_equipo.values()):
                    metricas_reales_todos[equipo_tm] = metricas_equipo
        if not metricas_reales_todos: print("  No se calcularon métricas para equipos reales."); return

        # 2. Encuentra el mínimo y máximo global para cada métrica (para normalizar)
        min_max_global = {}
        for metrica in metricas_validas:
            valores = []
            valor_optimo = self.metricas_titulares_optimo.get(metrica)
            if pd.notna(valor_optimo): valores.append(valor_optimo)
            for data_equipo in metricas_reales_todos.values():
                valor_real = data_equipo.get(metrica)
                if pd.notna(valor_real): valores.append(valor_real)
            if valores:
                min_val = min(valores);
                max_val = max(valores)
                if max_val > min_val: min_max_global[metrica] = {'min': min_val, 'max': max_val}

        # 3. Función interna para normalizar un valor a una escala 0-100
        def normalizar(valor, metrica, debug_label=""):
            if metrica not in min_max_global: return 0
            if pd.isna(valor): return 0
            stats = min_max_global[metrica];
            min_v = stats['min'];
            max_v = stats['max']
            if pd.isna(min_v) or pd.isna(max_v): return 0
            try:
                valor_f = float(valor); min_v_f = float(min_v); max_v_f = float(max_v)
            except (TypeError, ValueError):
                return 0
            denominador = max_v_f - min_v_f
            if denominador <= 1e-9: return 0 if abs(valor_f - min_v_f) < 1e-9 else 100
            norm_val = ((valor_f - min_v_f) / denominador) * 100
            resultado = max(0, min(100, int(round(norm_val))))
            return resultado

        # 4. Imprime las barras de comparación
        MAX_BAR_LEN = 30;
        METRIC_NAME_WIDTH = 15
        print("-" * (METRIC_NAME_WIDTH + 10 + MAX_BAR_LEN * 2))
        for equipo_tm, metricas_real in metricas_reales_todos.items():
            print(f"\n--- Óptimo vs. {equipo_tm} ---")
            print(
                f"{'Métrica'.ljust(METRIC_NAME_WIDTH)} | {'Óptimo'.center(MAX_BAR_LEN + 6)} | {'Real'.center(MAX_BAR_LEN + 6)}")
            print(f"{'-' * METRIC_NAME_WIDTH}-+-{'-' * (MAX_BAR_LEN + 6)}-+-{'-' * (MAX_BAR_LEN + 6)}")
            for metrica in metricas_validas:
                if metrica not in min_max_global: continue
                # Normaliza los valores y calcula la longitud de la barra
                val_opt = self.metricas_titulares_optimo.get(metrica);
                val_real = metricas_real.get(metrica)
                norm_opt = normalizar(val_opt, metrica, debug_label=f"Opt-{equipo_tm}")
                norm_real = normalizar(val_real, metrica, debug_label=f"Real-{equipo_tm}")
                bar_opt_len = int(round((norm_opt / 100) * MAX_BAR_LEN));
                bar_real_len = int(round((norm_real / 100) * MAX_BAR_LEN))
                bar_opt_str = '#' * bar_opt_len;
                bar_real_str = '#' * bar_real_len
                opt_str = f"({norm_opt:3d}) {bar_opt_str}";
                real_str = f"({norm_real:3d}) {bar_real_str}"
                # Imprime la línea de la métrica
                print(
                    f"{metrica.ljust(METRIC_NAME_WIDTH)} | {opt_str.ljust(MAX_BAR_LEN + 6)} | {real_str.ljust(MAX_BAR_LEN + 6)}")
            print("-" * (METRIC_NAME_WIDTH + 10 + MAX_BAR_LEN * 2))
        print("\n[Fin Análisis Visual]")

    def generar_visualizaciones(self, df_comp_real_resumen=None, resultados_sensibilidad=None):
        """Placeholder para gráficos futuros (e.g., con Matplotlib)."""
        pass  # No hacer nada aquí

# --- FIN DEL ARCHIVO AnalisisResultados.py ---