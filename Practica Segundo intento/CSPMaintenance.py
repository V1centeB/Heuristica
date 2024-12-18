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
            variable_name = f"airplane_{airplane['id']}_t{t}"
            domain = data['std_workshops'] + data['spc_workshops'] + data['parkings']
            problem.addVariable(variable_name, domain)
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

def validate_airplanes_per_taller(positions, airplane_types):
    """
    Valida las combinaciones de aviones por taller:
    - Máximo 2 aviones por taller.
    - Permite 2 aviones STD o 1 JMB + 1 STD.
    - Prohíbe más de 1 avión JMB en el mismo taller.
    """
    from collections import defaultdict
    talleres = defaultdict(list)
    for pos, airplane_type in zip(positions, airplane_types):
        talleres[pos].append(airplane_type)
    for aviones in talleres.values():
        if len(aviones) > 2:  # No más de 2 aviones
            return False
        if aviones.count("JMB") > 1:  # No más de 1 JMB
            return False
        if len(aviones) == 2 and aviones != ["STD", "STD"] and not ("JMB" in aviones and "STD" in aviones):
            return False
    return True



def make_constraint_function(airplane_types):
    """
    Devuelve una función que aplica las restricciones de taller.
    """
    def constraint(*positions):
        return validate_airplanes_per_taller(positions, airplane_types)
    return constraint




def ensure_t2_in_spc(problem, data):
    """
    Restricción: Todas las tareas T2 deben asignarse a talleres SPC.
    """
    spc_positions = data['spc_workshops']
    airplanes = data['airplanes']

    for airplane in airplanes:
        tasks_t2 = airplane['tasks_t2']

        # Aplicar restricción solo si hay tareas T2
        if tasks_t2 > 0:
            for t in range(tasks_t2):
                if t < data['time_slots']:
                    variable_name = f"airplane_{airplane['id']}_t{t}"

                    # Verificar si la variable existe en el modelo
                    if variable_name in problem._variables:
                        problem.addConstraint(
                            partial(lambda pos, spc: pos in spc, spc=spc_positions),
                            [variable_name]
                        )
                    else:
                        print(f"Advertencia: La variable {variable_name} no está en el modelo.")


def ensure_adjacent_vacancy(*positions):
    """
    Verifica que si un taller tiene ocupación, al menos una posición adyacente esté vacía.
    No marca posiciones con 2 aviones válidos como ocupadas completamente.
    """
    from collections import Counter, defaultdict

    talleres = defaultdict(list)
    for pos in positions:
        if pos is not None:
            talleres[pos].append(pos)

    for pos, ocupantes in talleres.items():
        # Si el taller tiene más de 2 ocupantes, lo consideramos totalmente ocupado (restricción ya gestionada).
        if len(ocupantes) > 2:
            continue

        # Analizamos la vecindad de esta posición
        x, y = pos
        adjacent_positions = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

        # Verificar si al menos una posición adyacente no está ocupada
        if all(adj in talleres for adj in adjacent_positions):
            return False  # Todas las posiciones adyacentes están ocupadas
    return True



def only_one_jumbo(*positions):
    """Restricción: Solo 1 avión JUMBO por taller."""
    from collections import Counter
    return all(count <= 1 for count in positions if count == "JMB")


def restrict_parking_usage(problem, data):
    """
    Restricción: Un avión puede estar en PRK solo si no tiene tareas asignadas en esa franja horaria.
    """
    parkings = data['parkings']
    std_workshops = data['std_workshops']
    spc_workshops = data['spc_workshops']

    for airplane in data['airplanes']:
        tasks_t2 = airplane['tasks_t2']
        tasks_t1 = airplane['tasks_t1']

        for t in range(data['time_slots']):
            variable = f"airplane_{airplane['id']}_t{t}"

            # Restricción: si el tiempo t es menor a tareas T2 + T1, debe estar en un taller
            if t < tasks_t2:
                problem.addConstraint(
                    lambda pos, spc=spc_workshops: pos in spc,
                    [variable]
                )
            elif t < tasks_t2 + tasks_t1:
                problem.addConstraint(
                    lambda pos, std=std_workshops: pos in std,
                    [variable]
                )
            else:
                # Restricción: si no tiene tareas pendientes, puede estar en PRK
                problem.addConstraint(
                    lambda pos, prk=parkings: pos in prk,
                    [variable]
                )


def no_adjacent_positions(p1, p2):
    """Restricción: Posiciones no adyacentes para maniobrabilidad."""
    x1, y1 = p1
    x2, y2 = p2
    return abs(x1 - x2) > 1 or abs(y1 - y2) > 1


def add_constraints(problem, data):
    airplanes = data['airplanes']
    time_slots = data['time_slots']

    # Restricción 1: Máximo 2 aviones y solo 1 JUMBO por taller
    for t in range(time_slots):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        airplane_types = [airplane['type'] for airplane in airplanes]
        problem.addConstraint(make_constraint_function(airplane_types), vars_at_time)

    # Restricción 2: Asegurar tareas T2 en talleres especializados
    ensure_t2_in_spc(problem, data)

    # Restricción 5: Al menos una posición adyacente debe estar vacía
    for t in range(time_slots):
        vars_at_time = [f"airplane_{airplane['id']}_t{t}" for airplane in airplanes]
        problem.addConstraint(ensure_adjacent_vacancy, vars_at_time)

    # Restricción 4: Asegurar el orden de tareas T2 antes de T1
    for airplane in airplanes:
        tasks_t2 = airplane['tasks_t2']
        tasks_t1 = airplane['tasks_t1']
        for t in range(tasks_t2):
            if t < time_slots:
                variable_name = f"airplane_{airplane['id']}_t{t}"
                problem.addConstraint(
                    lambda pos: pos in data['spc_workshops'],
                    [variable_name]
                )
        for t in range(tasks_t2, tasks_t2 + tasks_t1):
            if t < time_slots:
                variable_name = f"airplane_{airplane['id']}_t{t}"
                problem.addConstraint(
                    lambda pos: pos in data['std_workshops'],
                    [variable_name]
                )

    restrict_parking_usage(problem, data)



def write_output_file(output_file, solutions, data):
    """Writes the solutions in the desired format."""
    with open(output_file, 'w') as file:
        file.write(f"N. Sol: {len(solutions)}\n")
        for i, solution in enumerate(solutions[:5], start=1):
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
