from ortools.sat.python import cp_model
import numpy as np
import pandas as pd


class NursesPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, shifts, num_nurses, num_days, num_shifts, num_sunday_shifts, num_weeks, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._sunday_shifts = num_sunday_shifts
        self._num_nurses = num_nurses
        self._num_days = num_days
        self._num_shifts = num_shifts
        self._num_weeks = num_weeks
        self._solutions = set(sols)
        self._solution_count = 0
        self._solution_limit = 1000
        self.solution_array = np.zeros((num_days*num_weeks, num_sunday_shifts), dtype=np.int8)

    def on_solution_callback(self):
        if self._solution_count in self._solutions:
            print('Solution %i' % self._solution_count)
            for w in range(self._num_weeks):
                for d in range(1, self._num_days+1):
                    print('Day ' + str(d+(w*self._num_days)))
                    if d % self._num_days != 0:
                        for n in range(self._num_nurses):
                            is_working = False
                            for s in range(self._num_shifts):
                                if self.Value(self._shifts[(n, d+(w*self._num_days), s)]):
                                    is_working = True
                                    print('  Nurse {} works shift {}'.format(n, s))
                                    self.solution_array[d+(w*self._num_days)-1, s + 2] = int(n + 1)
                            # if not is_working:
                            #     print('  Nurse {} does not work'.format(n))
                    else:
                        for n in range(self._num_nurses):
                            is_working = False
                            for s in range(self._num_shifts + 2):
                                if self.Value(self._shifts[(n, d+(w*self._num_days), s)]):
                                    is_working = True
                                    print('  Nurse {} works shift {}'.format(n, s))
                                    self.solution_array[d+(w*self._num_days)-1, s] = int(n + 1)
                            # if not is_working:
                            #     print('  Nurse {} does not work'.format(n))
            print()
            # solution_filename = 'Solution_' + str(self._solution_count) + '.csv'
            # pd.DataFrame(self.solution_array).to_csv(solution_filename)
        self._solution_count += 1
        if self._solution_count >= self._solution_limit:
            print('Stop search after %i solutions' % self._solution_limit)
            self.StopSearch()

    def solution_count(self):
        return self._solution_count


def main():
    # Data.
    num_nurses = 22
    num_week_shifts = 2
    num_sunday_shifts = 4
    all_week_days = 7
    num_weeks = 1
    all_nurses = range(num_nurses)
    week_shifts = range(num_week_shifts)
    sunday_shifts = range(num_sunday_shifts)
    week_days = range(1, all_week_days)
    all_days = range(1, all_week_days + 1)
    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, d, s)]: nurse 'n' works shift 's' on day 'd'.
    shifts = {}
    for w in range(num_weeks):
        for n in all_nurses:
            for d in week_days:
                for s in week_shifts:
                    shifts[(n, d+(w*all_week_days), s)] = \
                        model.NewBoolVar('shift_op%id%is%i' % (n, d+(w*all_week_days), s))
            # add sundays
            sunday = all_week_days
            for s in sunday_shifts:
                shifts[(n, sunday+(w*all_week_days), s)] = \
                    model.NewBoolVar('shift_op%id%is%i' % (n, sunday+(w*all_week_days), s))

    # Each shift is assigned to exactly one nurse in the schedule period.
    for w in range(num_weeks):
        for d in all_days:
            if (((w*all_week_days) + d) % 7) != 0:
                for s in week_shifts:
                    model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for n in all_nurses) == 1)
            else:
                for s in sunday_shifts:
                    model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for n in all_nurses) == 1)

    # Each nurse works at most one shift per day.
    for n in all_nurses:
        if n != (num_nurses - 1):
            for w in range(num_weeks):
                for d in all_days:
                    if (((w*all_week_days) + d) % 7) != 0:
                        model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for s in week_shifts) <= 1)
                    else:
                        model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for s in sunday_shifts) <= 1)
        else:
            # and add constraint for Molinaro
            sunday_afternoon = [2, 3]
            for w in range(num_weeks):
                for d in all_days:
                    if (((w*all_week_days) + d) % 7) != 0:
                        model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for s in week_shifts) == 0)
                    else:
                        model.Add(sum(shifts[(n, (w*all_week_days) + d, s)] for s in sunday_afternoon) == 0)

    # Try to distribute the shifts evenly, so that each nurse works
    # min_shifts_per_nurse shifts. If this is not possible, because the total
    # number of shifts is not divisible by the number of nurses, some nurses will
    # be assigned one more shift.
    min_shifts_per_nurse = (num_weeks * ((num_week_shifts * 6) + 4)) // num_nurses
    if (num_weeks * ((num_week_shifts * 6) + 4)) % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1

    # TODO FROM HERE - add saturday constraint
    for n in all_nurses:
        num_shifts_worked = 0
        for w in range(num_weeks):
            for d in all_days:
                if (((w*all_week_days) + d) % 7) != 0:
                    for s in week_shifts:
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
    a_few_solutions = range(20)
    solution_printer = NursesPartialSolutionPrinter(shifts, num_nurses,
                                                    all_week_days, num_week_shifts, num_sunday_shifts,
                                                    num_weeks, a_few_solutions)
    status = solver.SearchForAllSolutions(model, solution_printer)
    # status = solver.SolveWithSolutionCallback(model, solution_printer) # todo improve printer

    # Statistics.
    print()
    print('Statistics')
    print('  - conflicts       : %i' % solver.NumConflicts())
    print('  - branches        : %i' % solver.NumBranches())
    print('  - wall time       : %f s' % solver.WallTime())
    print('  - solutions found : %i' % solution_printer.solution_count())


if __name__ == '__main__':
    main()
