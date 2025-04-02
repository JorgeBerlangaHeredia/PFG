# OptimizadorAlineacion.py
import pandas as pd
# Asegúrate de tener PuLP instalado: pip install pulp
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpBinary, PULP_CBC_CMD, LpStatus

class OptimizadorAlineacion:
    """
    Encuentra la alineación óptima de 5 jugadores (1 por posición estándar)
    usando Programación Lineal Entera (PuLP) para maximizar una métrica objetivo.
    Maneja jugadores con múltiples posiciones listadas (ej. 'C-PF').
    """

    def __init__(self, datos_con_metricas):
        """
        Inicializa con los datos de jugadores que incluyen métricas y posiciones.

        :param datos_con_metricas: DataFrame con 'Player', 'Pos', y las métricas calculadas.
        """
        if datos_con_metricas is None or datos_con_metricas.empty:
            raise ValueError("Se requiere un DataFrame con métricas no vacío.")

        # Verificar columnas esenciales mínimas
        required_init = ['Pos'] # La métrica se verificará en optimizar_quinteto
        if 'Player' not in datos_con_metricas.columns and datos_con_metricas.index.name != 'Player':
             # Intentar resetear si 'Player' no es columna ni índice
             if 'Player' in datos_con_metricas.reset_index().columns:
                  datos_con_metricas = datos_con_metricas.reset_index()
             else:
                  raise ValueError("Datos deben tener 'Player' como índice o columna.")

        missing_init = [col for col in required_init if col not in datos_con_metricas.columns]
        if missing_init:
             raise ValueError(f"Datos deben contener las columnas: {missing_init}")

        # Trabajar con una copia y asegurar 'Player' como índice para búsquedas fáciles
        self.datos = datos_con_metricas.copy()
        if 'Player' in self.datos.columns:
            self.datos = self.datos.set_index('Player')

        # Asegurar que 'Pos' es string y manejar NaNs residuales
        self.datos['Pos'] = self.datos['Pos'].fillna('Unknown').astype(str)
        print(f"OptimizadorAlineacion inicializado con {len(self.datos)} jugadores.")

    def _get_players_for_position(self, target_pos):
        """
        Función auxiliar para obtener la lista de índices de jugadores (nombres)
        que pueden jugar en la posición objetivo (target_pos),
        considerando las posiciones múltiples separadas por '-'.
        """
        eligible_players = []
        for player_index, player_data in self.datos.iterrows():
            # Manejar el caso improbable de que 'Pos' sea NaN a pesar del fillna anterior
            if pd.isna(player_data['Pos']): continue
            positions = player_data['Pos'].split('-')
            if target_pos in positions:
                eligible_players.append(player_index)
        return eligible_players

    def optimizar_quinteto(self, metrica_objetivo='Off_Rating_Simple'):
        """
        Encuentra el quinteto titular (1 PG, 1 SG, 1 SF, 1 PF, 1 C) que maximiza
        la métrica objetivo total, usando PuLP.

        :param metrica_objetivo: Nombre de la columna en self.datos a maximizar.
        :return: (DataFrame con los 5 jugadores de la alineación óptima, float con valor objetivo) o (None, None) si falla.
        """
        if metrica_objetivo not in self.datos.columns:
             print(f"Error: La métrica objetivo '{metrica_objetivo}' no se encuentra en las columnas.")
             raise ValueError(f"La métrica '{metrica_objetivo}' no se encuentra en los datos.")

        # Filtrar datos para asegurar que la métrica objetivo no tenga NaNs y sea numérica
        datos_opt = self.datos.copy()
        datos_opt[metrica_objetivo] = pd.to_numeric(datos_opt[metrica_objetivo], errors='coerce')
        datos_opt = datos_opt.dropna(subset=[metrica_objetivo, 'Pos']) # Asegurar Pos también

        if datos_opt.empty:
            print(f"Error: No hay jugadores válidos después de filtrar por métrica '{metrica_objetivo}' y 'Pos'.")
            return None, None

        print(f"\n--- Iniciando Optimización ---")
        print(f"Objetivo: Maximizar suma de '{metrica_objetivo}'")
        print(f"Jugadores considerados para optimización: {len(datos_opt)}")

        # 1. Crear el problema de optimización
        prob = LpProblem("Mejor_Quinteto_NBA", LpMaximize)

        # 2. Definir las variables de decisión (usando índices del df filtrado)
        jugadores = datos_opt.index.tolist()
        # El diccionario de variables usa los nombres de los jugadores como claves
        elegido = LpVariable.dicts("ElegirJugador", jugadores, cat=LpBinary)

        # 3. Definir la función objetivo
        prob += lpSum(datos_opt.loc[j, metrica_objetivo] * elegido[j] for j in jugadores), "Suma_Metrica_Objetivo"

        # 4. Definir las restricciones
        # Restricción 1: Exactamente 5 jugadores en total
        prob += lpSum(elegido[j] for j in jugadores) == 5, "Total_Jugadores_5"

        # Restricciones 2-6: Exactamente un jugador ELEGIBLE para cada posición requerida
        posiciones_requeridas = ['PG', 'SG', 'SF', 'PF', 'C']
        for pos in posiciones_requeridas:
            # Obtener jugadores elegibles DESDE EL DATAFRAME FILTRADO (datos_opt)
            eligible_indices_opt = []
            for player_index, player_data in datos_opt.iterrows():
                 if pd.isna(player_data['Pos']): continue
                 positions = player_data['Pos'].split('-')
                 if pos in positions:
                      eligible_indices_opt.append(player_index)

            if not eligible_indices_opt:
                 print(f"ERROR CRÍTICO: No hay jugadores elegibles en datos_opt para la posición requerida '{pos}'. No se puede formar quinteto.")
                 return None, None # No se puede cumplir la restricción

            # La restricción aplica solo a los jugadores elegibles para esta posición
            prob += lpSum(elegido[j] for j in eligible_indices_opt) == 1, f"Exactamente_1_{pos}"

        # 5. Resolver el problema
        print("Resolviendo el problema de optimización con PuLP...")
        # Usar solver CBC que viene con PuLP. msg=0 para menos verbosidad.
        try:
             status = prob.solve(PULP_CBC_CMD(msg=0))
        except Exception as e:
             print(f"Error durante la ejecución del solver PuLP: {e}")
             return None, None

        # 6. Interpretar los resultados
        if status == 1: # 1 significa 'Optimal' en PuLP
            print("¡Solución óptima encontrada!")
            # Extraer nombres de jugadores seleccionados
            quinteto_optimo_nombres = [j for j in jugadores if elegido[j].varValue > 0.5] # > 0.5 para precisión

            # Crear DataFrame del resultado usando el DataFrame original (self.datos) para tener todas las columnas
            # y resetear el índice para que 'Player' sea una columna
            quinteto_df = self.datos.loc[quinteto_optimo_nombres].reset_index()

            # Obtener el valor objetivo alcanzado
            valor_objetivo = prob.objective.value()
            print(f"Valor máximo de '{metrica_objetivo}' total: {valor_objetivo:.2f}")

            # Verificar si realmente tenemos 5 jugadores (sanity check)
            if len(quinteto_df) != 5:
                 print(f"Advertencia: Se encontraron {len(quinteto_df)} jugadores en lugar de 5. Revisar lógica.")
                 # Podría ocurrir si hay problemas con las restricciones o el solver

            return quinteto_df, valor_objetivo
        else:
            # Dar más detalles si no es óptimo
            status_text = LpStatus[prob.status]
            print(f"No se encontró una solución óptima. Estado de PuLP: {status_text} ({prob.status})")
            if status_text == 'Infeasible':
                print("El problema es infactible, probablemente no hay suficientes jugadores para cumplir las restricciones de posición.")
            elif status_text == 'Unbounded':
                print("El problema es no acotado, revisar la función objetivo o restricciones.")
            return None, None

    def visualizar_alineacion_basico(self, quinteto_df, valor_objetivo, metrica_objetivo):
         """Muestra la alineación óptima y KPIs seleccionados de forma básica."""
         print(f"\n--- Visualización Alineación Óptima ({metrica_objetivo}) ---")
         if quinteto_df is not None and not quinteto_df.empty:
             print(f"Alineación Óptima (Valor Total {metrica_objetivo}: {valor_objetivo:.2f}):")
             # Columnas a mostrar (asegúrate que existen)
             kpis_a_mostrar = ['Pos', metrica_objetivo, 'PTS', 'AST', 'TRB', 'EFF/MIN', 'TS%']
             # Seleccionar solo columnas existentes en el df del quinteto
             columnas_display = ['Player'] + [col for col in kpis_a_mostrar if col in quinteto_df.columns]

             print(quinteto_df[columnas_display].to_string(index=False))
         else:
             print("No hay alineación óptima para visualizar (posiblemente no se encontró solución).")
         print("-----------------------------------------------\n")