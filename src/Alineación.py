# --- START OF FILE Alineación.py ---

import pandas as pd

class Alineación:
    """
    Crea alineaciones titular y suplente usando un enfoque simple/greedy
    basado en una métrica seleccionada por tipo de alineación.
    Maneja multi-posición, evita duplicados y aplica filtros de tiempo de juego.
    """
    # MODIFICACIÓN: Añadir umbrales en __init__
    def __init__(self, datos_con_metricas, tipo_ali="equilibrada", min_g=15, min_mp_total=300):
        """
        Inicializa con datos, tipo de alineación y umbrales de tiempo de juego.
        :param datos_con_metricas: DataFrame con 'Player', 'Pos', y métricas. Debe tener 'Player' como índice o columna.
        :param tipo_ali: 'ofensiva', 'defensiva' o 'equilibrada'.
        :param min_g: Mínimo de partidos jugados para considerar a un jugador.
        :param min_mp_total: Mínimo de minutos totales jugados para considerar a un jugador.
        """
        required = ['Pos', 'Off_Rating_Simple', 'Def_Rating_Placeholder', 'EFF/MIN'] # Métricas usadas por defecto
        # Asegurar 'Player' como índice
        if 'Player' in datos_con_metricas.columns:
            self.datos = datos_con_metricas.set_index('Player').copy()
        elif datos_con_metricas.index.name == 'Player':
             self.datos = datos_con_metricas.copy()
        else:
             if 'Player' in datos_con_metricas.reset_index().columns:
                 self.datos = datos_con_metricas.reset_index().set_index('Player')
             else:
                 raise ValueError("Datos deben tener 'Player' como índice o columna.")

        # Verificar métricas requeridas por la clase
        if not all(col in self.datos.columns for col in required):
            missing = [col for col in required if col not in self.datos.columns]
            print(f"Advertencia (Alineación): Faltan columnas de métricas estándar: {missing}. Pueden ser necesarias para ciertos tipos de alineación.")
            # No lanzamos error aquí, la métrica específica se valida más abajo

        self.datos['Pos'] = self.datos['Pos'].astype(str)
        self.tipo_ali = tipo_ali
        self.metric_map = {
            'ofensiva': 'Off_Rating_Simple',
            'defensiva': 'Def_Rating_Placeholder', # Asegúrate que esta métrica exista o define otra
            'equilibrada': 'EFF/MIN'
        }
        if self.tipo_ali not in self.metric_map:
            raise ValueError(f"tipo_ali debe ser uno de {list(self.metric_map.keys())}")

        self.sort_metric = self.metric_map[self.tipo_ali]
        if self.sort_metric not in self.datos.columns:
            raise ValueError(f"La métrica '{self.sort_metric}' requerida para tipo_ali='{self.tipo_ali}' no se encuentra en los datos.")

        self.ascending_sort = False # Maximizar por defecto (cambiar si es necesario para métricas defensivas)

        # --- NUEVO: Almacenar y verificar columnas para filtros ---
        self.min_g = min_g
        self.min_mp_total = min_mp_total
        required_filter_cols = ['G', 'MP_Total']
        if not all(col in self.datos.columns for col in required_filter_cols):
             # Intenta calcular MP_Total si falta
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                 print("Advertencia (Alineación): Calculando MP_Total internamente para filtro.")
                 self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                 missing_filters = [col for col in required_filter_cols if col not in self.datos.columns]
                 raise ValueError(f"Datos deben contener columnas para filtros: {missing_filters}")
        # --- FIN NUEVO ---

        print(f"Alineacion creada: tipo='{self.tipo_ali}', métrica='{self.sort_metric}', filtros: min G={self.min_g}, min MP_Total={self.min_mp_total}")


    # MODIFICACIÓN: Aplicar filtro dentro de _get_eligible_players
    def _get_eligible_players(self, target_pos, excluded_players=[]):
        """Obtiene DataFrame de jugadores elegibles (que cumplen umbrales y posición) no excluidos."""
        eligible_indices = []

        # --- NUEVO: Filtrado inicial por minutos y juegos JUGADOS ---
        try:
            potential_players = self.datos[
                (self.datos['G'] >= self.min_g) &
                (self.datos['MP_Total'] >= self.min_mp_total)
            ]
        except KeyError as e:
            raise ValueError(f"Falta la columna necesaria para el filtro: {e}")

        print(f"  -> Pos {target_pos}: {len(potential_players)} jugadores cumplen umbrales G/MP_Total.")
        # --- FIN NUEVO ---

        # Ahora itera sobre los jugadores que CUMPLEN el umbral
        for player_index, player_data in potential_players.iterrows():
            if player_index in excluded_players:
                continue
            # Manejar Pos NaN residual (aunque debería estar limpio)
            if pd.isna(player_data['Pos']): continue
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_indices.append(player_index)

        print(f"  -> Pos {target_pos}: {len(eligible_indices)} jugadores elegibles tras filtro de posición y exclusión.")

        # Devuelve los datos de los jugadores elegibles (ya filtrados por G/MP_Total y Pos)
        if not eligible_indices:
            # Si no hay nadie elegible *después* de todos los filtros, devuelve df vacío
            return pd.DataFrame(columns=self.datos.columns)
        else:
             # Importante: usa .loc para obtener una copia y evitar SettingWithCopyWarning
             # y asegurar que operamos sobre los datos originales con todas las columnas
            return self.datos.loc[eligible_indices].copy()

    def crear_alineacion(self):
        """
        Crea y devuelve las alineaciones titular y suplente, usando jugadores filtrados.
        :return: (dict_titulares, dict_suplentes)
        """
        alineacion_titulares = {}
        alineacion_suplentes = {}
        selected_players = [] # Jugadores ya asignados a titular o suplente

        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']

        # --- Seleccionar Titulares ---
        print("\nSeleccionando Titulares...")
        for pos in posiciones:
            print(f"Buscando titular para {pos}...")
            # _get_eligible_players ya aplica los filtros G/MP_Total
            eligible_titulares = self._get_eligible_players(pos, excluded_players=selected_players)

            if eligible_titulares.empty:
                print(f"Advertencia: No jugadores disponibles (que cumplan filtros) para titular en {pos}")
                alineacion_titulares[pos] = None
                continue

            # Ordenar los elegibles (ya filtrados) por la métrica
            # Asegurarse de manejar NaNs en la métrica de ordenación si los hubiera
            best_player_series = eligible_titulares.sort_values(
                by=self.sort_metric, ascending=self.ascending_sort, na_position='last'
            ).iloc[0]
            best_player_name = best_player_series.name

            print(f"  -> Titular {pos}: {best_player_name} ({self.sort_metric}={best_player_series[self.sort_metric]:.2f})")
            alineacion_titulares[pos] = best_player_name
            selected_players.append(best_player_name)


        # --- Seleccionar Suplentes ---
        print("\nSeleccionando Suplentes...")
        for pos in posiciones:
            print(f"Buscando suplente para {pos}...")
            # _get_eligible_players ya aplica los filtros G/MP_Total
            eligible_suplentes = self._get_eligible_players(pos, excluded_players=selected_players)

            if eligible_suplentes.empty:
                print(f"Advertencia: No jugadores disponibles (que cumplan filtros) para suplente en {pos}")
                alineacion_suplentes[pos] = None
                continue

            best_suplente_series = eligible_suplentes.sort_values(
                by=self.sort_metric, ascending=self.ascending_sort, na_position='last'
            ).iloc[0]
            best_suplente_name = best_suplente_series.name

            print(f"  -> Suplente {pos}: {best_suplente_name} ({self.sort_metric}={best_suplente_series[self.sort_metric]:.2f})")
            alineacion_suplentes[pos] = best_suplente_name
            selected_players.append(best_suplente_name)


        print("\nAlineaciones generadas.")
        return alineacion_titulares, alineacion_suplentes

    def mostrar_alineacion_df(self, titulares, suplentes):
        """Muestra las alineaciones en formato DataFrame."""
        print("\n--- Alineación Generada (Simple/Greedy) ---")
        data_vis = {'Posicion': ['PG', 'SG', 'SF', 'PF', 'C']}
        titulares_list = [titulares.get(pos, 'N/A') for pos in data_vis['Posicion']]
        suplentes_list = [suplentes.get(pos, 'N/A') for pos in data_vis['Posicion']]
        data_vis['Titular'] = titulares_list
        data_vis['Suplente'] = suplentes_list

        df_vis = pd.DataFrame(data_vis)
        print(df_vis.to_string(index=False))

        # Mostrar métricas clave (sin cambios, usa self.datos que tiene todos los jugadores)
        print(f"\nMétricas del Titular (Ordenados por {self.sort_metric}):")
        titulares_validos = [p for p in titulares_list if p is not None and p != 'N/A']
        if titulares_validos:
             kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%'] # Añadir G, MP_Total
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[titulares_validos, cols_mostrar].sort_values(by=self.sort_metric, ascending=self.ascending_sort))
        else:
            print("No se seleccionaron titulares válidos.")

        print(f"\nMétricas del Suplente (Ordenados por {self.sort_metric}):")
        suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
        if suplentes_validos:
             kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%'] # Añadir G, MP_Total
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[suplentes_validos, cols_mostrar].sort_values(by=self.sort_metric, ascending=self.ascending_sort))
        else:
            print("No se seleccionaron suplentes válidos.")
        print("------------------------------------------")

# --- END OF FILE Alineación.py ---