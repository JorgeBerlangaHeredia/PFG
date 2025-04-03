# --- START OF FILE Alineación.py ---

import pandas as pd

class Alineación:
    """
    Crea alineaciones titular y suplente usando un enfoque simple/greedy
    basado en una métrica seleccionada por tipo de alineación.
    *** USA MULTI-POSICIÓN: Considera TODAS las posiciones listadas. ***
    Maneja evita duplicados y aplica filtros de tiempo de juego.
    """
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

        self.datos['Pos'] = self.datos['Pos'].astype(str)
        self.tipo_ali = tipo_ali
        self.metric_map = {
            'ofensiva': 'Off_Rating_Simple',
            'defensiva': 'Def_Rating_Placeholder', # ¡Validar esta métrica!
            'equilibrada': 'EFF/MIN'
        }
        if self.tipo_ali not in self.metric_map:
            raise ValueError(f"tipo_ali debe ser uno de {list(self.metric_map.keys())}")

        self.sort_metric = self.metric_map[self.tipo_ali]
        if self.sort_metric not in self.datos.columns:
            raise ValueError(f"La métrica '{self.sort_metric}' requerida para tipo_ali='{self.tipo_ali}' no se encuentra en los datos.")

        self.ascending_sort = False # Maximizar por defecto

        # Almacenar y verificar columnas para filtros
        self.min_g = min_g
        self.min_mp_total = min_mp_total
        required_filter_cols = ['G', 'MP_Total']
        if not all(col in self.datos.columns for col in required_filter_cols):
            if 'MP_Total' not in self.datos.columns and 'MP' in self.datos.columns and 'G' in self.datos.columns:
                 print("Advertencia (Alineación): Calculando MP_Total internamente para filtro.")
                 self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']
            else:
                 missing_filters = [col for col in required_filter_cols if col not in self.datos.columns]
                 raise ValueError(f"Datos deben contener columnas para filtros: {missing_filters}")

        print(f"Alineacion (Simple/Greedy) creada: tipo='{self.tipo_ali}', métrica='{self.sort_metric}', filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")
        print("*** Nota (Alineación Simple): Usa Multi-Posición. ***") # Nota actualizada

    # --- LÓGICA MULTI-POSICIÓN ---
    def _get_eligible_players(self, target_pos, excluded_players=[]):
        """
        Obtiene DataFrame de jugadores elegibles (que cumplen umbrales
        Y pueden jugar en target_pos - considerando multi-posición) no excluidos.
        """
        eligible_indices = []
        try:
            potential_players = self.datos[
                (self.datos['G'] >= self.min_g) &
                (self.datos['MP_Total'] >= self.min_mp_total)
            ]
        except KeyError as e:
            raise ValueError(f"Falta la columna necesaria para el filtro: {e}")

        for player_index, player_data in potential_players.iterrows():
            if player_index in excluded_players: continue
            if pd.isna(player_data['Pos']): continue
            positions = player_data['Pos'].split('-')
            # --- LÓGICA MULTI-POSICIÓN ---
            if target_pos in positions:
                 eligible_indices.append(player_index)
            # --- FIN LÓGICA MULTI-POSICIÓN ---

        if not eligible_indices:
            return pd.DataFrame(columns=self.datos.columns)
        else:
            return self.datos.loc[eligible_indices].copy()

    # --- Métodos crear_alineacion y mostrar_alineacion_df ---
    # (Sin cambios lógicos respecto a la última versión que te pasé,
    # pero asegúrate de que los prints reflejen "Multi-Pos")
    def crear_alineacion(self):
        alineacion_titulares = {}
        alineacion_suplentes = {}
        selected_players = []
        posiciones = ['PG', 'SG', 'SF', 'PF', 'C']
        print("\nSeleccionando Titulares (Método Simple/Greedy - Multi-Pos)...")
        for pos in posiciones:
            eligible_titulares = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_titulares.empty:
                print(f"Advertencia: No jugadores disponibles (filtros) para titular en {pos}")
                alineacion_titulares[pos] = None; continue
            best_player_series = eligible_titulares.sort_values(by=self.sort_metric, ascending=self.ascending_sort, na_position='last').iloc[0]
            best_player_name = best_player_series.name
            alineacion_titulares[pos] = best_player_name
            selected_players.append(best_player_name)
        print(f"Titulares Simple/Greedy (Multi-Pos) seleccionados: {len([p for p in alineacion_titulares.values() if p])} de 5")

        print("\nSeleccionando Suplentes (Método Simple/Greedy - Multi-Pos)...")
        for pos in posiciones:
            eligible_suplentes = self._get_eligible_players(pos, excluded_players=selected_players)
            if eligible_suplentes.empty:
                print(f"Advertencia: No jugadores disponibles (filtros/ya usados) para suplente en {pos}")
                alineacion_suplentes[pos] = None; continue
            best_suplente_series = eligible_suplentes.sort_values(by=self.sort_metric, ascending=self.ascending_sort, na_position='last').iloc[0]
            best_suplente_name = best_suplente_series.name
            alineacion_suplentes[pos] = best_suplente_name
            selected_players.append(best_suplente_name)
        print(f"Suplentes Simple/Greedy (Multi-Pos) seleccionados: {len([p for p in alineacion_suplentes.values() if p])} de 5")
        print("\nAlineaciones Simple/Greedy (Multi-Pos) generadas.")
        return alineacion_titulares, alineacion_suplentes

    def mostrar_alineacion_df(self, titulares, suplentes):
        print("\n--- Alineación Generada (Simple/Greedy - Usa Multi-Pos) ---")
        data_vis = {'Posicion': ['PG', 'SG', 'SF', 'PF', 'C']}
        titulares_list = [titulares.get(pos, 'N/A') for pos in data_vis['Posicion']]
        suplentes_list = [suplentes.get(pos, 'N/A') for pos in data_vis['Posicion']]
        data_vis['Titular'] = titulares_list
        data_vis['Suplente'] = suplentes_list
        df_vis = pd.DataFrame(data_vis)
        print("Tabla Resumen (Simple/Greedy - Multi-Pos):")
        print(df_vis.to_string(index=False))

        print(f"\nMétricas del Titular (Simple/Greedy-Multi-Pos - Ordenados por {self.sort_metric}):")
        # ... (código para mostrar métricas titulares) ...
        titulares_validos = [p for p in titulares_list if p is not None and p != 'N/A']
        if titulares_validos:
             kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[titulares_validos, cols_mostrar].sort_values(by=self.sort_metric, ascending=self.ascending_sort).to_string())
        else: print("No se seleccionaron titulares válidos.")

        print(f"\nMétricas del Suplente (Simple/Greedy-Multi-Pos - Ordenados por {self.sort_metric}):")
        # ... (código para mostrar métricas suplentes) ...
        suplentes_validos = [p for p in suplentes_list if p is not None and p != 'N/A']
        if suplentes_validos:
             kpis_mostrar = [self.sort_metric, 'G', 'MP_Total', 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             cols_mostrar = ['Pos'] + [col for col in kpis_mostrar if col in self.datos.columns]
             print(self.datos.loc[suplentes_validos, cols_mostrar].sort_values(by=self.sort_metric, ascending=self.ascending_sort).to_string())
        else: print("No se seleccionaron suplentes válidos.")
        print("------------------------------------------")

# --- END OF FILE Alineación.py ---