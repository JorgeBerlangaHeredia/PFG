# --- INICIO DEL ARCHIVO IndicadoresDesempeño.py ---

import pandas as pd
import numpy as np  # Necesario para np.where y np.inf

class IndicadoresDesempeño:
    """
    Calcula métricas de desempeño para jugadores, basándose en totales.
    Añade una métrica simple de Volumen Defensivo Total (STL+BLK).
    """

    def __init__(self, datos_limpiados):
        """Inicializa con datos limpios (stats por partido)."""
        if datos_limpiados is None or datos_limpiados.empty:
            raise ValueError("Se requiere un DataFrame de datos limpios no vacío.")
        # Verificar columnas base necesarias para calcular totales Y la nueva métrica
        required_base = ['Player', 'Pos', 'G', 'MP', 'PTS', 'AST', 'TRB', 'STL', 'BLK', # STL y BLK necesarios
                         'TOV', 'FG', 'FGA', 'FT', 'FTA', '3P']
        missing_base = [col for col in required_base if col not in datos_limpiados.columns]
        if missing_base:
            raise ValueError(f"Faltan columnas base necesarias en datos_limpiados: {', '.join(missing_base)}")
        self.datos = datos_limpiados.copy()
        self.datos_con_metricas = None  # Para almacenar el resultado final

    def _calcular_totales(self):
        """Paso 1: Calcula las estadísticas totales a partir de las por partido."""
        print("Calculando estadísticas totales...")
        stats_per_game_cols = ['PTS', 'AST', 'TRB', 'STL', 'BLK', 'TOV', 'FG', 'FGA', 'FT', 'FTA', 'MP', '3P']
        calculated_totals = [] # Para verificar después
        for col in stats_per_game_cols:
            total_col_name = f'{col}_Total'
            self.datos[total_col_name] = self.datos[col] * self.datos['G']
            calculated_totals.append(total_col_name)

        if '3P_Total' in self.datos.columns:
            self.datos.rename(columns={'3P_Total': 'ThreeP_Total'}, inplace=True)
            if 'ThreeP_Total' not in calculated_totals: calculated_totals.append('ThreeP_Total')

        # Verificar que las columnas totales esenciales se crearon
        required_totals = ['PTS_Total', 'TRB_Total', 'AST_Total', 'STL_Total', 'BLK_Total',
                           'FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'TOV_Total', 'MP_Total']
        missing_totals = [col for col in required_totals if col not in self.datos.columns]
        if missing_totals:
            raise RuntimeError(f"Fallo al calcular columnas totales esenciales: {missing_totals}")
        print("Estadísticas totales calculadas.")


    def _calcular_metricas_avanzadas(self):
        """Paso 2: Calcula métricas avanzadas usando las columnas _Total."""
        required_for_advanced = ['FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'PTS_Total', 'TRB_Total',
                                 'AST_Total', 'STL_Total', 'BLK_Total', 'TOV_Total', 'MP_Total']
        if self.datos is None or not all(col in self.datos.columns for col in required_for_advanced):
            missing = [col for col in required_for_advanced if col not in self.datos.columns]
            raise RuntimeError(f"Las columnas totales necesarias no están disponibles ({missing}) para calcular métricas avanzadas.")

        print("Calculando métricas avanzadas (EFF, TS%, Ratings)...")

        # Calcular EFF
        missed_fg = self.datos['FGA_Total'] - self.datos['FG_Total']
        missed_ft = self.datos['FTA_Total'] - self.datos['FT_Total']
        self.datos['EFF'] = (self.datos['PTS_Total'] + self.datos['TRB_Total'] + self.datos['AST_Total'] +
                             self.datos['STL_Total'] + self.datos['BLK_Total'] -
                             missed_fg - missed_ft - self.datos['TOV_Total'])

        # Calcular EFF/MIN
        self.datos['EFF/MIN'] = np.where(self.datos['MP_Total'] > 0, self.datos['EFF'] / self.datos['MP_Total'], 0)

        # Calcular TS%
        denominador_ts = 2 * (self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'])
        self.datos['TS%'] = np.where(denominador_ts > 0, self.datos['PTS_Total'] / denominador_ts, 0)

        # Calcular eFG% (calculado)
        denominador_efg = self.datos['FGA_Total']
        threeP_total = self.datos.get('ThreeP_Total', pd.Series(0, index=self.datos.index)) # Usar .get por si 3P no existe
        self.datos['eFG%_calculated'] = np.where(denominador_efg > 0,
                                                 (self.datos['FG_Total'] + 0.5 * threeP_total) / denominador_efg,
                                                 0)

        # Calcular Rating Ofensivo (Simplificado)
        posesiones_estimadas = self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'] + self.datos['TOV_Total']
        # Asegurar que posesiones no sea NaN o Infinito antes de dividir
        posesiones_estimadas = posesiones_estimadas.replace([np.inf, -np.inf], np.nan).fillna(0)
        self.datos['Off_Rating_Simple'] = np.where(posesiones_estimadas > 0,
                                                   (self.datos['PTS_Total'] / posesiones_estimadas) * 100,
                                                   0)
        # Placeholder para Def Rating y Net Rating
        # IMPORTANTE: Def_Rating_Placeholder ya no se usará para optimización defensiva
        self.datos['Def_Rating_Placeholder'] = 100 - self.datos['Off_Rating_Simple']
        self.datos['Net_Rating_Simple'] = self.datos['Off_Rating_Simple'] - self.datos['Def_Rating_Placeholder']

        print("Métricas avanzadas calculadas.")

    # --- NUEVO PASO PARA MÉTRICA DE VOLUMEN DEFENSIVO ---
    def _calcular_volumen_defensivo(self):
        """Paso 3: Calcula una métrica simple de volumen defensivo."""
        if 'STL_Total' not in self.datos.columns or 'BLK_Total' not in self.datos.columns:
            print("Advertencia: No se pueden calcular DEF_VOLUME_Total porque faltan STL_Total o BLK_Total.")
            self.datos['DEF_VOLUME_Total'] = 0 # Poner a 0 si faltan componentes
            return

        print("Calculando métrica de volumen defensivo (STL_Total + BLK_Total)...")
        # Sumar directamente, asumiendo que _calcular_totales ya manejó NaNs en STL/BLK originales
        self.datos['DEF_VOLUME_Total'] = self.datos['STL_Total'].fillna(0) + self.datos['BLK_Total'].fillna(0)
        print("Métrica de volumen defensivo calculada.")


    def _limpiar_metricas_finales(self):
        """Paso 4: Limpia Inf/NaN en todas las columnas calculadas."""
        print("Limpiando Inf/NaN en métricas finales...")
        # Lista más completa de columnas potencialmente calculadas
        calculated_cols = ['EFF', 'EFF/MIN', 'TS%', 'eFG%_calculated', 'Off_Rating_Simple',
                           'Def_Rating_Placeholder', 'Net_Rating_Simple', 'DEF_VOLUME_Total']
        # Añadir columnas _Total por si acaso
        total_cols = [col for col in self.datos.columns if col.endswith('_Total')]
        all_potential_cols = calculated_cols + total_cols

        for col in all_potential_cols:
            if col in self.datos.columns:
                 # Verificar si es numérica antes de intentar reemplazar/rellenar
                 if pd.api.types.is_numeric_dtype(self.datos[col]):
                    self.datos[col] = self.datos[col].replace([np.inf, -np.inf], 0).fillna(0)
                 # else: # Si no es numérica, no hacemos nada
                 #    print(f"Advertencia: La columna '{col}' no es numérica, no se limpiará.")
        print("Limpieza de métricas finales completada.")


    def calcular_metricas(self):
        """Orquesta el cálculo de totales, métricas avanzadas, volumen defensivo y limpieza final."""
        self._calcular_totales()
        self._calcular_metricas_avanzadas()
        self._calcular_volumen_defensivo() # <-- Llamada al nuevo método
        self._limpiar_metricas_finales()   # <-- Llamada a la limpieza final
        self.datos_con_metricas = self.datos.copy()  # Guardar el resultado final
        # Verificar si la nueva métrica existe
        if 'DEF_VOLUME_Total' not in self.datos_con_metricas.columns:
             print("Advertencia CRÍTICA: La métrica 'DEF_VOLUME_Total' no se pudo calcular o no existe.")
        return self.datos_con_metricas  # Devolver copia

    def obtener_datos_con_metricas(self):
        """Devuelve el DataFrame con todas las métricas calculadas."""
        if self.datos_con_metricas is None:
            print("Advertencia: Las métricas aún no se han calculado. Llamando a calcular_metricas()...")
            self.calcular_metricas()
        return self.datos_con_metricas.copy() if self.datos_con_metricas is not None else None

# --- FIN DEL ARCHIVO IndicadoresDesempeño.py ---