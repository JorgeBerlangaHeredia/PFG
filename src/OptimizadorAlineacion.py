# --- INICIO DEL ARCHIVO OptimizadorAlineacion.py ---

import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus

class OptimizadorAlineacion:
    """
    Encuentra la alineación titular óptima (5 jugadores) usando PuLP y
    selecciona suplentes mediante un enfoque greedy, maximizando una
    métrica objetivo y considerando filtros y multi-posición.
    """
    def __init__(self, datos_con_metricas, min_g=15, min_mp_total=300):
        # ... (el __init__ no cambia significativamente) ...
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

        print(f"OptimizadorAlineacion inicializado. Filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")


    def _get_eligible_players_from_df(self, dataframe, target_pos, excluded_players=[]):
        """
        Obtiene DataFrame de jugadores elegibles (multi-pos) desde el DataFrame pasado,
        excluyendo a los ya seleccionados.
        Helper interno para selección greedy de suplentes.
        """
        eligible_indices = []
        # dataframe ya debe estar pre-filtrado por G y MP_Total en este punto
        for player_index, player_data in dataframe.iterrows():
            if player_index in excluded_players: continue
            # Asumiendo que 'Pos' ya no es NaN en dataframe
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                 eligible_indices.append(player_index)

        if not eligible_indices:
            return pd.DataFrame(columns=dataframe.columns) # Devuelve DF vacío si no hay nadie
        else:
            # Devuelve las filas elegibles del dataframe original pasado
            return dataframe.loc[eligible_indices].copy()


    def _seleccionar_suplentes_greedy(self, datos_filtrados, jugadores_titulares, metrica_objetivo):
        """Selecciona 5 suplentes (1 por pos) de forma greedy."""
        print("\n  Seleccionando Suplentes (Método Simple/Greedy)...")
        suplentes_dict = {}
        selected_players = list(jugadores_titulares) # Empezar con los titulares excluidos
        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']
        ascending_sort = False # Maximizar métrica

        for pos in posiciones:
            # Usar el helper para encontrar elegibles DENTRO de los datos ya filtrados
            eligible_suplentes = self._get_eligible_players_from_df(
                datos_filtrados, # Pasar el DF ya filtrado por G/MP
                pos,
                excluded_players=selected_players
            )

            if eligible_suplentes.empty:
                print(f"    Advertencia: No jugadores disponibles (filtros/ya usados) para suplente en {pos}")
                suplentes_dict[pos] = None
                continue # Pasar a la siguiente posición

            # Seleccionar el mejor suplente restante para esa posición
            # Asegurarse que la métrica sea numérica para ordenar
            if pd.api.types.is_numeric_dtype(eligible_suplentes[metrica_objetivo]):
                best_suplente_series = eligible_suplentes.sort_values(
                    by=metrica_objetivo, ascending=ascending_sort, na_position='last'
                ).iloc[0]
                best_suplente_name = best_suplente_series.name
                suplentes_dict[pos] = best_suplente_name
                selected_players.append(best_suplente_name) # Añadir suplente a excluidos
            else:
                 print(f"    Advertencia: Métrica '{metrica_objetivo}' no es numérica para suplente {pos}. No se puede seleccionar.")
                 suplentes_dict[pos] = None


        print(f"  Suplentes Simple/Greedy seleccionados: {len([p for p in suplentes_dict.values() if p])} de 5")
        return suplentes_dict


    def optimizar_quinteto(self, metrica_objetivo='Off_Rating_Simple'):
        """
        Encuentra el quinteto titular óptimo (PuLP) y selecciona suplentes (Greedy).
        Devuelve: DataFrame titulares, valor objetivo, Diccionario suplentes.
        """
        if metrica_objetivo not in self.datos.columns:
             raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")

        # 1. Filtrar datos base y aplicar filtros G/MP (PARA AMBOS, TITULARES Y SUPLENTES)
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
            return None, None, None # Devuelve 3 Nones

        print(f"\n--- Iniciando Optimización Titulares ({metrica_objetivo}) ---")
        print(f"Jugadores considerados (total elegibles): {len(datos_opt)}")

        # 2. Optimización Titulares (PuLP)
        prob = LpProblem("Mejor_Quinteto_Titular_NBA", LpMaximize)
        jugadores = datos_opt.index.tolist()
        elegido = LpVariable.dicts("ElegirJugador", jugadores, cat=LpBinary)
        prob += lpSum(datos_opt.loc[j, metrica_objetivo] * elegido[j] for j in jugadores), "Suma_Metrica"
        prob += lpSum(elegido[j] for j in jugadores) == 5, "Total_5"
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            eligible_indices_pulp = self._get_players_for_position_from_df(datos_opt, pos) # Reusamos helper
            if not eligible_indices_pulp:
                 print(f"ERROR CRÍTICO (PuLP): No hay jugadores elegibles en datos_opt para '{pos}'.")
                 return None, None, None # Devuelve 3 Nones
            # Modificación clave para PuLP: >= 1 por posición exacta
            # prob += lpSum(elegido[j] for j in eligible_indices_pulp) == 1, f"Exactamente_1_{pos}"
            # Corrección: La restricción debe ser >= 1 para permitir multi-posición flexiblmente
            # La restricción global de == 5 se encarga del total.
            # PERO, para garantizar *un rol principal*, mantenemos == 1 aquí.
            # El _get_players_for_position_from_df ya maneja multi-posición.
            # Asegurémonos que la función _get_players... sea la correcta (sí, lo es)
            prob += lpSum(elegido[j] for j in eligible_indices_pulp if j in elegido) == 1, f"Exactamente_1_{pos}"


        print("  Resolviendo problema de optimización con PuLP...")
        try: status = prob.solve(PULP_CBC_CMD(msg=0))
        except Exception as e: print(f"  Error solver PuLP: {e}"); return None, None, None

        if status == 1:
            print("  ¡Solución óptima para titulares encontrada!")
            nombres_titulares = [j for j in jugadores if elegido[j].varValue > 0.5]
            quinteto_df = self.datos.loc[nombres_titulares].reset_index() # Usar datos originales
            valor_objetivo = prob.objective.value()
            print(f"  Valor Total Titulares ({metrica_objetivo}): {valor_objetivo:.2f}")
            if len(quinteto_df) != 5: print(f"  Advertencia: {len(quinteto_df)} titulares encontrados.")

            # 3. Selección de Suplentes (Greedy) - USANDO datos_opt (ya filtrado)
            suplentes_dict = self._seleccionar_suplentes_greedy(
                datos_opt, # Pasar los datos filtrados antes de PuLP
                nombres_titulares,
                metrica_objetivo
            )

            return quinteto_df, valor_objetivo, suplentes_dict # Devolver los tres

        else:
            status_text = LpStatus[prob.status]
            print(f"No se encontró solución óptima para titulares. Estado PuLP: {status_text} ({prob.status})")
            return None, None, None # Devuelve 3 Nones


    # Renombrar y adaptar la función de visualización
    def visualizar_alineacion_completa(self, quinteto_df, valor_objetivo, metrica_objetivo, suplentes_dict):
        """Muestra titulares óptimos y suplentes greedy."""
        print(f"\n--- Visualización Alineación ({metrica_objetivo}) ---")
        print("--- Titulares Óptimos (PuLP) ---")
        if quinteto_df is not None and not quinteto_df.empty:
            print(f"Valor Total Titulares ({metrica_objetivo}): {valor_objetivo:.2f}")
            kpis_a_mostrar = ['Pos', metrica_objetivo, 'G', 'MP_Total', 'PTS', 'AST', 'TRB']
            columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in quinteto_df.columns]
            pos_order = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}
            quinteto_df_vis = quinteto_df.copy()
            # Extraer posición principal para ordenar visualización
            quinteto_df_vis['SortPos'] = quinteto_df_vis['Pos'].apply(lambda x: x.split('-')[0] if pd.notna(x) else 'N/A')
            quinteto_df_vis['SortOrder'] = quinteto_df_vis['SortPos'].map(pos_order).fillna(5)
            print(quinteto_df_vis.sort_values('SortOrder')[columnas_display].to_string(index=False))
        else:
            print("No hay titulares óptimos para visualizar.")

        print("\n--- Suplentes Seleccionados (Greedy) ---")
        if suplentes_dict:
            posiciones_std = ['PG', 'SG', 'SF', 'PF', 'C']
            data_vis = {'Posicion': posiciones_std}
            # Titulares (para tabla resumen) - obtener de quinteto_df si es posible
            titulares_list_vis = ['N/A'] * 5
            if quinteto_df is not None:
                 # Mapear titulares a sus posiciones principales para la tabla
                 titulares_map = {}
                 for idx, row in quinteto_df.iterrows():
                      main_pos = row['Pos'].split('-')[0]
                      if main_pos in posiciones_std:
                           titulares_map[main_pos] = row['Player']
                 titulares_list_vis = [titulares_map.get(pos, 'N/A?') for pos in posiciones_std]


            suplentes_list = [suplentes_dict.get(pos, 'N/A') for pos in posiciones_std]
            data_vis['Titular (Optimo)'] = titulares_list_vis # Añadido para contexto
            data_vis['Suplente (Greedy)'] = suplentes_list
            df_vis = pd.DataFrame(data_vis)
            print("\nTabla Resumen Titulares/Suplentes:")
            print(df_vis.to_string(index=False))

            # Mostrar métricas de suplentes válidos
            suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
            if suplentes_validos:
                 print(f"\nMétricas del Suplente (Ordenados por {metrica_objetivo}):")
                 kpis_mostrar_sup = [metrica_objetivo, 'Pos', 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN'] # Añadir Pos y EFF/MIN
                 cols_mostrar_sup = [col for col in kpis_mostrar_sup if col in self.datos.columns]
                 # Asegurarse que las columnas existen antes de intentar acceder
                 cols_existentes = [c for c in cols_mostrar_sup if c in self.datos.columns]
                 if cols_existentes:
                      print(self.datos.loc[suplentes_validos, cols_existentes].sort_values(
                           by=metrica_objetivo, ascending=False # Siempre descendente para visualización
                         ).to_string())
                 else:
                      print("No hay columnas de KPIs válidas para mostrar para los suplentes.")

            else: print("\nNo se seleccionaron suplentes válidos.")
        else:
            print("No se generó diccionario de suplentes.")
        print("-------------------------------------------------------\n")


    # Helper renombrado y ajustado
    def _get_players_for_position_from_df(self, dataframe, target_pos):
        """Obtiene índices de jugadores elegibles (multi-pos) desde el DataFrame pasado.
           USADO POR PULP."""
        eligible_players = []
        for player_index, player_data in dataframe.iterrows():
            # Asumiendo que 'Pos' ya no es NaN en dataframe (datos_opt)
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        # Devuelve solo los ÍNDICES (nombres) para PuLP
        return eligible_players


# --- FIN DEL ARCHIVO OptimizadorAlineacion.py ---