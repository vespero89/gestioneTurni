from ortools.sat.python import cp_model
import numpy as np
import itertools
import pandas as pd


class NursesPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, shifts, num_nurses, num_tot_days, num_shifts, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._num_nurses = num_nurses
        self._num_days = num_tot_days
        self._num_shifts = num_shifts
        self._solutions = set(sols)
        self._solution_count = 0
        self._solution_limit = 10
        self.solution_array = np.ones((num_tot_days, num_shifts), dtype=np.int8)*-1

    def on_solution_callback(self):
        if self._solution_count in self._solutions:
            print('Solution %i' % self._solution_count)
            for d in range(self._num_days):
                # print('Day ' + str(d))
                for n in range(self._num_nurses):
                    is_working = False
                    for s in range(self._num_shifts):
                        value = self.Value(self._shifts[(n, d, s)])
                        if value == 1:
                            is_working = True
                            # print('  Nurse {} works shift {}'.format(n, s))
                            self.solution_array[d, s] = int(n)
                    # if not is_working:
                    #     print('  Nurse {} does not work'.format(n))
            print()
            solution_filename = 'Solution_' + str(self._solution_count) + '.csv'
            pd.DataFrame(self.solution_array).to_csv(solution_filename)
        self._solution_count += 1
        if self._solution_count >= self._solution_limit:
            print('Stop search after %i solutions' % self._solution_limit)
            self.StopSearch()

    def solution_count(self):
        return self._solution_count


def main():
    # Data.
    num_weeks = 7
    week_days = 7
    num_shifts = 4
    sunday_shifts = 4
    shifts_per_week = 16
    num_nurses = 22
    nurseList = list(range(num_nurses))
    nurseList_ = range(1, num_nurses)
    weekdaysList = range(week_days)
    infrasettimanali = [0, 1, 2, 3, 4, 5]
    dayList = range(num_weeks * 7)
    shiftList = range(num_shifts)
    weekList = range(num_weeks)

    tot_shifts_to_assign_per_nurse = shifts_per_week * num_weeks
    min_shifts_per_nurse = tot_shifts_to_assign_per_nurse // num_nurses
    if tot_shifts_to_assign_per_nurse % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1

    num_turni_di_prima = (max_shifts_per_nurse // 2)
    num_turni_di_seconda = max_shifts_per_nurse - num_turni_di_prima

    weekend_shifts_to_assing = sunday_shifts * num_weeks
    min_we_shifts_per_nurse = weekend_shifts_to_assing // num_nurses
    if weekend_shifts_to_assing % num_nurses == 0:
        max_we_shifts_per_nurse = min_we_shifts_per_nurse
    else:
        max_we_shifts_per_nurse = min_we_shifts_per_nurse + 1

    print("Generated weeks {}".format(num_weeks))
    print("Min shifts per nurse {}".format(min_shifts_per_nurse))
    print("Max shifts per nurse {}".format(max_shifts_per_nurse))
    print("Max shifts per nurse di Prima {}".format(num_turni_di_prima))
    print("Max shifts per nurse di Seconda {}".format(num_turni_di_seconda))

    print("Min WE shifts per nurse {}".format(min_we_shifts_per_nurse))
    print("Max WE shifts per nurse {}".format(max_we_shifts_per_nurse))

    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, d, s)]: nurse 'n' works shift 's' on day 'd'.
    shifts = {}
    for n in nurseList:
        for d in dayList:
            for s in shiftList:
                shifts[(n, d, s)] = model.NewBoolVar('shift_op%id%is%i' % (n, d, s))

    # setup shift planner
    for w in weekList:
        for d in infrasettimanali:
            day = w*7 + d
            model.Add(sum(shifts[(n, day, 0)] for n in nurseList) == 0)
            model.Add(sum(shifts[(n, day, 1)] for n in nurseList) == 0)
    # MOLINARO
    for w in weekList:
        for d in weekdaysList:
            day = int(w * 7 + d)
            model.Add(shifts[(0, day, 2)] == 0)
            model.Add(shifts[(0, day, 3)] == 0)

    # Each shift is assigned to exactly one nurse in the schedule period.
    i = 0
    for d in dayList:
        i += 1
        if i == 7:
            for s in shiftList:
                model.Add(sum(shifts[(n, d, s)] for n in nurseList) == 1)
            i = 0

    for w in weekList:
        for d in infrasettimanali:
            day = w * 7 + d
            for s in [2, 3]:
                model.Add(sum(shifts[(n, day, s)] for n in nurseList) == 1)

    # Each nurse works at most one shift per day.
    for n in nurseList:
        for d in dayList:
            model.Add(sum(shifts[(n, d, s)] for s in shiftList) <= 1)

    for n in nurseList_:
        num_shifts_worked = 0
        num_shifts_prima = 0
        num_shifts_seconda = 0
        num_shifts_domenica = 0
        j = 0
        for d in dayList:
            j += 1
            for s in shiftList:
                num_shifts_worked += shifts[(n, d, s)]
            for s1 in [0, 2]:
                num_shifts_prima += shifts[(n, d, s1)]
            for s2 in [1, 3]:
                num_shifts_seconda += shifts[(n, d, s2)]
            if j == 7:
                for sd in shiftList:
                    num_shifts_domenica += shifts[(n, d, sd)]
                j = 0
        model.Add(min_shifts_per_nurse <= num_shifts_worked)
        model.Add(num_shifts_worked <= max_shifts_per_nurse)
        model.Add(min_we_shifts_per_nurse <= num_shifts_domenica)
        model.Add(num_shifts_domenica <= max_we_shifts_per_nurse)
        model.Add(num_shifts_prima <= num_turni_di_prima)
        model.Add(num_shifts_seconda <= num_turni_di_seconda)
    ######MOLINARO###############################################
    weekend_shifts_to_assing_M = 2 * num_weeks
    min_we_shifts_per_nurse_M = weekend_shifts_to_assing_M // num_nurses
    if weekend_shifts_to_assing_M % num_nurses == 0:
        max_we_shifts_per_nurse_M = min_we_shifts_per_nurse_M
    else:
        max_we_shifts_per_nurse_M = min_we_shifts_per_nurse_M + 1
    num_shifts_prima_M = 0
    num_shifts_seconda_M = 0
    num_shifts_domenica_M = 0
    j = 0
    for d in dayList:
        j += 1
        if j == 7:
            for sd in shiftList:
                num_shifts_domenica_M += shifts[(0, d, sd)]
            num_shifts_prima_M += shifts[(0, d, 0)]
            num_shifts_seconda_M += shifts[(0, d, 1)]
            j = 0
    model.Add(min_we_shifts_per_nurse_M <= num_shifts_domenica_M)
    model.Add(num_shifts_domenica_M <= max_we_shifts_per_nurse_M)
    #############################################################
    # Penalized transitions
    # disposizioni
    dispositions = []
    for di in itertools.product(shiftList, repeat=2):
        dispositions.append(di)
    for n in nurseList_:
        for d in range((num_weeks * 7) - 3):
            for disp in dispositions:
                transition1 = [shifts[n, d, disp[0]].Not(), shifts[n, d+1, disp[1]].Not()]
                transition2 = [shifts[n, d, disp[0]].Not(), shifts[n, d+2, disp[1]].Not()]
                transition3 = [shifts[n, d, disp[0]].Not(), shifts[n, d+3, disp[1]].Not()]
                model.AddBoolOr(transition1)
                model.AddBoolOr(transition2)
                model.AddBoolOr(transition3)
    # TODO add penalized weekend transitions
    # TODO add condition for nurseList_:  num_shift_worked_per_shift <= ((max_shifts_per_nurse // num_weeks) + 1)
    ################## BALANCE WEEKS ############################################################################
    max_shifts_per_nurse_per_week = (max_shifts_per_nurse // num_weeks) + 1
    for n in nurseList_:
        num_shifts_worked_in_week = 0
        j = 0
        for d in dayList:
            j += 1
            if j < 8:
                for s in shiftList:
                    num_shifts_worked_in_week += shifts[(n, d, s)]
            else:
                model.Add(num_shifts_worked_in_week <= max_shifts_per_nurse_per_week)
                j = 0
                num_shifts_worked_in_week = 0
                for s in shiftList:
                    num_shifts_worked_in_week += shifts[(n, d, s)]

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    # Display the first five solutions.
    a_few_solutions = range(5)
    solution_printer = NursesPartialSolutionPrinter(shifts, num_nurses, len(dayList), num_shifts, a_few_solutions)
    # status = solver.SearchForAllSolutions(model, solution_printer)
    status = solver.SolveWithSolutionCallback(model, solution_printer)
    # Statistics.
    print()
    print('Statistics')
    print('  - conflicts       : %i' % solver.NumConflicts())
    print('  - branches        : %i' % solver.NumBranches())
    print('  - wall time       : %f s' % solver.WallTime())
    print('  - solutions found : %i' % solution_printer.solution_count())


if __name__ == '__main__':
    main()
