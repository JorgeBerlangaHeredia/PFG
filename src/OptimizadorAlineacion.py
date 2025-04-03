# --- START OF FILE OptimizadorAlineacion.py ---

import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus

class OptimizadorAlineacion:
    """
    Encuentra la alineación óptima (...) usando PuLP para maximizar una métrica objetivo,
    considerando solo jugadores que cumplen umbrales de participación.
    """
    # MODIFICACIÓN: Añadir umbrales en __init__
    def __init__(self, datos_con_metricas, min_g=15, min_mp_total=300):
        """
        Inicializa con datos, métricas y umbrales de tiempo de juego.
        :param datos_con_metricas: DataFrame con 'Player', 'Pos', métricas y columnas 'G', 'MP_Total'. Debe tener 'Player' como índice o columna.
        :param min_g: Mínimo de partidos jugados para considerar a un jugador.
        :param min_mp_total: Mínimo de minutos totales jugados para considerar a un jugador.
        """
        if datos_con_metricas is None or datos_con_metricas.empty:
            raise ValueError("Se requiere un DataFrame con métricas no vacío.")

        # Asegurar 'Player' como índice
        self.datos = datos_con_metricas.copy()
        if 'Player' in self.datos.columns:
            self.datos = self.datos.set_index('Player')
        elif self.datos.index.name != 'Player':
             if 'Player' in self.datos.reset_index().columns:
                 self.datos = self.datos.reset_index().set_index('Player')
             else:
                 raise ValueError("Datos deben tener 'Player' como índice o columna.")

        # Verificar columnas iniciales mínimas ('Pos' y las de filtro)
        required_init = ['Pos', 'G', 'MP_Total']
        if not all(col in self.datos.columns for col in required_init):
            # Intenta calcular MP_Total si falta
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                 print("Advertencia (Optimizador): Calculando MP_Total internamente para filtro.")
                 self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                missing_init = [col for col in required_init if col not in self.datos.columns]
                raise ValueError(f"Datos deben contener las columnas para inicialización/filtros: {missing_init}")

        # Almacenar umbrales
        self.min_g = min_g
        self.min_mp_total = min_mp_total

        # Asegurar 'Pos' es string y manejar NaNs residuales
        self.datos['Pos'] = self.datos['Pos'].fillna('Unknown').astype(str)
        print(f"OptimizadorAlineacion inicializado con {len(self.datos)} jugadores. Filtros aplicados en optimización: min G={self.min_g}, min MP_Total={self.min_mp_total}")


    # MODIFICACIÓN: Aplicar filtro dentro de optimizar_quinteto
    def optimizar_quinteto(self, metrica_objetivo='Off_Rating_Simple'):
        """
        Encuentra el quinteto titular (...) que maximiza la métrica objetivo,
        considerando solo jugadores que cumplen umbrales de participación.
        """
        if metrica_objetivo not in self.datos.columns:
             raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")

        # Filtrar datos base: métrica numérica, Pos no nulo
        datos_opt = self.datos.copy()
        datos_opt[metrica_objetivo] = pd.to_numeric(datos_opt[metrica_objetivo], errors='coerce')
        # Asegurar columnas de filtro también
        filter_cols_check = [metrica_objetivo, 'Pos', 'G', 'MP_Total']
        datos_opt = datos_opt.dropna(subset=filter_cols_check)

        # --- NUEVO: Aplicar filtro de participación a datos_opt ---
        print(f"Jugadores antes del filtro G/MP_Total: {len(datos_opt)}")
        try:
            datos_opt = datos_opt[
                (datos_opt['G'] >= self.min_g) &
                (datos_opt['MP_Total'] >= self.min_mp_total)
            ]
        except KeyError as e:
             raise ValueError(f"Falta columna para filtro en datos: {e}")

        print(f"Jugadores DESPUÉS del filtro G/MP_Total: {len(datos_opt)}")
        # --- FIN NUEVO ---

        if datos_opt.empty:
            print(f"Error: No hay jugadores válidos después de aplicar todos los filtros (métrica, Pos, G, MP_Total).")
            return None, None

        print(f"\n--- Iniciando Optimización ({metrica_objetivo}) ---")
        print(f"Jugadores considerados para optimización (post-filtros): {len(datos_opt)}")

        # 1. Crear el problema
        prob = LpProblem("Mejor_Quinteto_NBA", LpMaximize)

        # 2. Definir variables (solo sobre jugadores en datos_opt filtrado)
        jugadores = datos_opt.index.tolist()
        elegido = LpVariable.dicts("ElegirJugador", jugadores, cat=LpBinary)

        # 3. Función objetivo (solo sobre jugadores en datos_opt)
        prob += lpSum(datos_opt.loc[j, metrica_objetivo] * elegido[j] for j in jugadores), "Suma_Metrica_Objetivo"

        # 4. Restricciones
        # Restricción 1: Exactamente 5 jugadores en total (de los elegibles post-filtro)
        prob += lpSum(elegido[j] for j in jugadores) == 5, "Total_Jugadores_5"

        # Restricciones 2-6: Exactamente un jugador ELEGIBLE (de datos_opt) para cada posición
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            # Obtener jugadores elegibles DESDE EL DATAFRAME YA FILTRADO (datos_opt)
            eligible_indices_opt = self._get_players_for_position_from_df(datos_opt, pos) # Usa helper

            if not eligible_indices_opt:
                 # ¡Este error es más probable ahora con filtros más estrictos!
                 print(f"ERROR CRÍTICO: No hay jugadores elegibles en datos_opt (post-filtros) para la posición '{pos}'. No se puede formar quinteto.")
                 return None, None

            # La restricción aplica solo a los jugadores elegibles (de datos_opt) para esta posición
            prob += lpSum(elegido[j] for j in eligible_indices_opt) == 1, f"Exactamente_1_{pos}"

        # 5. Resolver el problema
        print("Resolviendo el problema de optimización con PuLP...")
        try:
             status = prob.solve(PULP_CBC_CMD(msg=0))
        except Exception as e:
             print(f"Error durante la ejecución del solver PuLP: {e}")
             return None, None

        # 6. Interpretar los resultados
        if status == 1:
            print("¡Solución óptima encontrada!")
            quinteto_optimo_nombres = [j for j in jugadores if elegido[j].varValue > 0.5]

            # Crear DataFrame del resultado usando el DataFrame original (self.datos)
            # para tener todas las columnas originales antes del filtro G/MP
            quinteto_df = self.datos.loc[quinteto_optimo_nombres].reset_index()

            valor_objetivo = prob.objective.value()
            print(f"Valor máximo de '{metrica_objetivo}' total: {valor_objetivo:.2f}")

            if len(quinteto_df) != 5:
                 print(f"Advertencia: Se encontraron {len(quinteto_df)} jugadores en lugar de 5.")

            return quinteto_df, valor_objetivo
        else:
            status_text = LpStatus[prob.status]
            print(f"No se encontró una solución óptima. Estado de PuLP: {status_text} ({prob.status})")
            if status_text == 'Infeasible':
                print("El problema es infactible, probablemente no hay suficientes jugadores (post-filtros) para cumplir las restricciones de posición.")
            return None, None

    # Helper original (no se usa más en optimizar_quinteto pero puede ser útil)
    def _get_players_for_position(self, target_pos):
        """Obtiene índices de jugadores elegibles para target_pos desde self.datos (original)."""
        eligible_players = []
        for player_index, player_data in self.datos.iterrows():
            if pd.isna(player_data['Pos']): continue
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players

    # --- NUEVO: Helper para obtener elegibles desde un DF específico ---
    def _get_players_for_position_from_df(self, dataframe, target_pos):
        """Obtiene índices de jugadores elegibles para target_pos desde el DataFrame pasado como argumento."""
        eligible_players = []
        for player_index, player_data in dataframe.iterrows():
            # No necesitamos verificar Pos NaN aquí porque ya se hizo en el dropna de datos_opt
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players
    # --- FIN NUEVO ---

    def visualizar_alineacion_basico(self, quinteto_df, valor_objetivo, metrica_objetivo):
         """Muestra la alineación óptima y KPIs seleccionados de forma básica."""
         print(f"\n--- Visualización Alineación Óptima ({metrica_objetivo}) ---")
         if quinteto_df is not None and not quinteto_df.empty:
             print(f"Alineación Óptima (Valor Total {metrica_objetivo}: {valor_objetivo:.2f}):")
             # Añadir G y MP_Total a la visualización
             kpis_a_mostrar = ['Pos', metrica_objetivo, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in quinteto_df.columns]

             # Ordenar por posición estándar para mejor visualización
             pos_order = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}
             # Extraer la primera posición listada para ordenar
             quinteto_df['SortPos'] = quinteto_df['Pos'].apply(lambda x: x.split('-')[0])
             quinteto_df['SortOrder'] = quinteto_df['SortPos'].map(pos_order).fillna(5) # Poner desconocidos al final
             print(quinteto_df.sort_values('SortOrder')[columnas_display].to_string(index=False))
             # Eliminar columnas temporales si no las quieres permanentemente
             quinteto_df.drop(columns=['SortPos', 'SortOrder'], inplace=True, errors='ignore')

         else:
             print("No hay alineación óptima para visualizar.")
         print("-----------------------------------------------\n")

# --- END OF FILE OptimizadorAlineacion.py ---