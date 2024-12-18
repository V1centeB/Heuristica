import sys
from file_reader import read_input_file
from constraint import Problem
from collections import Counter
from functools import partial


def initialize_csp_model(data):
    """Initializes the CSP model with variables and domains."""
    problem = Problem()
    for airplane in data['airplanes']:
        for t in range(data['time_slots']):
            # Cada variable es la posición del avión en una franja horaria
            problem.addVariable(f"airplane_{airplane['id']}_t{t}",
                                data['std_workshops'] + data['spc_workshops'] + data['parkings'])
    return problem


# Funciones de restricciones
def max_two_and_one_jumbo(*positions, airplane_types):
    from collections import Counter
    counter = Counter(positions)

    for pos, count in counter.items():
        if count > 2:  # Máximo 2 aviones en la misma posición
            return False
        jumbo_count = sum(1 for i, p in enumerate(positions) if p == pos and airplane_types[i] == "JMB")
        if jumbo_count > 1:  # Máximo 1 JUMBO
            return False
    return True

def ensure_t2_in_spc(problem, data):
    """
    Restricción: Si un avión tiene tareas T2 (especialista),
    al menos una franja horaria debe asignarse a un taller especialista (SPC).
    Además, las tareas T2 no pueden realizarse en talleres estándar.
    """
    spc_positions = data['spc_workshops']
    airplanes = data['airplanes']

    for airplane in airplanes:
        if airplane['tasks_t2'] > 0:  # Solo para aviones con tareas tipo 2
            # Variables de posición para todas las franjas horarias
            task_vars = [f"airplane_{airplane['id']}_t{t}" for t in range(data['time_slots'])]

            # Asegurar que al menos una posición esté en SPC
            problem.addConstraint(
                lambda *positions: any(pos in spc_positions for pos in positions),
                task_vars
            )

            # Restringir las primeras tareas T2 a talleres SPC
            for t in range(min(airplane['tasks_t2'], data['time_slots'])):  # Evitar índice fuera de rango
                problem.addConstraint(
                    lambda pos: pos in spc_positions,
                    [f"airplane_{airplane['id']}_t{t}"]
                )


def ensure_adjacent_vacancy(*positions):
    """
    Restricción: Si una posición está ocupada, al menos una posición adyacente debe estar vacía.
    """
    occupied_positions = set(positions)  # Todas las posiciones asignadas en esta franja horaria

    for pos in occupied_positions:
        if pos is None:  # Si no hay avión asignado a esta posición
            continue
        x, y = pos  # Desempaquetar coordenadas (x, y)
        adjacent_positions = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

        # Verificar si al menos una posición adyacente no está ocupada
        if all(adj in occupied_positions for adj in adjacent_positions):
            return False  # Si todas las posiciones adyacentes están ocupadas, restricción violada
    return True  # La restricción se cumple


def only_one_jumbo(*positions):
    """Restricción: Solo 1 avión JUMBO por taller."""
    from collections import Counter
    return all(count <= 1 for count in positions if count == "JMB")


def no_adjacent_positions(p1, p2):
    """Restricción: Posiciones no adyacentes para maniobrabilidad."""
    x1, y1 = p1
    x2, y2 = p2
    return abs(x1 - x2) > 1 or abs(y1 - y2) > 1


def add_constraints(problem, data):
    """
    Adds all the constraints to the problem.
    """
    airplanes = data['airplanes']
    time_slots = data['time_slots']

    # Restricción 1: Máximo 2 aviones y solo 1 JUMBO por taller en una franja horaria
    for t in range(time_slots):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        airplane_types = [airplane['type'] for airplane in airplanes]
        problem.addConstraint(
            lambda *positions: max_two_and_one_jumbo(*positions, airplane_types=airplane_types),
            vars_at_time
        )

    # Restricción 2: JUMBO no pueden compartir taller
    for t in range(time_slots):
        jumbo_vars = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes if airplane['type'] == "JMB"]
        problem.addConstraint(lambda *positions: len(set(positions)) == len(positions), jumbo_vars)

    # Restricción 3: Tareas T2 en SPC
    ensure_t2_in_spc(problem, data)

    # Restricción 3: Posiciones adyacentes para maniobrabilidad
    for t in range(time_slots):
        for i, airplane1 in enumerate(airplanes):
            for j, airplane2 in enumerate(airplanes):
                if i < j:
                    var1 = f"airplane_{airplane1['id']}_t{t}"
                    var2 = f"airplane_{airplane2['id']}_t{t}"
                    problem.addConstraint(no_adjacent_positions, [var1, var2])

    # Restricción 5: Al menos una posición adyacente debe estar vacía
    for t in range(time_slots):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        problem.addConstraint(ensure_adjacent_vacancy, vars_at_time)

    # Restricción 6: Los aviones JUMBO no pueden ocupar posiciones adyacentes
    jumbos = [airplane for airplane in airplanes if airplane['type'] == "JMB"]
    for t in range(time_slots):
        for i, jumbo1 in enumerate(jumbos):
            for j, jumbo2 in enumerate(jumbos):
                if i < j:
                    var1 = f"airplane_{jumbo1['id']}_t{t}"
                    var2 = f"airplane_{jumbo2['id']}_t{t}"
                    problem.addConstraint(no_adjacent_positions, [var1, var2])

    # Restricción 4: Orden de tareas tipo 2 antes que tipo 1
    for airplane in airplanes:
        if airplane['order'] == 'T':
            for t in range(airplane['tasks_t2']):
                problem.addConstraint(
                    lambda pos: pos in data['spc_workshops'],
                    [f"airplane_{airplane['id']}_t{t}"]
                )


def write_output_file(output_file, solutions, data):
    """Writes the solutions in the desired format."""
    with open(output_file, 'w') as file:
        file.write(f"N. Sol: {len(solutions)}\n")
        for i, solution in enumerate(solutions[:100], start=1):
            file.write(f"\nSolución {i}:\n")
            for airplane in data['airplanes']:
                positions = [solution[f"airplane_{airplane['id']}_t{t}"] for t in range(data['time_slots'])]
                positions_str = ', '.join([
                    f"{'SPC' if pos in data['spc_workshops'] else 'STD' if pos in data['std_workshops'] else 'PRK'}{pos}"
                    for pos in positions
                ])
                file.write(
                    f"{airplane['id']}-{airplane['type']}-{airplane['order']}-{airplane['tasks_t1']}-{airplane['tasks_t2']}: {positions_str}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 CSPMaintenance.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    data = read_input_file(input_file)

    print("Initializing CSP model...")
    problem = initialize_csp_model(data)

    print("Adding constraints...")
    add_constraints(problem, data)

    print("Solving CSP model...")
    solutions = problem.getSolutions()
    print(f"Total solutions found: {len(solutions)}")

    # Escribir las soluciones en el archivo de salida
    output_file = input_file.replace(".txt", ".csv")
    write_output_file(output_file, solutions, data)
    print(f"Solutions written to {output_file}")
