"""Este módulo contiene todo lo refentea a escribir y leer de los archivos y coger los argumentos que se ponen por terminal"""

import sys
import csv
import os


def escribir_csv(solucion: dict, filas: int, columnas: int, num_sols: int, path_fichero: str) -> None:
    datos = []
    datos.append(['N. Sol:', num_sols])

    # Creacion de la lista con todos los elementos en su interior
    for i in range(filas):
        datos.append([])
        for j in range(columnas):
            datos[i + 1].append('-')

    # Cambiar los valores necesarios en las posiciones necesarios
    if solucion is not None:
        for i in solucion:
            fila_csv = solucion[i][0]
            columna_csv = solucion[i][1] - 1
            datos[fila_csv][columna_csv] = i

    tupla_ruta = os.path.splitext(path_fichero)
    path_fichero = f"{tupla_ruta[0]}.csv"

    try:
        with open(path_fichero, mode='w', newline='') as archivo_csv:
            # Crea un objeto escritor CSV
            escritor_csv = csv.writer(archivo_csv, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)

            # Escribe los datos en el archivo CSV
            escritor_csv.writerows(datos)
    except FileNotFoundError:
        print("El archivo no se encontró.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        sys.exit(1)

    print(f"Los datos han sido escritos en el archivo CSV: {path_fichero}")


def argumentos_programa() -> str:
    """Funcion para obtener los argumentos del programa"""
    if len(sys.argv) != 2:
        print("Uso: python programa.py path_fichero")
        sys.exit(1)
    return sys.argv[1]


def leer_fichero(path_fichero: str) -> None:
    try:
        # Abre el archivo en modo lectura
        with open(path_fichero, 'r') as archivo:
            # .strip para quitarse los saltos de linea
            buffer = [linea.strip() for linea in archivo.readlines()]
            return buffer
    except FileNotFoundError:
        print("El archivo no se encontró.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        sys.exit(1)