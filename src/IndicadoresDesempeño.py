import pandas as pd
import numpy as np  # Necesario para np.where y np.inf


class IndicadoresDesempeño:
    """Calcula métricas de desempeño para jugadores, basándose en totales."""

    def __init__(self, datos_limpiados):
        """Inicializa con datos limpios (stats por partido)."""
        if datos_limpiados is None or datos_limpiados.empty:
            raise ValueError("Se requiere un DataFrame de datos limpios no vacío.")
        # Verificar columnas base necesarias para calcular totales
        required_base = ['Player', 'Pos', 'G', 'MP', 'PTS', 'AST', 'TRB', 'STL', 'BLK', 'TOV', 'FG', 'FGA', 'FT', 'FTA',
                         '3P']
        missing_base = [col for col in required_base if col not in datos_limpiados.columns]
        if missing_base:
            raise ValueError(f"Faltan columnas base necesarias en datos_limpiados: {', '.join(missing_base)}")
        self.datos = datos_limpiados.copy()
        self.datos_con_metricas = None  # Para almacenar el resultado final

    def _calcular_totales(self):
        """Paso 1: Calcula las estadísticas totales a partir de las por partido."""
        print("Calculando estadísticas totales...")
        # Columnas a convertir a totales multiplicando por 'G'
        stats_per_game_cols = ['PTS', 'AST', 'TRB', 'STL', 'BLK', 'TOV', 'FG', 'FGA', 'FT', 'FTA', 'MP', '3P']
        for col in stats_per_game_cols:
            self.datos[f'{col}_Total'] = self.datos[col] * self.datos['G']

        # Renombrar 3P_Total por consistencia
        if '3P_Total' in self.datos.columns:
            self.datos.rename(columns={'3P_Total': 'ThreeP_Total'}, inplace=True)

        # Verificar que las columnas totales esenciales se crearon
        required_totals = ['PTS_Total', 'TRB_Total', 'AST_Total', 'STL_Total', 'BLK_Total',
                           'FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'TOV_Total', 'MP_Total']
        missing_totals = [col for col in required_totals if col not in self.datos.columns]
        if missing_totals:
            raise RuntimeError(f"Fallo al calcular columnas totales esenciales: {missing_totals}")
        print("Estadísticas totales calculadas.")

    def _calcular_metricas_avanzadas(self):
        """Paso 2: Calcula métricas avanzadas usando las columnas _Total."""
        if self.datos is None or not all(col in self.datos.columns for col in
                                         ['FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'PTS_Total', 'TRB_Total',
                                          'AST_Total', 'STL_Total', 'BLK_Total', 'TOV_Total', 'MP_Total']):
            raise RuntimeError("Las columnas totales necesarias no están disponibles para calcular métricas avanzadas.")

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
        # Usamos .get con valor por defecto 0 para ThreeP_Total por si acaso no se calculó
        threeP_total = self.datos.get('ThreeP_Total', pd.Series(0, index=self.datos.index))
        self.datos['eFG%_calculated'] = np.where(denominador_efg > 0,
                                                 (self.datos['FG_Total'] + 0.5 * threeP_total) / denominador_efg,
                                                 0)

        # Calcular Rating Ofensivo (Simplificado)
        posesiones_estimadas = self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'] + self.datos['TOV_Total']
        self.datos['Off_Rating_Simple'] = np.where(posesiones_estimadas > 0,
                                                   (self.datos['PTS_Total'] / posesiones_estimadas) * 100,
                                                   0)
        # Placeholder para Def Rating y Net Rating
        self.datos['Def_Rating_Placeholder'] = 100 - self.datos['Off_Rating_Simple']
        self.datos['Net_Rating_Simple'] = self.datos['Off_Rating_Simple'] - self.datos['Def_Rating_Placeholder']

        # Limpiar Inf/NaN en columnas calculadas
        calculated_cols = ['EFF', 'EFF/MIN', 'TS%', 'eFG%_calculated', 'Off_Rating_Simple', 'Def_Rating_Placeholder',
                           'Net_Rating_Simple']
        for col in calculated_cols:
            if col in self.datos.columns:
                self.datos[col] = self.datos[col].replace([np.inf, -np.inf], 0).fillna(0)

        print("Métricas avanzadas calculadas.")

    def calcular_metricas(self):
        """Orquesta el cálculo de totales y luego métricas avanzadas."""
        self._calcular_totales()
        self._calcular_metricas_avanzadas()
        self.datos_con_metricas = self.datos.copy()  # Guardar el resultado final
        return self.datos_con_metricas  # Devolver copia

    def obtener_datos_con_metricas(self):
        """Devuelve el DataFrame con todas las métricas calculadas."""
        if self.datos_con_metricas is None:
            print("Advertencia: Las métricas aún no se han calculado. Llamando a calcular_metricas()...")
            self.calcular_metricas()
        return self.datos_con_metricas.copy() if self.datos_con_metricas is not None else None
