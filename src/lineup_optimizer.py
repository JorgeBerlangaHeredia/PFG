

import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus


class OptimizadorAlineacion:
    """
    Encuentra la alineación titular óptima (5 jugadores) usando Programación Lineal (PuLP)
    y selecciona suplentes con un método simple (greedy).
    """

    def __init__(self, datos_con_metricas, min_g=15, min_mp_total=300):
        """Inicializa con los datos y los filtros de tiempo de juego."""
        if datos_con_metricas is None or datos_con_metricas.empty:
            raise ValueError("Se requiere un DataFrame con métricas no vacío.")

        # Asegura que 'Player' sea el índice del DataFrame
        self.datos = datos_con_metricas.copy()
        if 'Player' in self.datos.columns:
            self.datos = self.datos.set_index('Player')
        elif self.datos.index.name != 'Player':
            if 'Player' in self.datos.reset_index().columns:
                self.datos = self.datos.reset_index().set_index('Player')
            else:
                raise ValueError("data deben tener 'Player' como índice o columna.")

        # Verifica si las columnas para filtros existen, si no, calcula MP_Total
        required_init = ['Pos', 'G', 'MP_Total']
        if not all(col in self.datos.columns for col in required_init):
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                print("Advertencia (Optimizador): Calculando MP_Total internamente.")
                self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                missing_init = [col for col in required_init if col not in self.datos.columns]
                raise ValueError(f"data deben contener columnas para filtros: {missing_init}")

        self.min_g = min_g
        self.min_mp_total = min_mp_total
        self.datos['Pos'] = self.datos['Pos'].fillna('Unknown').astype(str)

        print(f"OptimizadorAlineacion inicializado. Filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")

    def _get_eligible_players_from_df(self, dataframe, target_pos, excluded_players=[]):
        """Helper para la selección greedy: encuentra jugadores elegibles en un DataFrame."""
        eligible_indices = []
        # Itera sobre los jugadores del DataFrame proporcionado
        for player_index, player_data in dataframe.iterrows():
            if player_index in excluded_players: continue
            # Comprueba si el jugador puede jugar en la posición buscada (lógica multi-posición)
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_indices.append(player_index)

        if not eligible_indices:
            return pd.DataFrame(columns=dataframe.columns)
        else:
            return dataframe.loc[eligible_indices].copy()

    def _seleccionar_suplentes_greedy(self, datos_filtrados, jugadores_titulares, metrica_objetivo):
        """Selecciona 5 suplentes (uno por posición) con un método greedy."""
        print("\n  Seleccionando Suplentes (Método Simple/Greedy)...")
        suplentes_dict = {}
        selected_players = list(jugadores_titulares)  # Excluye a los titulares
        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']
        ascending_sort = False  # Para maximizar la métrica

        # Itera sobre las posiciones para buscar un suplente para cada una
        for pos in posiciones:
            # Encuentra jugadores disponibles para la posición (que no sean titulares)
            eligible_suplentes = self._get_eligible_players_from_df(datos_filtrados, pos,
                                                                    excluded_players=selected_players)
            if eligible_suplentes.empty:
                suplentes_dict[pos] = None
                continue

            # Si hay jugadores, elige al mejor según la métrica objetivo
            if pd.api.types.is_numeric_dtype(eligible_suplentes[metrica_objetivo]):
                best_suplente_series = \
                eligible_suplentes.sort_values(by=metrica_objetivo, ascending=ascending_sort).iloc[0]
                best_suplente_name = best_suplente_series.name
                suplentes_dict[pos] = best_suplente_name
                selected_players.append(best_suplente_name)  # Añade al seleccionado para no repetirlo
            else:
                suplentes_dict[pos] = None
        print(f"  Suplentes Simple/Greedy seleccionados: {len([p for p in suplentes_dict.values() if p])} de 5")
        return suplentes_dict

    def optimizar_quinteto(self, metrica_objetivo='Off_Rating_Simple'):
        """Función principal: optimiza titulares con PuLP y selecciona suplentes con greedy."""
        if metrica_objetivo not in self.datos.columns:
            raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")

        # 1. Filtra el DataFrame para obtener solo jugadores elegibles (que cumplen G y MP_Total)
        datos_opt = self.datos.copy()
        datos_opt[metrica_objetivo] = pd.to_numeric(datos_opt[metrica_objetivo], errors='coerce')
        datos_opt = datos_opt.dropna(subset=[metrica_objetivo, 'Pos', 'G', 'MP_Total'])
        datos_opt = datos_opt[(datos_opt['G'] >= self.min_g) & (datos_opt['MP_Total'] >= self.min_mp_total)]
        if datos_opt.empty:
            print(f"Error: No hay jugadores válidos tras aplicar filtros.")
            return None, None, None

        print(f"\n--- Iniciando Optimización Titulares ({metrica_objetivo}) ---")
        print(f"Jugadores considerados (total elegibles): {len(datos_opt)}")

        # 2. Configuración del problema de optimización con PuLP para los titulares
        prob = LpProblem("Mejor_Quinteto_Titular_NBA", LpMaximize)  # Define el problema: maximizar
        jugadores = datos_opt.index.tolist()
        elegido = LpVariable.dicts("ElegirJugador", jugadores,
                                   cat=LpBinary)  # Variable de decisión: 1 si se elige, 0 si no

        # Función Objetivo: maximizar la suma de la métrica de los jugadores elegidos
        prob += lpSum(datos_opt.loc[j, metrica_objetivo] * elegido[j] for j in jugadores), "Suma_Metrica"

        # Restricción 1: El equipo debe tener exactamente 5 jugadores
        prob += lpSum(elegido[j] for j in jugadores) == 5, "Total_5"

        # Restricción 2: Debe haber exactamente un jugador para cada rol principal (PG, SG, etc.)
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            eligible_indices_pulp = self._get_players_for_position_from_df(datos_opt, pos)
            if not eligible_indices_pulp:
                print(f"ERROR CRÍTICO (PuLP): No hay jugadores elegibles para '{pos}'.")
                return None, None, None
            prob += lpSum(elegido[j] for j in eligible_indices_pulp if j in elegido) == 1, f"Exactamente_1_{pos}"

        print("  Resolviendo problema de optimización con PuLP...")
        status = prob.solve(PULP_CBC_CMD(msg=0))  # Resuelve el problema (sin mostrar mensajes del solver)

        # 3. Procesar la solución
        if status == 1:  # Si se encontró una solución óptima...
            print("  ¡Solución óptima para titulares encontrada!")
            nombres_titulares = [j for j in jugadores if
                                 elegido[j].varValue > 0.5]  # Extrae los jugadores seleccionados
            quinteto_df = self.datos.loc[nombres_titulares].reset_index()
            valor_objetivo = prob.objective.value()  # Obtiene el valor total de la métrica
            print(f"  Valor Total Titulares ({metrica_objetivo}): {valor_objetivo:.2f}")

            # 4. Llama a la función greedy para seleccionar a los suplentes
            suplentes_dict = self._seleccionar_suplentes_greedy(datos_opt, nombres_titulares, metrica_objetivo)
            return quinteto_df, valor_objetivo, suplentes_dict  # Devuelve los tres resultados
        else:  # Si no se encontró solución...
            status_text = LpStatus[prob.status]
            print(f"No se encontró solución óptima. Estado PuLP: {status_text}")
            return None, None, None

    def visualizar_alineacion_completa(self, quinteto_df, valor_objetivo, metrica_objetivo, suplentes_dict):
        """Muestra en formato de tabla los titulares óptimos y los suplentes seleccionados."""
        print(f"\n--- Visualización Alineación ({metrica_objetivo}) ---")

        # Muestra los datos de los titulares óptimos
        print("--- Titulares Óptimos (PuLP) ---")
        if quinteto_df is not None and not quinteto_df.empty:
            print(f"Valor Total Titulares ({metrica_objetivo}): {valor_objetivo:.2f}")
            kpis_a_mostrar = ['Pos', metrica_objetivo, 'G', 'MP_Total', 'PTS', 'AST', 'TRB']
            columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in quinteto_df.columns]

            # Prepara los datos para ordenar la visualización por posición (PG, SG, SF...)
            pos_order = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}
            quinteto_df_vis = quinteto_df.copy()
            quinteto_df_vis['SortPos'] = quinteto_df_vis['Pos'].apply(lambda x: x.split('-')[0])
            quinteto_df_vis['SortOrder'] = quinteto_df_vis['SortPos'].map(pos_order).fillna(5)
            print(quinteto_df_vis.sort_values('SortOrder')[columnas_display].to_string(index=False))

        # Muestra los datos de los suplentes
        print("\n--- Suplentes Seleccionados (Greedy) ---")
        if suplentes_dict:
            # Crea una tabla resumen de Titulares y Suplentes
            posiciones_std = ['PG', 'SG', 'SF', 'PF', 'C']
            titulares_map = {row['Pos'].split('-')[0]: row['Player'] for idx, row in quinteto_df.iterrows()}
            titulares_list_vis = [titulares_map.get(pos) for pos in posiciones_std]
            suplentes_list = [suplentes_dict.get(pos, 'N/A') for pos in posiciones_std]
            df_vis = pd.DataFrame({'Posicion': posiciones_std, 'Titular (Optimo)': titulares_list_vis,
                                   'Suplente (Greedy)': suplentes_list})
            print("\nTabla Resumen Titulares/Suplentes:")
            print(df_vis.to_string(index=False))

            # Muestra las métricas detalladas de los suplentes válidos
            suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
            if suplentes_validos:
                print(f"\nMétricas del Suplente (Ordenados por {metrica_objetivo}):")
                kpis_mostrar_sup = [metrica_objetivo, 'Pos', 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN']
                cols_mostrar_sup = [col for col in kpis_mostrar_sup if col in self.datos.columns]
                if cols_mostrar_sup:
                    print(self.datos.loc[suplentes_validos, cols_mostrar_sup].sort_values(by=metrica_objetivo,
                                                                                          ascending=False).to_string())
        print("-------------------------------------------------------\n")

    def _get_players_for_position_from_df(self, dataframe, target_pos):
        """Helper para PuLP: devuelve una lista de nombres de jugadores para una posición."""
        eligible_players = []
        for player_index, player_data in dataframe.iterrows():
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players
