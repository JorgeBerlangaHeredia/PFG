
import pandas as pd


class Alineación:
    """
    Crea alineaciones titular y suplente usando un enfoque simple/greedy.
    Selecciona el mejor jugador disponible para cada posición según una métrica.
    Considera que un jugador puede tener múltiples posiciones (ej: 'SG-SF').
    """

    def __init__(self, datos_con_metricas, tipo_ali="equilibrada", min_g=15, min_mp_total=300):
        """
        Inicializa la clase con los datos y las reglas para la selección.
        :param datos_con_metricas: DataFrame con todos los jugadores y sus estadísticas.
        :param tipo_ali: Define la métrica a usar ('ofensiva', 'defensiva', 'equilibrada').
        :param min_g: Filtro de mínimo de partidos jugados.
        :param min_mp_total: Filtro de mínimo de minutos totales jugados.
        """
        required = ['Pos', 'Off_Rating_Simple', 'Def_Rating_Placeholder', 'EFF/MIN']  # Métricas clave

        # Asegura que 'Player' sea el índice del DataFrame
        if 'Player' in datos_con_metricas.columns:
            self.datos = datos_con_metricas.set_index('Player').copy()
        elif datos_con_metricas.index.name == 'Player':
            self.datos = datos_con_metricas.copy()
        else:
            # Intenta recuperar 'Player' si es una columna oculta tras el índice
            if 'Player' in datos_con_metricas.reset_index().columns:
                self.datos = datos_con_metricas.reset_index().set_index('Player')
            else:
                raise ValueError("data deben tener 'Player' como índice o columna.")

        # Verifica si las métricas por defecto existen
        if not all(col in self.datos.columns for col in required):
            missing = [col for col in required if col not in self.datos.columns]
            print(f"Advertencia (Alineación): Faltan columnas de métricas estándar: {missing}.")

        self.datos['Pos'] = self.datos['Pos'].astype(str)  # Asegura que la posición sea un string
        self.tipo_ali = tipo_ali

        # Mapea el tipo de alineación a la métrica de ordenación
        self.metric_map = {
            'ofensiva': 'Off_Rating_Simple',
            'defensiva': 'Def_Rating_Placeholder',
            'equilibrada': 'EFF/MIN'
        }
        if self.tipo_ali not in self.metric_map:
            raise ValueError(f"tipo_ali debe ser uno de {list(self.metric_map.keys())}")

        # Establece la métrica que se usará para ordenar y encontrar al "mejor" jugador
        self.sort_metric = self.metric_map[self.tipo_ali]
        if self.sort_metric not in self.datos.columns:
            raise ValueError(f"La métrica '{self.sort_metric}' no se encuentra en los datos.")

        self.ascending_sort = False  # False para que el valor más alto quede primero (maximizar)

        # Almacena los filtros de tiempo de juego
        self.min_g = min_g
        self.min_mp_total = min_mp_total
        required_filter_cols = ['G', 'MP_Total']
        # Si 'MP_Total' no existe, intenta calcularlo desde 'MP' y 'G'
        if not all(col in self.datos.columns for col in required_filter_cols):
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                print("Advertencia (Alineación): Calculando MP_Total internamente para filtro.")
                self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                missing_filters = [col for col in required_filter_cols if col not in self.datos.columns]
                raise ValueError(f"data deben contener columnas para filtros: {missing_filters}")

        print(
            f"Alineacion (Simple/Greedy) creada: tipo='{self.tipo_ali}', métrica='{self.sort_metric}', filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")
        print("*** Nota (Alineación Simple): Usa Multi-Posición. ***")

    def _get_eligible_players(self, target_pos, excluded_players=[]):
        """
        Encuentra jugadores que cumplen los filtros de tiempo de juego
        y pueden jugar en la posición buscada (target_pos), excluyendo a los ya seleccionados.
        """
        try:
            # Aplica los filtros de minutos y partidos jugados
            potential_players = self.datos[
                (self.datos['G'] >= self.min_g) &
                (self.datos['MP_Total'] >= self.min_mp_total)
                ]
        except KeyError as e:
            raise ValueError(f"Falta la columna necesaria para el filtro: {e}")

        eligible_indices = []
        for player_index, player_data in potential_players.iterrows():
            if player_index in excluded_players: continue  # Omite jugadores ya seleccionados
            if pd.isna(player_data['Pos']): continue  # Omite jugadores sin posición definida

            # --- LÓGICA MULTI-POSICIÓN ---
            # Divide el string de posición (ej. 'SG-SF') en una lista
            positions = player_data['Pos'].split('-')
            # Comprueba si la posición buscada está en la lista de posiciones del jugador
            if target_pos in positions:
                eligible_indices.append(player_index)

        if not eligible_indices:
            return pd.DataFrame(columns=self.datos.columns)  # Devuelve un DF vacío si no hay jugadores
        else:
            return self.datos.loc[eligible_indices].copy()  # Devuelve los jugadores elegibles

    def crear_alineacion(self):
        """
        Construye el equipo titular y suplente, posición por posición.
        """
        alineacion_titulares = {}
        alineacion_suplentes = {}
        selected_players = []  # Lista para no repetir jugadores
        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']  # Orden de selección

        print("\nSeleccionando Titulares (Método Simple/Greedy - Multi-Pos)...")
        for pos in posiciones:
            # Encuentra jugadores elegibles para la posición actual
            eligible_titulares = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_titulares.empty:
                print(f"Advertencia: No jugadores disponibles (filtros) para titular en {pos}")
                alineacion_titulares[pos] = None;
                continue

            # Ordena por la métrica y elige al mejor (el primero de la lista)
            best_player_series = \
            eligible_titulares.sort_values(by=self.sort_metric, ascending=self.ascending_sort, na_position='last').iloc[
                0]
            best_player_name = best_player_series.name

            # Añade al jugador al equipo y a la lista de seleccionados
            alineacion_titulares[pos] = best_player_name
            selected_players.append(best_player_name)
        print(
            f"Titulares Simple/Greedy (Multi-Pos) seleccionados: {len([p for p in alineacion_titulares.values() if p])} de 5")

        print("\nSeleccionando Suplentes (Método Simple/Greedy - Multi-Pos)...")
        for pos in posiciones:
            # Repite el proceso para los suplentes, excluyendo a los titulares ya elegidos
            eligible_suplentes = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_suplentes.empty:
                print(f"Advertencia: No jugadores disponibles (filtros/ya usados) para suplente en {pos}")
                alineacion_suplentes[pos] = None;
                continue

            best_suplente_series = \
            eligible_suplentes.sort_values(by=self.sort_metric, ascending=self.ascending_sort, na_position='last').iloc[
                0]
            best_suplente_name = best_suplente_series.name

            alineacion_suplentes[pos] = best_suplente_name
            selected_players.append(best_suplente_name)
        print(
            f"Suplentes Simple/Greedy (Multi-Pos) seleccionados: {len([p for p in alineacion_suplentes.values() if p])} de 5")
        print("\nAlineaciones Simple/Greedy (Multi-Pos) generadas.")

        return alineacion_titulares, alineacion_suplentes

    def mostrar_alineacion_df(self, titulares, suplentes):
        """Muestra las alineaciones generadas en un formato de tabla legible."""
        print("\n--- Alineación Generada (Simple/Greedy - Usa Multi-Pos) ---")

        # Crea un DataFrame resumen con Titulares y Suplentes
        data_vis = {'Posicion': ['PG', 'SG', 'SF', 'PF', 'C']}
        titulares_list = [titulares.get(pos, 'N/A') for pos in data_vis['Posicion']]
        suplentes_list = [suplentes.get(pos, 'N/A') for pos in data_vis['Posicion']]
        data_vis['Titular'] = titulares_list
        data_vis['Suplente'] = suplentes_list
        df_vis = pd.DataFrame(data_vis)
        print("Tabla Resumen (Simple/Greedy - Multi-Pos):")
        print(df_vis.to_string(index=False))

        # Muestra las estadísticas detalladas de los jugadores titulares
        print(f"\nMétricas del Titular (Simple/Greedy-Multi-Pos - Ordenados por {self.sort_metric}):")
        titulares_validos = [p for p in titulares_list if p is not None and p != 'N/A']
        if titulares_validos:
            kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
            cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
            print(self.datos.loc[titulares_validos, cols_mostrar].sort_values(by=self.sort_metric,
                                                                              ascending=self.ascending_sort).to_string())
        else:
            print("No se seleccionaron titulares válidos.")

        # Muestra las estadísticas detalladas de los jugadores suplentes
        print(f"\nMétricas del Suplente (Simple/Greedy-Multi-Pos - Ordenados por {self.sort_metric}):")
        suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
        if suplentes_validos:
            kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
            cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
            print(self.datos.loc[suplentes_validos, cols_mostrar].sort_values(by=self.sort_metric,
                                                                              ascending=self.ascending_sort).to_string())
        else:
            print("No se seleccionaron suplentes válidos.")
        print("------------------------------------------")
