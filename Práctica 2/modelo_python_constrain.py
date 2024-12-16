from constraint import Problem, AllDifferentConstraint
import csv

# Leer archivo de entrada
def read_input_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

        # Parámetros iniciales
        franjas_horarias = int(lines[0].strip())
        tam_matriz = tuple(map(int, lines[1].strip().split('x')))

        # Talleres y parkings
        talleres_std = [tuple(map(int, pos.split(','))) for pos in lines[2].strip().split()]
        talleres_spc = [tuple(map(int, pos.split(','))) for pos in lines[3].strip().split()]
        parkings = [tuple(map(int, pos.split(','))) for pos in lines[4].strip().split()]

        # Información de aviones
        aviones = []
        for line in lines[5:]:
            if line.strip():
                parts = line.strip().split('-')
                aviones.append({
                    'id': int(parts[0]),
                    'tipo': parts[1],
                    'restr': parts[2] == 'T',
                    't1': int(parts[3]),
                    't2': int(parts[4])
                })

    return franjas_horarias, tam_matriz, talleres_std, talleres_spc, parkings, aviones


# Pre-cálculo de posiciones adyacentes
def precalculate_adyacentes(tam_matriz):
    adyacencias = {}
    for i in range(tam_matriz[0]):
        for j in range(tam_matriz[1]):
            pos = (i, j)
            adyacencias[pos] = [(i + dx, j + dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                if 0 <= i + dx < tam_matriz[0] and 0 <= j + dy < tam_matriz[1]]
    return adyacencias


# Restricciones del problema
def setup_constraints(problem, aviones, talleres_std, talleres_spc, parkings, franjas_horarias, tam_matriz):
    adyacencias = precalculate_adyacentes(tam_matriz)

    # Definición de variables y dominios optimizados
    for avion in aviones:
        for franja in range(franjas_horarias):
            var = f"A{avion['id']}_T{franja}"
            if avion['restr']:
                problem.addVariable(var, talleres_spc)  # Solo talleres especialistas
            else:
                problem.addVariable(var, talleres_std + talleres_spc + parkings)

    # Restricción: Todo avión tiene una posición única por franja horaria
    for franja in range(franjas_horarias):
        problem.addConstraint(AllDifferentConstraint(), [f"A{avion['id']}_T{franja}" for avion in aviones])

    # Restricción de adyacencia para maniobrabilidad
    def check_adyacencia(*args):
        for pos in args:
            if pos in adyacencias:  # Verificar si la posición existe en adyacencias
                if all(args.count(adj) > 0 for adj in adyacencias[pos]):
                    return False
        return True

    for franja in range(franjas_horarias):
        problem.addConstraint(check_adyacencia, [f"A{avion['id']}_T{franja}" for avion in aviones])

    # Restricción: Evitar aviones JUMBO adyacentes
    def check_jumbo_adyacentes(*args):
        for i, pos1 in enumerate(args):
            for j, pos2 in enumerate(args):
                if i != j and pos1 in adyacencias and pos2 in adyacencias[pos1]:
                    return False
        return True

    for franja in range(franjas_horarias):
        problem.addConstraint(check_jumbo_adyacentes,
                              [f"A{avion['id']}_T{franja}" for avion in aviones if avion['tipo'] == 'JMB'])

    # Restricción: Máximo 2 aviones por taller (incluido JMB)
    for franja in range(franjas_horarias):
        for taller in talleres_std + talleres_spc:
            problem.addConstraint(lambda *args: args.count(taller) <= 2,
                                  [f"A{avion['id']}_T{franja}" for avion in aviones])

    # Restricción: Solo un avión JMB por taller por franja horaria
    for franja in range(franjas_horarias):
        for taller in talleres_std + talleres_spc:
            problem.addConstraint(lambda *args: sum(1 for val in args if val == taller) <= 1,
                                  [f"A{avion['id']}_T{franja}" for avion in aviones if avion['tipo'] == 'JMB'])


# Guardar resultados en archivo CSV
def save_results(file_name, solutions):
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([f"N. Sol: {len(solutions)}"])
        for i, solution in enumerate(solutions):
            writer.writerow([f"Solución {i + 1}:"])
            for avion_id in set(key.split('_')[0] for key in solution.keys()):
                posiciones = [f"{solution[var]}" for var in solution if var.startswith(avion_id)]
                writer.writerow([f"{avion_id}: {', '.join(posiciones)}"])


# Programa principal
def main(file_path):
    franjas_horarias, tam_matriz, talleres_std, talleres_spc, parkings, aviones = read_input_file(file_path)
    problem = Problem()
    setup_constraints(problem, aviones, talleres_std, talleres_spc, parkings, franjas_horarias, tam_matriz)
    solutions = problem.getSolutions()
    print(f"Number of solutions: {len(solutions)}")
    save_results(f"{file_path.split('.')[0]}.csv", solutions)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Uso: python modelo_python_constrain.py <path input>")
    else:
        main(sys.argv[1])
