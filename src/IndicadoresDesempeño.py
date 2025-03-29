import pandas as pd

class IndicadoresDesempeño:
    """
    Clase para calcular diferentes métricas de desempeño de jugadores de baloncesto.
    """

    def __init__(self, datos):
        """
        Inicializa la clase con los datos de los jugadores.
        """
        self.datos = datos.copy()  # Copia de los datos originales

    def calcular_metricas(self):
        """
        Calcula diversas métricas de rendimiento para los jugadores,
        incluyendo estadísticas totales y métricas avanzadas como eficiencia y ratings.
        """
        if self.datos is not None:
            # Calcular estadísticas totales a partir de valores por partido
            self.datos['PTS_Total'] = self.datos['PTS'] * self.datos['G']
            self.datos['AST_Total'] = self.datos['AST'] * self.datos['G']
            self.datos['TRB_Total'] = self.datos['TRB'] * self.datos['G']
            self.datos['STL_Total'] = self.datos['STL'] * self.datos['G']
            self.datos['BLK_Total'] = self.datos['BLK'] * self.datos['G']
            self.datos['TOV_Total'] = self.datos['TOV'] * self.datos['G']
            self.datos['FGA_Total'] = self.datos['FGA'] * self.datos['G']
            self.datos['FG_Total'] = self.datos['FG'] * self.datos['G']
            self.datos['FTA_Total'] = self.datos['FTA'] * self.datos['G']
            self.datos['FT_Total'] = self.datos['FT'] * self.datos['G']
            self.datos['MP_Total'] = self.datos['MP'] * self.datos['G']

            # Calcular eficiencia por minuto
            self.datos['EFF/MIN'] = (
                self.datos['PTS_Total'] + self.datos['TRB_Total'] + self.datos['AST_Total'] +
                self.datos['STL_Total'] + self.datos['BLK_Total'] -
                (self.datos['FGA_Total'] - self.datos['FG_Total']) -
                (self.datos['FTA_Total'] - self.datos['FT_Total']) -
                self.datos['TOV_Total']
            ) / self.datos['MP_Total']

            # Calcular rating ofensivo y defensivo (simplificado)
            if {'PTS_Total', 'FGA_Total', 'FTA_Total', 'TOV_Total', 'MP_Total'}.issubset(self.datos.columns):
                self.datos['Off_Rating'] = (self.datos['PTS_Total'] / (
                    self.datos['FGA_Total'] + 0.44 * self.datos['FTA_Total'] + self.datos['TOV_Total'])) * 100
                self.datos['Def_Rating'] = 100 - self.datos['Off_Rating']  # Referencia, no es el cálculo real

            print("Métricas calculadas correctamente.")
        else:
            print("No hay datos cargados. Asegúrate de proporcionar un DataFrame válido.")

    def obtener_datos_con_metricas(self):
        """
        Devuelve el DataFrame con las métricas calculadas.
        """
        return self.datos
