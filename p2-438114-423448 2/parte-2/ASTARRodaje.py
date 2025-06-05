import heapq
import os
import sys
import time
from itertools import product

MOVIMIENTOS = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]  

class Estado:
    def __init__(self, posiciones, camino, costo_acumulado, heuristica):
        self.posiciones = tuple(posiciones)
        self.camino = camino
        self.costo_acumulado = costo_acumulado
        self.heuristica = heuristica
        self.costo_estimado = self.costo_acumulado + self.heuristica

    def __lt__(self, otro):
        return self.costo_estimado < otro.costo_estimado

def leer_mapa(archivo):
    with open(archivo, 'r') as f:
        n = int(f.readline().strip())
        aviones = []

        for _ in range(n):
            init_str, goal_str = f.readline().split()
            init = tuple(map(int, init_str.strip('()').split(',')))
            goal = tuple(map(int, goal_str.strip('()').split(',')))
            aviones.append((init, goal))

        mapa = [line.strip().split(';') for line in f.readlines()]

    return aviones, mapa

def es_valido(pos, mapa, ocupadas, posiciones_anteriores, idx, movimientos):
    fila, col = pos

    # Verifica límites y obstáculos
    if not (0 <= fila < len(mapa) and 0 <= col < len(mapa[0])):
        return False
    if mapa[fila][col] == 'G':
        return False

    # Evita colisiones con otros aviones
    if pos in ocupadas:
        return False

    # Evita cruces simultáneos con otros aviones
    for i, (prev_pos, mov_anterior) in enumerate(zip(posiciones_anteriores, movimientos)):
        if i != idx:
            if prev_pos == pos:
                return False
            if prev_pos == (fila - mov_anterior[0], col - mov_anterior[1]) and pos == posiciones_anteriores[i]:
                return False

    # Evita esperas innecesarias en celdas amarillas
    if mapa[fila][col] == 'A' and pos == posiciones_anteriores[idx]:
        return False

    return True

#Distancia Manhattan
def heuristica1(posiciones, destinos, mapa):
    return sum(abs(x1 - x2) + abs(y1 - y2) for (x1, y1), (x2, y2) in zip(posiciones, destinos))

def floyd_warshall(mapa):
    filas = len(mapa)
    columnas = len(mapa[0])
    INF = float('inf')

    # Inicializa distancias
    dist = [[INF] * (filas * columnas) for _ in range(filas * columnas)]

    for i in range(filas):
        for j in range(columnas):
            if mapa[i][j] != 'G':  # Si no es obstáculo
                idx = i * columnas + j
                dist[idx][idx] = 0
                for dx, dy in MOVIMIENTOS[:-1]:  # Movimientos válidos (sin espera)
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < filas and 0 <= nj < columnas and mapa[ni][nj] != 'G':
                        nidx = ni * columnas + nj
                        dist[idx][nidx] = 1

    # Aplica Floyd-Warshall
    for k in range(filas * columnas):
        for i in range(filas * columnas):
            for j in range(filas * columnas):
                dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])

    return dist

def heuristica2(posiciones, destinos, mapa):
    filas, columnas = len(mapa), len(mapa[0])
    dist = floyd_warshall(mapa)
    
    def coord_to_index(x, y):
        return x * columnas + y

    costo = 0
    for (x1, y1), (x2, y2) in zip(posiciones, destinos):
        idx1 = coord_to_index(x1, y1)
        idx2 = coord_to_index(x2, y2)
        costo += dist[idx1][idx2]

    return costo

def sucesores(estado, mapa, destinos, heuristica):
    sucesores = []
    posiciones_anteriores = estado.posiciones

    # Genera todas las combinaciones posibles de movimientos para los aviones
    for movimientos in product(MOVIMIENTOS, repeat=len(estado.posiciones)):
        nuevas_pos = []
        ocupadas = set()
        valido = True
        movimiento_efectivo = False

        for idx, ((x, y), (dx, dy)) in enumerate(zip(estado.posiciones, movimientos)):
            nueva_pos = (x + dx, y + dy)

            # Mantiene la posición si ya se alcanzó el destino
            if (x, y) == destinos[idx]:
                nueva_pos = (x, y)

            # Verifica validez del movimiento actual
            if not es_valido(nueva_pos, mapa, ocupadas, posiciones_anteriores, idx, movimientos):
                valido = False
                break

            ocupadas.add(nueva_pos)
            nuevas_pos.append(nueva_pos)

            if nueva_pos != (x, y):
                movimiento_efectivo = True

        # Solo añade estados válidos como sucesores
        if valido:
            costo = estado.costo_acumulado + 1
            h = heuristica(nuevas_pos, destinos, mapa)
            sucesores.append(Estado(nuevas_pos, estado.camino + [nuevas_pos], costo, h))

    return [s for s in sucesores if any(p != a for p, a in zip(s.posiciones, posiciones_anteriores))] or [Estado(posiciones_anteriores, estado.camino + [posiciones_anteriores], estado.costo_acumulado + 1, estado.heuristica)]

def a_estrella(aviones, mapa, heuristica):
    posiciones, destinos = zip(*aviones)
    heuristica_inicial = heuristica(posiciones, destinos, mapa)
    inicial = Estado(posiciones, [posiciones], 0, heuristica_inicial)

    frontera = [(inicial.costo_estimado, inicial)]
    visitados = {}
    nodos_expandidos = 0

    while frontera:
        _, estado = heapq.heappop(frontera)
        nodos_expandidos += 1

        if estado.posiciones == destinos:
            return estado.camino, estado.costo_acumulado, heuristica_inicial, nodos_expandidos

        clave = estado.posiciones
        if clave in visitados and visitados[clave] <= estado.costo_acumulado:
            continue
        visitados[clave] = estado.costo_acumulado

        for sucesor in sucesores(estado, mapa, destinos, heuristica):
            heapq.heappush(frontera, (sucesor.costo_estimado, sucesor))

    return None, None, heuristica_inicial, nodos_expandidos

def imprimir_movimientos(camino):
    for t, posiciones in enumerate(camino):
        print(f"Tiempo {t}: {posiciones}")

def traducir_camino(trayectoria):
    movimientos = []
    for i in range(1, len(trayectoria)):
        x1, y1 = trayectoria[i-1]
        x2, y2 = trayectoria[i]

        if (x2, y2) == (x1, y1):
            movimientos.append("w")  # Espera
        elif x2 == x1 - 1 and y2 == y1:
            movimientos.append("↑")  # Arriba
        elif x2 == x1 + 1 and y2 == y1:
            movimientos.append("↓")  # Abajo
        elif x2 == x1 and y2 == y1 + 1:
            movimientos.append("→")  # Derecha
        elif x2 == x1 and y2 == y1 - 1:
            movimientos.append("←")  # Izquierda

    return movimientos

def escribir_solucion(nombre_archivo, camino, costo, tiempo, heuristica_inicial, nodos_expandidos, heuristica_num):
    directorio = "./ASTAR-tests"
    os.makedirs(directorio, exist_ok=True)

    nombre_base = os.path.basename(nombre_archivo)  # Extrae solo el nombre base
    output_file = os.path.join(directorio, f"{nombre_base}-{heuristica_num}.output")
    stat_file = os.path.join(directorio, f"{nombre_base}-{heuristica_num}.stat")

    # Escribe la solución en el archivo .output
    with open(output_file, "w", encoding="utf-8") as f:
        for idx in range(len(camino[0])):  # Para cada avión
            trayectoria = [posiciones[idx] for posiciones in camino]  # Posiciones del avión en cada paso
            movimientos = traducir_camino(trayectoria)
            linea = " ".join([f"({x},{y}) {m}" for (x, y), m in zip(trayectoria, movimientos + [""])]);
            f.write(linea.strip() + "\n")

    # Escribe estadísticas en el archivo .stat
    with open(stat_file, "w", encoding="utf-8") as f:
        f.write(f"Tiempo total: {tiempo:.2f}s\n")
        f.write(f"Makespan: {costo}\n")
        f.write(f"h inicial: {heuristica_inicial}\n")
        f.write(f"Nodos expandidos: {nodos_expandidos}\n")

def main():
    if len(sys.argv) < 3:
        print("Uso: python ASTARRodaje.py <path mapa.csv> <num-h>")
        sys.exit(1)

    mapa_file = sys.argv[1]
    heuristica_num = int(sys.argv[2])

    if heuristica_num == 1:
        heuristica = heuristica1
    elif heuristica_num == 2:
        heuristica = heuristica2
    else:
        print("Heurística inválida. Use 1 para Heurística 1 (Distancia Manhattan) o 2 para Heurística 2 (Algoritmo Floyd-Warshall).")
        sys.exit(1)

    aviones, mapa = leer_mapa(mapa_file)

    inicio = time.time()
    camino, costo, heuristica_inicial, nodos_expandidos = a_estrella(aviones, mapa, heuristica)
    fin = time.time()

    if camino:
        # Guarda solución y estadísticas en los archivos
        escribir_solucion(mapa_file, camino, costo, fin - inicio, heuristica_inicial, nodos_expandidos, heuristica_num)
        # Genera nombres de archivo
        directorio = "./ASTAR-tests"
        nombre_base = os.path.basename(mapa_file)
        output_file = os.path.join(directorio, f"{nombre_base}-{heuristica_num}.output")
        stat_file = os.path.join(directorio, f"{nombre_base}-{heuristica_num}.stat")

        print(f"Se han guardado las estadísticas en {stat_file}")
        print(f"Se ha guardado la solución en {output_file}")
    else:
        print("No se encontró ninguna solución")


if __name__ == "__main__":
    main()
