# Optimizador de Alineaciones NBA - TFG

Sistema integral para la optimización y análisis de alineaciones de baloncesto (NBA). La aplicación permite cargar estadísticas de jugadores, definir un enfoque de optimización y generar el quinteto titular matemáticamente óptimo mediante Programación Lineal.

Además, el sistema realiza un análisis comparativo contra alineaciones reales, evalúa la sensibilidad de la solución y presenta todos los resultados a través de una **interfaz web interactiva** construida con Flask.


*(Reemplaza la URL de la imagen de arriba con una captura de pantalla de tu propia aplicación en ejecución)*

---

## Índice

- [Características Principales](#características-principales)
- [Tecnologías Utilizadas](#tecnologías-utilizadas)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Uso](#uso)
- [Descripción de los Módulos](#descripción-de-los-módulos)

## Características Principales

-   **Carga y Limpieza de Datos**: Procesa archivos CSV con estadísticas de jugadores, manejando duplicados (jugadores traspasados) y limpiando datos nulos o inconsistentes.
-   **Cálculo de Métricas Avanzadas**: A partir de estadísticas base, calcula indicadores de rendimiento clave como `EFF` (Eficiencia), `TS%` (True Shooting Percentage) y un rating ofensivo simplificado.
-   **Optimización de Quinteto Titular**: Utiliza **Programación Lineal Entera** (con la librería `PuLP`) para encontrar el quinteto titular que maximiza una métrica objetivo, cumpliendo con las restricciones posicionales.
-   **Selección de Suplentes**: Complementa el quinteto óptimo con una selección de suplentes mediante un enfoque *greedy*.
-   **Análisis Comparativo vs. Realidad**: Compara el quinteto óptimo con alineaciones reales, utilizando el **índice de Jaccard** para medir la similitud y calculando la "mejora" en diversas métricas.
-   **Análisis de Sensibilidad**: Evalúa la robustez de la solución, identificando "jugadores robustos" que aparecen consistentemente en los quintetos óptimos aunque se varíe la métrica objetivo.
-   **Interfaz Web Interactiva**: Aplicación web desarrollada con **Flask** que permite al usuario subir sus datos, configurar los parámetros y visualizar los resultados de forma clara.
-   **Visualización de Datos**: Presenta los resultados en tablas claras y a través de una comparativa visual "estilo FIFA", que normaliza las métricas en una escala de 0 a 100 para una interpretación intuitiva.

## Tecnologías Utilizadas

-   **Backend**: Python 3.x
-   **Librerías Principales**:
    -   **Flask**: Para el desarrollo del servidor y la interfaz web.
    -   **Pandas**: Para la manipulación y análisis de datos.
    -   **PuLP**: Para la modelización y resolución del problema de optimización lineal.
    -   **NumPy**: Para operaciones numéricas eficientes.
-   **Frontend**: HTML5, CSS3.

## Estructura del Proyecto
```
proyecto-nba/
├── Datos/
│   ├── NBA_2024_per_game(...).csv # Archivo de ejemplo con estadísticas
│   └── ruta_reales_csv.csv       # Archivo opcional con alineaciones reales
├── src/
│   ├── AnalisisResultados.py
│   ├── CargaDatos.py
│   ├── IndicadoresDesempeño.py
│   └── OptimizadorAlineacion.py
├── static/
│   └── style.css                 # Hoja de estilos para la web
├── templates/
│   ├── upload.html               # Plantilla de la página de carga
│   └── results.html              # Plantilla de la página de resultados
├── uploads/                        # Carpeta donde se guardan los archivos subidos
├── app.py                          # Archivo principal para ejecutar la aplicación web
└── README.md                       # Este archivo
```

## Instalación

Para ejecutar este proyecto localmente, sigue estos pasos:

1.  **Clona el repositorio**:
    ```bash
    git clone https://github.com/tu_usuario/tu_repositorio.git
    cd tu_repositorio
    ```

2.  **Crea y activa un entorno virtual** (recomendado):
    ```bash
    # En Windows
    python -m venv venv
    .\venv\Scripts\activate

    # En macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instala las dependencias**:
    ```bash
    pip install Flask pandas pulp numpy
    ```

## Uso

1.  **Prepara tus datos**:
    -   Asegúrate de que tu archivo de estadísticas de jugadores esté en formato `.csv` y se encuentre en la carpeta `Datos/`.
    -   (Opcional) Si quieres realizar la comparación, crea un archivo llamado `ruta_reales_csv.csv` en la carpeta `Datos/` con las columnas `Tm, Player1, Player2, Player3, Player4, Player5`.

2.  **Ejecuta la aplicación web**:
    Desde la carpeta raíz del proyecto, ejecuta el siguiente comando en tu terminal:
    ```bash
    python app.py
    ```

3.  **Accede a la interfaz**:
    -   Abre tu navegador web y ve a la dirección `http://127.0.0.1:5001`.
    -   Usa el formulario para subir tu archivo `.csv`.
    -   Ajusta los filtros y selecciona el enfoque de optimización.
    -   Haz clic en "Generar Alineación" para ver los resultados.

## Descripción de los Módulos

-   `app.py`: El corazón de la aplicación web. Gestiona las rutas, maneja las peticiones, orquesta la llamada a los módulos del backend y renderiza las plantillas HTML.
-   `src/CargaDatos.py`: Clase responsable de cargar el archivo CSV, realizar la limpieza inicial (manejo de duplicados, valores nulos) y validar la integridad de los datos.
-   `src/IndicadoresDesempeño.py`: Toma los datos limpios y calcula un amplio abanico de métricas avanzadas que serán la base para la optimización.
-   `src/OptimizadorAlineacion.py`: Contiene la lógica de optimización. Utiliza PuLP para resolver el problema de programación lineal y encontrar el quinteto titular óptimo.
-   `src/AnalisisResultados.py`: Clase dedicada al análisis post-optimización. Realiza la comparación numérica con equipos reales y el análisis de sensibilidad.
-   `templates/`: Carpeta con las plantillas HTML que definen la estructura de la interfaz web.
-   `static/`: Carpeta que contiene los archivos estáticos, como la hoja de estilos `style.css`.
