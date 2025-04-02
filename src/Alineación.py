import pandas as pd

class Alineación:
    """
    Crea alineaciones titular y suplente usando un enfoque simple/greedy
    basado en una métrica seleccionada por tipo de alineación.
    Maneja multi-posición y evita duplicados.
    """
    def __init__(self, datos_con_metricas, tipo_ali="equilibrada"):
        """
        Inicializa con datos y tipo de alineación.
        :param datos_con_metricas: DataFrame con 'Player', 'Pos', y métricas.
        :param tipo_ali: 'ofensiva', 'defensiva' o 'equilibrada'.
        """
        required = ['Pos', 'Off_Rating_Simple', 'Def_Rating_Placeholder', 'EFF/MIN']
        if 'Player' in datos_con_metricas.columns:
            self.datos = datos_con_metricas.set_index('Player').copy()
        elif datos_con_metricas.index.name == 'Player':
             self.datos = datos_con_metricas.copy()
        else:
             if 'Player' in datos_con_metricas.reset_index().columns:
                 self.datos = datos_con_metricas.reset_index().set_index('Player')
             else:
                 raise ValueError("Datos deben tener 'Player' como índice o columna.")

        if not all(col in self.datos.columns for col in required):
            missing = [col for col in required if col not in self.datos.columns]
            raise ValueError(f"Datos deben contener columnas: {missing}")

        self.datos['Pos'] = self.datos['Pos'].astype(str)
        self.tipo_ali = tipo_ali
        self.metric_map = {
            'ofensiva': 'Off_Rating_Simple',
            'defensiva': 'Def_Rating_Placeholder',
            'equilibrada': 'EFF/MIN'
        }
        if self.tipo_ali not in self.metric_map:
            raise ValueError("tipo_ali debe ser 'ofensiva', 'defensiva' o 'equilibrada'")

        self.sort_metric = self.metric_map[self.tipo_ali]
        self.ascending_sort = False # Maximizar por defecto


        print(f"Alineacion creada: tipo='{self.tipo_ali}', métrica='{self.sort_metric}'")


    def _get_eligible_players(self, target_pos, excluded_players=[]):
        """Obtiene DataFrame de jugadores elegibles no excluidos para una posición."""
        eligible_indices = []
        for player_index, player_data in self.datos.iterrows():
            if player_index in excluded_players:
                continue
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_indices.append(player_index)
        return self.datos.loc[eligible_indices]

    def crear_alineacion(self):
        """
        Crea y devuelve las alineaciones titular y suplente.
        :return: (dict_titulares, dict_suplentes)
        """
        alineacion_titulares = {}
        alineacion_suplentes = {}
        selected_players = [] # Jugadores ya asignados a titular o suplente

        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']

        # --- Seleccionar Titulares ---
        print("\nSeleccionando Titulares...")
        for pos in posiciones:
            eligible_titulares = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_titulares.empty:
                print(f"Advertencia: No jugadores disponibles para titular en {pos}")
                alineacion_titulares[pos] = None
                continue

            best_player_series = eligible_titulares.sort_values(
                by=self.sort_metric, ascending=self.ascending_sort, na_position='last'
            ).iloc[0]
            best_player_name = best_player_series.name

            alineacion_titulares[pos] = best_player_name
            selected_players.append(best_player_name)


        # --- Seleccionar Suplentes ---
        print("Seleccionando Suplentes...")
        for pos in posiciones:
            eligible_suplentes = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_suplentes.empty:
                print(f"Advertencia: No jugadores disponibles para suplente en {pos}")
                alineacion_suplentes[pos] = None
                continue

            best_suplente_series = eligible_suplentes.sort_values(
                by=self.sort_metric, ascending=self.ascending_sort, na_position='last'
            ).iloc[0]
            best_suplente_name = best_suplente_series.name

            alineacion_suplentes[pos] = best_suplente_name
            selected_players.append(best_suplente_name)


        print("Alineaciones generadas.")
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

        # Mostrar métricas clave de los jugadores seleccionados
        print("\nMétricas del Titular:")
        titulares_validos = [p for p in titulares_list if p is not None and p != 'N/A']
        if titulares_validos:
             kpis_mostrar = [self.sort_metric, 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[titulares_validos, cols_mostrar])
        else:
            print("No se seleccionaron titulares válidos.")

        print("\nMétricas del Suplente:")
        suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
        if suplentes_validos:
             kpis_mostrar = [self.sort_metric, 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[suplentes_validos, cols_mostrar])
        else:
            print("No se seleccionaron suplentes válidos.")
        print("------------------------------------------")