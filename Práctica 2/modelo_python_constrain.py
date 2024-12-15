#! /usr/bin/env python
# -*- coding: utf-8 -*-
from constraint import Problem, AllDifferentConstraint
from inputs_file import leer_fichero, escribir_csv, argumentos_programa

def parse_input(buffer):
    """
    Parsea el contenido del archivo de entrada y devuelve los datos necesarios.
    """
    franjas_horarias = int(buffer[0])
    talleres_std = [tuple(map(int, pos.split(','))) for pos in buffer[2].split()]
    talleres_spc = [tuple(map(int, pos.split(','))) for pos in buffer[3].split()]
    parkings = [tuple(map(int, pos.split(','))) for pos in buffer[4].split()]
    aviones = []
    for line in buffer[5:]:
        parts = line.split('-')
        aviones.append({
            'ID': parts[0],
            'TIPO': parts[1],
            'RESTR': parts[2] == 'T',
            'T1': int(parts[3]),
            'T2': int(parts[4])
        })
    return franjas_horarias, talleres_std, talleres_spc, parkings, aviones

def csp_aircraft_maintenance(buffer, output_path):
    """
    Modelo y resolución del problema CSP usando python-constraint.
    """
    franjas_horarias, talleres_std, talleres_spc, parkings, aviones = parse_input(buffer)
    problem = Problem()

    # Declaración de variables y dominios optimizados
    for i, avion in enumerate(aviones):
        for h in range(franjas_horarias):
            if avion['T2'] > 0:  # Aviones con tareas tipo 2 deben ir a talleres SPC
                problem.addVariable((i, h), talleres_spc)
            else:  # Otros aviones pueden estar en talleres STD, SPC o parkings
                problem.addVariable((i, h), talleres_std + talleres_spc + parkings)

    # Restricciones
    # 1. Cada avión en una única posición por franja horaria
    for h in range(franjas_horarias):
        problem.addConstraint(AllDifferentConstraint(), [(i, h) for i in range(len(aviones))])

    # 2. Capacidad de talleres: máximo 2 aviones por taller, solo 1 tipo JMB
    def capacity_constraint(*positions):
        count = {}
        for pos in positions:
            if pos not in count:
                count[pos] = {'total': 0, 'JMB': 0}
            count[pos]['total'] += 1
        for i, pos in enumerate(positions):
            if aviones[i]['TIPO'] == 'JMB':
                count[pos]['JMB'] += 1
        return all(info['total'] <= 2 and info['JMB'] <= 1 for info in count.values())

    for h in range(franjas_horarias):
        problem.addConstraint(capacity_constraint, [(i, h) for i in range(len(aviones))])

    # Resolución: obtener todas las soluciones
    solutions = problem.getSolutions()  # Obtiene todas las soluciones factibles
    print(f"Number of solutions: {len(solutions)}")

    if solutions:
        # Escribir todas las soluciones al archivo CSV
        for idx, solution in enumerate(solutions):
            escribir_csv(solution, franjas_horarias, len(aviones), idx + 1, output_path)
    else:
        print("No se encontraron soluciones factibles.")

if __name__ == "__main__":
    path_fichero = argumentos_programa()
    buffer = leer_fichero(path_fichero)
    csp_aircraft_maintenance(buffer, path_fichero)