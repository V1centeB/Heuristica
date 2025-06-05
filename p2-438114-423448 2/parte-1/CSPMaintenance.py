import sys
from collections import defaultdict
from functools import partial

from constraint import Problem


def read_input_file(file_path):

    data = {}
    with open(file_path, 'r') as file:
        lines = file.readlines()

        # Leer el número de franjas de tiempo
        data['slots_tiempo'] = int(lines[0].strip())

        # Leer dimensiones de la matriz
        data['matriz'] = tuple(map(int, lines[1].strip().split('x')))

        # Procesar posiciones de talleres estándar y especializados
        data['taller_std'] = [tuple(map(int, pos.strip('()').split(',')))
                              for pos in lines[2].strip().split(':')[1].split()]
        data['taller_spc'] = [tuple(map(int, pos.strip('()').split(',')))
                              for pos in lines[3].strip().split(':')[1].split()]

        # Procesar posiciones de parkings
        data['parkings'] = [tuple(map(int, pos.strip('()').split(',')))
                            for pos in lines[4].strip().split(':')[1].split()]

        # Leer y procesar los aviones
        airplanes = []
        for line in lines[5:]:
            if line.strip():
                airplane = line.strip().split('-')
                if len(airplane) == 5:
                    # Guardar la información de cada avión
                    airplanes.append({
                        'id': int(airplane[0]),
                        'type': airplane[1],
                        'order': airplane[2],
                        'tareas_t1': int(airplane[3]),
                        'tareas_t2': int(airplane[4])
                    })
        data['airplanes'] = airplanes

    return data

def inicializacion_modelo_CSP(data):
    problem = Problem()
    for airplane in data['airplanes']:
        for t in range(data['slots_tiempo']):
            # Crear una variable para cada avión en cada franja horaria
            variable_name = f"airplane_{airplane['id']}_t{t}"
            # Dominio: cualquier taller o parking
            domain = data['taller_std'] + data['taller_spc'] + data['parkings']
            problem.addVariable(variable_name, domain)
    return problem

# ---------------- Funciones de restricciones ----------------

def capacidad_talleres(positions, airplane_types):
    talleres = defaultdict(list)
    for pos, airplane_type in zip(positions, airplane_types):
        talleres[pos].append(airplane_type)

    for aviones in talleres.values():
        # Validar que no haya más de 2 aviones en un taller
        if len(aviones) > 2:
            return False
        # Validar que no haya más de 1 avión JUMBO
        if aviones.count("JMB") > 1:
            return False
        # Validar combinaciones específicas de tipos de aviones
        if len(aviones) == 2 and aviones != ["STD", "STD"] and not ("JMB" in aviones and "STD" in aviones):
            return False
    return True


def implementacion_capacidad_talleres(airplane_types):

    def constraint(*positions):
        return capacidad_talleres(positions, airplane_types)
    return constraint


def tareas_t2_SPC(problem, data):
    pos_spc = data['taller_spc']
    airplanes = data['airplanes']

    for airplane in airplanes:
        tareas_t2 = airplane['tareas_t2']

        if tareas_t2 > 0:
            for t in range(tareas_t2):
                if t < data['slots_tiempo']:
                    variable_name = f"airplane_{airplane['id']}_t{t}"

                    # Asegurarse de que la variable existe antes de aplicar la restricción
                    if variable_name in problem._variables:
                        # Restringir a posiciones de talleres especializados (SPC)
                        problem.addConstraint(
                            partial(lambda pos, spc: pos in spc, spc=pos_spc),
                            [variable_name]
                        )

def movilidad_aviones(*positions):
    talleres = defaultdict(list)
    for pos in positions:
        if pos is not None:
            talleres[pos].append(pos)

    for pos, ocupantes in talleres.items():
        x, y = pos
        adjacent_positions = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

        # Si todas las posiciones adyacentes están ocupadas, falla la restricción
        if all(adj in talleres for adj in adjacent_positions):
            return False
    return True


def restriccion_adyacencia_jumbos(data):
    def no_jumbos_adyacentes(*positions):
        jumbo_positions = [pos for pos, airplane_type in zip(positions, data['airplanes']) if airplane_type['type'] == 'JMB']
        for pos in jumbo_positions:
            x, y = pos
            adjacent_positions = {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)}
            if any(adj in jumbo_positions for adj in adjacent_positions):
                return False
        return True
    return no_jumbos_adyacentes


def prioridad_tareas(slots_tiempo, airplanes, problem):
    for airplane in airplanes:
        tareas_t2 = airplane['tareas_t2']
        tareas_t1 = airplane['tareas_t1']
        for t in range(tareas_t2):
            if t < slots_tiempo:
                variable_name = f"airplane_{airplane['id']}_t{t}"
                problem.addConstraint(
                    lambda pos: pos in data['taller_spc'],
                    [variable_name]
                )
        for t in range(tareas_t2, tareas_t2 + tareas_t1):
            if t < slots_tiempo:
                variable_name = f"airplane_{airplane['id']}_t{t}"
                problem.addConstraint(
                    lambda pos: pos in data['taller_std'],
                    [variable_name]
                )


def restriccion_parkings(problem, data):

    parkings = data['parkings']
    taller_std = data['taller_std']
    taller_spc = data['taller_spc']

    for airplane in data['airplanes']:
        tareas_t2 = airplane['tareas_t2']
        tareas_t1 = airplane['tareas_t1']

        for t in range(data['slots_tiempo']):
            variable = f"airplane_{airplane['id']}_t{t}"

            if t < tareas_t2:
                problem.addConstraint(
                    lambda pos, spc=taller_spc: pos in spc,
                    [variable]
                )
            elif t < tareas_t2 + tareas_t1:
                problem.addConstraint(
                    lambda pos, std=taller_std: pos in std,
                    [variable]
                )
            else:
                # Restricción: si no tiene tareas pendientes, puede estar en PRK
                problem.addConstraint(
                    lambda pos, prk=parkings: pos in prk,
                    [variable]
                )


def implementacion_restricciones(problem, data):

    airplanes = data['airplanes']
    slots_tiempo = data['slots_tiempo']

    # Restricción 2: Máxima capacidad de talleres
    for t in range(slots_tiempo):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        airplane_types = [airplane['type'] for airplane in airplanes]
        problem.addConstraint(implementacion_capacidad_talleres(airplane_types), vars_at_time)

    # Restricción 3: Realización de tareas T2 en taller SPC
    tareas_t2_SPC(problem, data)

    # Restricción 4: Asegurar el orden de tareas T2 antes de T1
    prioridad_tareas(slots_tiempo, airplanes, problem)

    # Restricción 5: Movilidad general de aviones
    for t in range(slots_tiempo):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        problem.addConstraint(movilidad_aviones, vars_at_time)

    # Restricción 6: Prohibir aviones JUMBO adyacentes
    for t in range(slots_tiempo):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        problem.addConstraint(restriccion_adyacencia_jumbos(data), vars_at_time)

    restriccion_parkings(problem, data)


def write_output_file(output_file, solutions, data):

    with open(output_file, 'w') as file:
        file.write(f"N. Sol: {len(solutions)}\n")
        for i, solution in enumerate(solutions[:100], start=1):
            file.write(f"\nSolución {i}:\n")
            for airplane in data['airplanes']:
                positions = [solution[f"airplane_{airplane['id']}_t{t}"] for t in range(data['slots_tiempo'])]
                positions_str = ', '.join([
                    f"{'SPC' if pos in data['taller_spc'] else 'STD' if pos in data['taller_std'] else 'PRK'}{pos}"
                    for pos in positions
                ])
                file.write(
                    f"{airplane['id']}-{airplane['type']}-{airplane['order']}-{airplane['tareas_t1']}-{airplane['tareas_t2']}: {positions_str}\n")


def soluciones_unicas(solutions, data):
    unique_solutions = set()
    filtered_solutions = []

    for solution in solutions:
        normalized_solution = []
        for airplane in sorted(data['airplanes'], key=lambda x: x['id']):
            positions = tuple(sorted(
                solution[f"airplane_{airplane['id']}_t{t}"] for t in range(data['slots_tiempo'])
            ))
            normalized_solution.append((airplane['id'], positions))
        normalized_solution = tuple(sorted(normalized_solution))
        if normalized_solution not in unique_solutions:
            unique_solutions.add(normalized_solution)
            filtered_solutions.append(solution)

    return filtered_solutions


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 CSPMaintenance.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    data = read_input_file(input_file)

    # Inicializar modelo CSP
    model_CSP = inicializacion_modelo_CSP(data)

    # Aplicar restricciones
    implementacion_restricciones(model_CSP, data)

    # Obtener soluciones
    solutions = model_CSP.getSolutions()
    solutions = soluciones_unicas(solutions, data)

    # Guardar soluciones en archivo de salida
    output_file = input_file.replace(".txt", ".csv")
    write_output_file(output_file, solutions, data)
    print(f"Solutions written to {output_file}")
