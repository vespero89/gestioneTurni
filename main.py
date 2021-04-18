from ortools.sat.python import cp_model


class NursesPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, shifts, num_nurses, num_days, num_shifts, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts  # TODO HERE
        self._num_nurses = num_nurses
        self._num_days = num_days
        self._num_shifts = num_shifts
        self._solutions = set(sols)
        self._solution_count = 0

    def on_solution_callback(self):
        if self._solution_count in self._solutions:
            print('Solution %i' % self._solution_count)
            for d in range(self._num_days):
                print('Day %i' % d)
                for n in range(self._num_nurses):
                    is_working = False
                    for s in range(self._num_shifts):
                        if self.Value(self._shifts[(n, d, s)]):
                            is_working = True
                            print('  Nurse %i works shift %i' % (n, s))
                    if not is_working:
                        print('  Nurse {} does not work'.format(n))
            print()
        self._solution_count += 1

    def solution_count(self):
        return self._solution_count


def main():
    # Data.
    num_nurses = 19
    num_shifts = 2
    num_days = 6
    all_nurses = range(num_nurses)
    all_shifts = range(num_shifts)
    week_days = range(num_days)
    all_days = range(7)
    sunday_shifts = range(4)
    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, d, s)]: nurse 'n' works shift 's' on day 'd'.
    shifts = {}
    for n in all_nurses:
        for d in week_days:
            for s in all_shifts:
                shifts[(n, d, s)] = model.NewBoolVar('shift_op%id%is%i' % (n, d, s))
        # add sundays
        sunday = 7 - 1
        for s in sunday_shifts:
            shifts[(n, sunday, s)] = model.NewBoolVar('shift_op%id%is%i' % (n, sunday, s))

    # Each shift is assigned to exactly one nurse in the schedule period.
    for d in all_days:
        if d != 6:
            for s in all_shifts:
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) == 1)
        else:
            for s in sunday_shifts:
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) == 1)

    # # Each nurse works at most one shift per day.
    # for n in all_nurses:
    #     for d in all_days:
    #         if d != 6:
    #             for s in all_shifts:
    #                 model.Add(sum(shifts[(n, d, s)] <= 1))
    #         else:
    #             for s in sunday_shifts:
    #                 model.Add(sum(shifts[(n, d, s)] <= 1))

    # Each nurse works at most one shift per day.
    for n in all_nurses:
        for d in all_days:
            if d != 6:
                model.Add(sum(shifts[(n, d, s)] for s in all_shifts) <= 1)
            else:
                model.Add(sum(shifts[(n, d, s)] for s in sunday_shifts) <= 1)

    # TODO add constraint for Molinaro
    # Try to distribute the shifts evenly, so that each nurse works
    # min_shifts_per_nurse shifts. If this is not possible, because the total
    # number of shifts is not divisible by the number of nurses, some nurses will
    # be assigned one more shift.
    min_shifts_per_nurse = ((num_shifts * num_days) + 4) // num_nurses
    if ((num_shifts * num_days) + 4) % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1

    # TODO FROM HERE
    for n in all_nurses:
        num_shifts_worked = 0
        for d in all_days:
            if d != 6:
                for s in all_shifts:
                    num_shifts_worked += shifts[(n, d, s)]
            else:
                for s in sunday_shifts:
                    num_shifts_worked += shifts[(n, d, s)]
        model.Add(min_shifts_per_nurse <= num_shifts_worked)
        model.Add(num_shifts_worked <= max_shifts_per_nurse)

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    # Display the first five solutions.
    a_few_solutions = range(5)
    solution_printer = NursesPartialSolutionPrinter(shifts, num_nurses,
                                                    num_days + 1, num_shifts,
                                                    a_few_solutions)
    solver.SearchForAllSolutions(model, solution_printer)

    # Statistics.
    print()
    print('Statistics')
    print('  - conflicts       : %i' % solver.NumConflicts())
    print('  - branches        : %i' % solver.NumBranches())
    print('  - wall time       : %f s' % solver.WallTime())
    print('  - solutions found : %i' % solution_printer.solution_count())


if __name__ == '__main__':
    main()
