class Alineacion:
    def __init__(self, datos, tipo_ali="equilibrada"):
        """
        Inicializa la clase con los datos de los jugadores y el tipo de alineación.
        :param datos: DataFrame con los datos de los jugadores, incluyendo las métricas.
        :param tipo_ali: Tipo de alineación ('ofensiva', 'defensiva', 'equilibrada').
        """
        self.datos = datos.copy()  # Copia de los datos de los jugadores
        self.tipo_ali = tipo_ali  # Tipo de alineación (por defecto es 'equilibrada')

    def obtener_mejor_jugador_por_posicion(self, posicion):
        """
        Obtiene el mejor jugador para una posición dada (base, escolta, alero, ala-pívot, pívot).
        :param posicion: La posición para la cual se desea obtener al mejor jugador.
        :return: El jugador seleccionado para la posición.
        """
        if posicion == "PG":  # Base
            # Filtrar jugadores que juegan de base (PG)
            base = self.datos[self.datos['Pos'] == 'PG']
            if self.tipo_ali == 'ofensiva':
                mejor_base = base.sort_values(by='Off_Rating', ascending=False).head(1)  # Usamos Off_Rating
            elif self.tipo_ali == 'defensiva':
                mejor_base = base.sort_values(by='Def_Rating', ascending=False).head(1)  # Usamos Def_Rating
            else:  # Equilibrada
                mejor_base = base.sort_values(by='EFF/MIN', ascending=False).head(1)  # Usamos EFF/MIN
            return mejor_base

        elif posicion == "SG":  # Escolta
            # Filtrar jugadores que juegan de escolta (SG)
            escolta = self.datos[self.datos['Pos'] == 'SG']
            if self.tipo_ali == 'ofensiva':
                mejor_escolta = escolta.sort_values(by='Off_Rating', ascending=False).head(1)  # Usamos Off_Rating
            elif self.tipo_ali == 'defensiva':
                mejor_escolta = escolta.sort_values(by='Def_Rating', ascending=False).head(1)  # Usamos Def_Rating
            else:  # Equilibrada
                mejor_escolta = escolta.sort_values(by='EFF/MIN', ascending=False).head(1)  # Usamos EFF/MIN
            return mejor_escolta

        elif posicion == "SF":  # Alero
            # Filtrar jugadores que juegan de alero (SF)
            alero = self.datos[self.datos['Pos'] == 'SF']
            if self.tipo_ali == 'ofensiva':
                mejor_alero = alero.sort_values(by='Off_Rating', ascending=False).head(1)  # Usamos Off_Rating
            elif self.tipo_ali == 'defensiva':
                mejor_alero = alero.sort_values(by='Def_Rating', ascending=False).head(1)  # Usamos Def_Rating
            else:  # Equilibrada
                mejor_alero = alero.sort_values(by='EFF/MIN', ascending=False).head(1)  # Usamos EFF/MIN
            return mejor_alero

        elif posicion == "PF":  # Ala-pívot
            # Filtrar jugadores que juegan de ala-pívot (PF)
            ala_pivot = self.datos[self.datos['Pos'] == 'PF']
            if self.tipo_ali == 'ofensiva':
                mejor_ala_pivot = ala_pivot.sort_values(by='Off_Rating', ascending=False).head(1)  # Usamos Off_Rating
            elif self.tipo_ali == 'defensiva':
                mejor_ala_pivot = ala_pivot.sort_values(by='Def_Rating', ascending=False).head(1)  # Usamos Def_Rating
            else:  # Equilibrada
                mejor_ala_pivot = ala_pivot.sort_values(by='EFF/MIN', ascending=False).head(1)  # Usamos EFF/MIN
            return mejor_ala_pivot

        elif posicion == "C":  # Pívot
            # Filtrar jugadores que juegan de pívot (C)
            pivot = self.datos[self.datos['Pos'] == 'C']
            if self.tipo_ali == 'ofensiva':
                mejor_pivot = pivot.sort_values(by='Off_Rating', ascending=False).head(1)  # Usamos Off_Rating
            elif self.tipo_ali == 'defensiva':
                mejor_pivot = pivot.sort_values(by='Def_Rating', ascending=False).head(1)  # Usamos Def_Rating
            else:  # Equilibrada
                mejor_pivot = pivot.sort_values(by='EFF/MIN', ascending=False).head(1)  # Usamos EFF/MIN
            return mejor_pivot

        else:
            raise ValueError("Posición no válida. Debe ser 'PG', 'SG', 'SF', 'PF' o 'C'.")

    def crear_alineacion(self):
        """
        Crea una alineación titular y una de suplentes para cada posición.
        Devuelve un diccionario con los jugadores titulares y suplentes por posición.
        """
        alineacion_titulares = {}
        alineacion_suplentes = {}

        # Crear alineación titular (por posición)
        for posicion in ['PG', 'SG', 'SF', 'PF', 'C']:
            mejor_jugador = self.obtener_mejor_jugador_por_posicion(posicion)
            alineacion_titulares[posicion] = mejor_jugador['Player'].values[0]

            # Crear suplente: seleccionamos el siguiente mejor jugador de la misma posición
            suplente = self.datos[self.datos['Pos'] == posicion].sort_values(by='Off_Rating', ascending=False).iloc[1]
            alineacion_suplentes[posicion] = suplente['Player']

        return alineacion_titulares, alineacion_suplentes
