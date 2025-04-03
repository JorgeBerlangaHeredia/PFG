# --- START OF FILE OptimizadorAlineacion.py ---

import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus

class OptimizadorAlineacion:
    """
    Encuentra la alineación titular ÓPTIMA y la alineación suplente ÓPTIMA
    usando dos ejecuciones separadas de PuLP, considerando filtros de participación.
    """
    def __init__(self, datos_con_metricas, min_g=15, min_mp_total=300):
        """
        Inicializa con datos, métricas y umbrales de tiempo de juego.
        """
        # ... (El __init__ se mantiene igual que tu versión anterior) ...
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
        print(f"OptimizadorAlineacion (Doble Opt) inicializado. Filtros: G>={self.min_g}, MP_Total>={self.min_mp_total}")


    def _optimizar_unidad(self, metrica_objetivo, jugadores_a_considerar, nombre_unidad="Titulares"):
        """
        Función interna genérica para optimizar un quinteto (titular o suplente)
        a partir de un DataFrame de jugadores ya filtrado.
        """
        if jugadores_a_considerar.empty:
            print(f"Error ({nombre_unidad}): No hay jugadores válidos para optimizar.")
            return None, None

        print(f"\n--- Iniciando Optimización para {nombre_unidad} ({metrica_objetivo}) ---")
        print(f"Jugadores considerados para {nombre_unidad}: {len(jugadores_a_considerar)}")

        # 1. Crear el problema
        prob = LpProblem(f"Mejor_Quinteto_{nombre_unidad}", LpMaximize)

        # 2. Definir variables
        jugadores_idx = jugadores_a_considerar.index.tolist()
        elegido = LpVariable.dicts(f"Elegir_{nombre_unidad}", jugadores_idx, cat=LpBinary)

        # 3. Función objetivo
        prob += lpSum(jugadores_a_considerar.loc[j, metrica_objetivo] * elegido[j] for j in jugadores_idx), f"Suma_{metrica_objetivo}_{nombre_unidad}"

        # 4. Restricciones
        prob += lpSum(elegido[j] for j in jugadores_idx) == 5, f"Total_{nombre_unidad}_5"
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            eligible_indices = self._get_players_for_position_from_df(jugadores_a_considerar, pos)
            if not eligible_indices:
                 print(f"ERROR CRÍTICO ({nombre_unidad}): No hay jugadores elegibles en pool para la posición '{pos}'.")
                 return None, None
            prob += lpSum(elegido[j] for j in eligible_indices) == 1, f"Exactamente_1_{pos}_{nombre_unidad}"

        # 5. Resolver
        print(f"  Resolviendo problema de optimización de {nombre_unidad} con PuLP...")
        try:
             status = prob.solve(PULP_CBC_CMD(msg=0))
        except Exception as e:
             print(f"  Error durante la ejecución del solver PuLP para {nombre_unidad}: {e}")
             return None, None

        # 6. Interpretar
        if status == 1:
            print(f"  ¡Solución óptima para {nombre_unidad} encontrada!")
            nombres_seleccionados = [j for j in jugadores_idx if elegido[j].varValue > 0.5]
            # Usar self.datos original para obtener todas las columnas
            unidad_df = self.datos.loc[nombres_seleccionados].reset_index()
            valor_objetivo_unidad = prob.objective.value()
            print(f"  Valor máximo de '{metrica_objetivo}' total ({nombre_unidad}): {valor_objetivo_unidad:.2f}")
            if len(unidad_df) != 5: print(f"  Advertencia: Se encontraron {len(unidad_df)} jugadores para {nombre_unidad} en lugar de 5.")
            return unidad_df, valor_objetivo_unidad
        else:
            status_text = LpStatus[prob.status]
            print(f"No se encontró una solución óptima para {nombre_unidad}. Estado de PuLP: {status_text} ({prob.status})")
            return None, None


    def generar_equipo_completo_doble_optimizado(self, metrica_objetivo='Off_Rating_Simple'):
        """
        Optimiza el quinteto titular y LUEGO optimiza el quinteto suplente
        a partir de los jugadores restantes que cumplen filtros.
        """
        print(f"\n--- Iniciando Doble Optimización (Métrica: {metrica_objetivo}) ---")

        # 0. Preparar datos base filtrados por métrica, Pos, G, MP_Total
        if metrica_objetivo not in self.datos.columns:
             raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")
        datos_base_filtrados = self.datos.copy()
        datos_base_filtrados[metrica_objetivo] = pd.to_numeric(datos_base_filtrados[metrica_objetivo], errors='coerce')
        filter_cols_check = [metrica_objetivo, 'Pos', 'G', 'MP_Total']
        datos_base_filtrados = datos_base_filtrados.dropna(subset=filter_cols_check)
        try:
            datos_base_filtrados = datos_base_filtrados[
                (datos_base_filtrados['G'] >= self.min_g) &
                (datos_base_filtrados['MP_Total'] >= self.min_mp_total)
            ]
        except KeyError as e:
             raise ValueError(f"Falta columna para filtro G/MP: {e}")

        if datos_base_filtrados.empty:
            print("Error: No hay jugadores válidos después de aplicar filtros G/MP iniciales.")
            return None, None, None, None

        # 1. Optimizar Titulares
        df_titulares, valor_obj_titulares = self._optimizar_unidad(
            metrica_objetivo,
            datos_base_filtrados, # Pasar el DF filtrado
            nombre_unidad="Titulares"
        )

        if df_titulares is None:
            print("Fallo al optimizar titulares. No se puede continuar.")
            return None, None, None, None

        # 2. Preparar datos para optimizar Suplentes
        titulares_nombres = df_titulares['Player'].tolist()
        # Crear pool de suplentes quitando los titulares del pool filtrado inicial
        pool_suplentes = datos_base_filtrados.drop(index=titulares_nombres, errors='ignore')

        # 3. Optimizar Suplentes
        df_suplentes, valor_obj_suplentes = self._optimizar_unidad(
            metrica_objetivo,
            pool_suplentes, # Pasar el pool restante
            nombre_unidad="Suplentes"
        )

        if df_suplentes is None:
            print("Se optimizaron titulares, pero falló la optimización de suplentes.")
            # Devolver titulares pero indicar fallo en suplentes
            return df_titulares, None, valor_obj_titulares, None

        return df_titulares, df_suplentes, valor_obj_titulares, valor_obj_suplentes


    def visualizar_equipo_doble_optimizado(self, df_titulares, df_suplentes, val_tit, val_sup, metrica):
        """Muestra las alineaciones óptimas de titulares y suplentes."""
        print(f"\n--- Visualización Equipo Doble Optimizado ({metrica}) ---")

        if df_titulares is None:
            print("No se generó quinteto titular óptimo.")
            return

        # --- Tabla Resumen ---
        data_vis = {'Posicion': ['PG', 'SG', 'SF', 'PF', 'C']}
        pos_order = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}

        def get_player_for_pos(df, pos_std):
            """Helper para encontrar el jugador en el df para una posición estándar"""
            if df is None: return 'N/A'
            for _, row in df.iterrows():
                player_pos = row['Pos'].split('-')
                if pos_std in player_pos:
                     # Asumimos que la optimización ya garantizó uno por posición
                     # Necesitamos una forma de mapear el jugador a la posición *requerida*
                     # Esto es complicado si un jugador multi-pos fue asignado.
                     # Por simplicidad visual, asignaremos basado en la primera posición requerida que cumple.
                     # O mejor: crear un mapeo directo después de la optimización.
                     # SOLUCIÓN MÁS SIMPLE: Presentar listas, no forzar mapeo 1 a 1 en la tabla.
                     pass # Se manejará abajo
            return 'N/A' # No encontrado (no debería pasar si la optimización funcionó)

        # Crear listas ordenadas por métrica o nombre para visualización
        titulares_list_str = df_titulares.sort_values(by=metrica, ascending=False)['Player'].tolist() if df_titulares is not None else ['N/A']*5
        suplentes_list_str = df_suplentes.sort_values(by=metrica, ascending=False)['Player'].tolist() if df_suplentes is not None else ['N/A']*5

        print("\nTabla Resumen (Óptimo Titular + Óptimo Suplente):")
        # Crear tabla simple con listas (sin forzar posición exacta)
        max_len = max(len(titulares_list_str), len(suplentes_list_str))
        titulares_list_str.extend([''] * (max_len - len(titulares_list_str)))
        suplentes_list_str.extend([''] * (max_len - len(suplentes_list_str)))
        df_vis_simple = pd.DataFrame({
            'Titular Optimizado': titulares_list_str,
            'Suplente Optimizado': suplentes_list_str
        })
        print(df_vis_simple.to_string(index=False))
        print(f"\nValor Total Titulares ({metrica}): {val_tit:.2f}")
        if val_sup is not None:
            print(f"Valor Total Suplentes ({metrica}): {val_sup:.2f}")
            print(f"Valor Total Equipo ({metrica}): {(val_tit or 0) + (val_sup or 0):.2f}")
        # --- Fin Tabla Resumen ---

        # --- Métricas Titulares ---
        print(f"\nMétricas Titulares Óptimos (Ordenados por {metrica}):")
        kpis_a_mostrar = [metrica, 'G', 'MP_Total', 'Pos', 'PTS', 'AST', 'TRB']
        columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in df_titulares.columns]
        print(df_titulares.sort_values(by=metrica, ascending=False)[columnas_display].to_string(index=False))

        # --- Métricas Suplentes ---
        if df_suplentes is not None and not df_suplentes.empty:
            print(f"\nMétricas Suplentes Óptimos (Ordenados por {metrica}):")
            columnas_display_subs = ['Player'] + [col for col in kpis_a_mostrar if col in df_suplentes.columns]
            print(df_suplentes.sort_values(by=metrica, ascending=False)[columnas_display_subs].to_string(index=False))
        else:
            print("\nNo se generó quinteto suplente óptimo.")

        print("-----------------------------------------------------------\n")


    # Helper para obtener elegibles desde un DF específico (usado por _optimizar_unidad)
    def _get_players_for_position_from_df(self, dataframe, target_pos):
        """Obtiene índices de jugadores elegibles para target_pos desde el DataFrame pasado."""
        eligible_players = []
        for player_index, player_data in dataframe.iterrows():
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players

# --- END OF FILE OptimizadorAlineacion.py ---