

import pandas as pd
import numpy as np  # Necesario para np.where y np.inf


class IndicadoresDesempeño:
    """
    Calcula métricas de desempeño para jugadores a partir de sus estadísticas base.
    Añade métricas avanzadas como EFF, TS% y un rating ofensivo simple.
    """

    def __init__(self, datos_limpiados):
        """Inicializa con el DataFrame de datos ya limpios."""
        if datos_limpiados is None or datos_limpiados.empty:
            raise ValueError("Se requiere un DataFrame de datos limpios no vacío.")

        # Define las columnas base necesarias para los cálculos
        required_base = ['Player', 'Pos', 'G', 'MP', 'PTS', 'AST', 'TRB', 'STL', 'BLK',
                         'TOV', 'FG', 'FGA', 'FT', 'FTA', '3P']
        missing_base = [col for col in required_base if col not in datos_limpiados.columns]
        if missing_base:
            raise ValueError(f"Faltan columnas base necesarias en datos_limpiados: {', '.join(missing_base)}")

        self.datos = datos_limpiados.copy()
        self.datos_con_metricas = None  # Se rellenará después de los cálculos

    def _calcular_totales(self):
        """Paso 1: Convierte estadísticas por partido a totales de temporada."""
        print("Calculando estadísticas totales...")
        # Lista de columnas a convertir (multiplicando por partidos jugados 'G')
        stats_per_game_cols = ['PTS', 'AST', 'TRB', 'STL', 'BLK', 'TOV', 'FG', 'FGA', 'FT', 'FTA', 'MP', '3P']
        for col in stats_per_game_cols:
            total_col_name = f'{col}_Total'
            self.datos[total_col_name] = self.datos[col] * self.datos['G']

        # Renombra '3P_Total' a 'ThreeP_Total' para mayor claridad
        if '3P_Total' in self.datos.columns:
            self.datos.rename(columns={'3P_Total': 'ThreeP_Total'}, inplace=True)

        # Verifica que se hayan creado las columnas totales esenciales
        required_totals = ['PTS_Total', 'TRB_Total', 'AST_Total', 'STL_Total', 'BLK_Total',
                           'FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'TOV_Total', 'MP_Total']
        missing_totals = [col for col in required_totals if col not in self.datos.columns]
        if missing_totals:
            raise RuntimeError(f"Fallo al calcular columnas totales esenciales: {missing_totals}")
        print("Estadísticas totales calculadas.")

    def _calcular_metricas_avanzadas(self):
        """Paso 2: Calcula métricas avanzadas (EFF, TS%, etc.) usando los totales."""
        required_for_advanced = ['FGA_Total', 'FG_Total', 'FTA_Total', 'FT_Total', 'PTS_Total', 'TRB_Total',
                                 'AST_Total', 'STL_Total', 'BLK_Total', 'TOV_Total', 'MP_Total']
        if self.datos is None or not all(col in self.datos.columns for col in required_for_advanced):
            missing = [col for col in required_for_advanced if col not in self.datos.columns]
            raise RuntimeError(f"Faltan columnas totales para calcular métricas avanzadas: {missing}")

        print("Calculando métricas avanzadas (EFF, TS%, Ratings)...")

        # Fórmula de Efficiency (EFF)
        missed_fg = self.datos['FGA_Total'] - self.datos['FG_Total']
        missed_ft = self.datos['FTA_Total'] - self.datos['FT_Total']
        self.datos['EFF'] = (self.datos['PTS_Total'] + self.datos['TRB_Total'] + self.datos['AST_Total'] +
                             self.datos['STL_Total'] + self.datos['BLK_Total'] -
                             missed_fg - missed_ft - self.datos['TOV_Total'])

        # EFF por minuto, evitando división por cero
        self.datos['EFF/MIN'] = np.where(self.datos['MP_Total'] > 0, self.datos['EFF'] / self.datos['MP_Total'], 0)

        # True Shooting Percentage (TS%), evitando división por cero
        denominador_ts = 2 * (self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'])
        self.datos['TS%'] = np.where(denominador_ts > 0, self.datos['PTS_Total'] / denominador_ts, 0)

        # Effective Field Goal Percentage (eFG%), usando .get por si no hay datos de triples
        denominador_efg = self.datos['FGA_Total']
        threeP_total = self.datos.get('ThreeP_Total', 0)  # Si 'ThreeP_Total' no existe, usa 0
        self.datos['eFG%_calculated'] = np.where(denominador_efg > 0,
                                                 (self.datos['FG_Total'] + 0.5 * threeP_total) / denominador_efg,
                                                 0)

        # Rating Ofensivo Simple (puntos por 100 posesiones estimadas)
        posesiones_estimadas = self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'] + self.datos['TOV_Total']
        posesiones_estimadas = posesiones_estimadas.replace([np.inf, -np.inf], 0).fillna(0)  # Limpieza previa
        self.datos['Off_Rating_Simple'] = np.where(posesiones_estimadas > 0,
                                                   (self.datos['PTS_Total'] / posesiones_estimadas) * 100,
                                                   0)
        # Ratings defensivo y neto como placeholders (no son fórmulas reales)
        self.datos['Def_Rating_Placeholder'] = 100 - self.datos['Off_Rating_Simple']
        self.datos['Net_Rating_Simple'] = self.datos['Off_Rating_Simple'] - self.datos['Def_Rating_Placeholder']

        print("Métricas avanzadas calculadas.")

    def _calcular_volumen_defensivo(self):
        """Paso 3: Calcula una métrica simple sumando robos y tapones totales."""
        if 'STL_Total' not in self.datos.columns or 'BLK_Total' not in self.datos.columns:
            print("Advertencia: No se puede calcular DEF_VOLUME_Total.")
            self.datos['DEF_VOLUME_Total'] = 0
            return

        print("Calculando métrica de volumen defensivo (STL_Total + BLK_Total)...")
        # Suma de robos y tapones totales
        self.datos['DEF_VOLUME_Total'] = self.datos['STL_Total'].fillna(0) + self.datos['BLK_Total'].fillna(0)
        print("Métrica de volumen defensivo calculada.")

    def _limpiar_metricas_finales(self):
        """Paso 4: Reemplaza valores infinitos (inf) o nulos (NaN) con 0 en las métricas calculadas."""
        print("Limpiando Inf/NaN en métricas finales...")
        # Lista de todas las columnas que se han calculado
        calculated_cols = ['EFF', 'EFF/MIN', 'TS%', 'eFG%_calculated', 'Off_Rating_Simple',
                           'Def_Rating_Placeholder', 'Net_Rating_Simple', 'DEF_VOLUME_Total']
        total_cols = [col for col in self.datos.columns if col.endswith('_Total')]
        all_potential_cols = calculated_cols + total_cols

        for col in all_potential_cols:
            if col in self.datos.columns:
                # Solo limpia si la columna es numérica
                if pd.api.types.is_numeric_dtype(self.datos[col]):
                    self.datos[col] = self.datos[col].replace([np.inf, -np.inf], 0).fillna(0)
        print("Limpieza de métricas finales completada.")

    def calcular_metricas(self):
        """
        Orquesta todos los pasos:
        1. Calcular totales.
        2. Calcular métricas avanzadas.
        3. Calcular volumen defensivo.
        4. Limpiar resultados.
        """
        self._calcular_totales()
        self._calcular_metricas_avanzadas()
        self._calcular_volumen_defensivo()
        self._limpiar_metricas_finales()
        self.datos_con_metricas = self.datos.copy()  # Guarda el resultado final

        if 'DEF_VOLUME_Total' not in self.datos_con_metricas.columns:
            print("Advertencia CRÍTICA: La métrica 'DEF_VOLUME_Total' no se pudo calcular.")
        return self.datos_con_metricas

    def obtener_datos_con_metricas(self):
        """Devuelve el DataFrame final con todas las métricas."""
        if self.datos_con_metricas is None:
            print("Advertencia: Las métricas aún no se han calculado. Llamando a calcular_metricas()...")
            self.calcular_metricas()
        return self.datos_con_metricas.copy() if self.datos_con_metricas is not None else None

