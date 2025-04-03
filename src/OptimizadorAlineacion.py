# --- START OF FILE OptimizadorAlineacion.py ---

import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus

class OptimizadorAlineacion:
    """
    Encuentra la alineación titular óptima (5 jugadores) usando PuLP para
    maximizar una métrica objetivo, considerando filtros de participación y multi-posición.
    """
    def __init__(self, datos_con_metricas, min_g=15, min_mp_total=300):
        """
        Inicializa con datos, métricas y umbrales de tiempo de juego.
        """
        if datos_con_metricas is None or datos_con_metricas.empty:
            raise ValueError("Se requiere un DataFrame con métricas no vacío.")

        self.datos = datos_con_metricas.copy()
        if 'Player' in self.datos.columns: self.datos = self.datos.set_index('Player')
        elif self.datos.index.name != 'Player':
             if 'Player' in self.datos.reset_index().columns: self.datos = self.datos.reset_index().set_index('Player')
             else: raise ValueError("Datos deben tener 'Player' como índice o columna.")

        required_init = ['Pos', 'G', 'MP_Total']
        if not all(col in self.datos.columns for col in required_init):
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                 print("Advertencia (Optimizador): Calculando MP_Total internamente.")
                 self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                missing_init = [col for col in required_init if col not in self.datos.columns]
                raise ValueError(f"Datos deben contener columnas para filtros: {missing_init}")

        self.min_g = min_g
        self.min_mp_total = min_mp_total
        self.datos['Pos'] = self.datos['Pos'].fillna('Unknown').astype(str)

        print(f"OptimizadorAlineacion (Solo Titulares) inicializado. Filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")


    def optimizar_quinteto(self, metrica_objetivo='Off_Rating_Simple'):
        """
        Encuentra el quinteto titular óptimo (5 jugadores) que maximiza la métrica objetivo,
        considerando filtros de participación y multi-posición.
        Devuelve el DataFrame de los 5 titulares y el valor objetivo.
        """
        if metrica_objetivo not in self.datos.columns:
             raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")

        # Filtrar datos base y aplicar filtros G/MP
        datos_opt = self.datos.copy()
        datos_opt[metrica_objetivo] = pd.to_numeric(datos_opt[metrica_objetivo], errors='coerce')
        filter_cols_check = [metrica_objetivo, 'Pos', 'G', 'MP_Total']
        datos_opt = datos_opt.dropna(subset=filter_cols_check)
        try:
            datos_opt = datos_opt[
                (datos_opt['G'] >= self.min_g) &
                (datos_opt['MP_Total'] >= self.min_mp_total)
            ]
        except KeyError as e: raise ValueError(f"Falta columna para filtro: {e}")

        if datos_opt.empty:
            print(f"Error (optimizar_quinteto): No hay jugadores válidos post-filtros.")
            return None, None

        print(f"\n--- Iniciando Optimización Titulares ({metrica_objetivo}) ---")
        print(f"Jugadores considerados: {len(datos_opt)}")

        # --- Lógica PuLP ---
        prob = LpProblem("Mejor_Quinteto_Titular_NBA", LpMaximize)
        jugadores = datos_opt.index.tolist()
        elegido = LpVariable.dicts("ElegirJugador", jugadores, cat=LpBinary)
        prob += lpSum(datos_opt.loc[j, metrica_objetivo] * elegido[j] for j in jugadores), "Suma_Metrica"
        prob += lpSum(elegido[j] for j in jugadores) == 5, "Total_5"
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            # Usa el helper para encontrar elegibles (multi-pos) dentro de datos_opt
            eligible_indices = self._get_players_for_position_from_df(datos_opt, pos)
            if not eligible_indices:
                 print(f"ERROR CRÍTICO: No hay jugadores elegibles en datos_opt para '{pos}'.")
                 return None, None
            prob += lpSum(elegido[j] for j in eligible_indices) == 1, f"Exactamente_1_{pos}"

        print("  Resolviendo problema de optimización con PuLP...")
        try: status = prob.solve(PULP_CBC_CMD(msg=0))
        except Exception as e: print(f"  Error solver PuLP: {e}"); return None, None

        if status == 1:
            print("  ¡Solución óptima encontrada!")
            nombres_seleccionados = [j for j in jugadores if elegido[j].varValue > 0.5]
            quinteto_df = self.datos.loc[nombres_seleccionados].reset_index() # Usar datos originales
            valor_objetivo = prob.objective.value()
            print(f"  Valor Total ({metrica_objetivo}): {valor_objetivo:.2f}")
            if len(quinteto_df) != 5: print(f"  Advertencia: {len(quinteto_df)} jugadores encontrados.")
            return quinteto_df, valor_objetivo
        else:
            status_text = LpStatus[prob.status]
            print(f"No se encontró solución óptima. Estado PuLP: {status_text} ({prob.status})")
            return None, None


    # Helper para obtener elegibles desde un DF específico (usado por optimizar_quinteto)
    def _get_players_for_position_from_df(self, dataframe, target_pos):
        """Obtiene índices de jugadores elegibles (multi-pos) desde el DataFrame pasado."""
        eligible_players = []
        for player_index, player_data in dataframe.iterrows():
            # Asumiendo que 'Pos' ya no es NaN en dataframe (datos_opt)
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players


    def visualizar_alineacion_basico(self, quinteto_df, valor_objetivo, metrica_objetivo):
        """Muestra SOLO el quinteto titular óptimo y KPIs seleccionados."""
        print(f"\n--- Visualización Quinteto Titular Óptimo ({metrica_objetivo}) ---")
        if quinteto_df is not None and not quinteto_df.empty:
            print(f"Alineación Óptima (Valor Total {metrica_objetivo}: {valor_objetivo:.2f}):")
            kpis_a_mostrar = ['Pos', metrica_objetivo, 'G', 'MP_Total', 'PTS', 'AST', 'TRB']
            columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in quinteto_df.columns]
            # Ordenar visualización por posición estándar
            pos_order = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}
            quinteto_df_vis = quinteto_df.copy()
            quinteto_df_vis['SortPos'] = quinteto_df_vis['Pos'].apply(lambda x: x.split('-')[0] if pd.notna(x) else 'N/A')
            quinteto_df_vis['SortOrder'] = quinteto_df_vis['SortPos'].map(pos_order).fillna(5)
            print(quinteto_df_vis.sort_values('SortOrder')[columnas_display].to_string(index=False))
        else:
            print("No hay alineación óptima para visualizar.")
        print("-------------------------------------------------------\n")

# --- END OF FILE OptimizadorAlineacion.py ---