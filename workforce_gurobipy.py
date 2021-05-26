#!/usr/bin/python

# Copyright 2018, Gurobi Optimization, LLC

# Assign workers to shifts; each worker may or may not be available on a
# particular day. We use multi-objective optimization to solve the model.
# The highest-priority objective minimizes the sum of the slacks
# (i.e., the total number of uncovered shifts). The secondary objective
# minimizes the difference between the maximum and minimum number of
# shifts worked among all workers.  The second optimization is allowed
# to degrade the first objective by up to the smaller value of 10% and 2 */

from gurobipy import *
import pandas as pd


num_weeks = 7
week_days = 7
num_shifts = 4
sunday_shifts = 4
shifts_per_week = 16
num_nurses = 19
nurseList = range(num_nurses)
weekdaysList = range(week_days)
dayList = range(num_weeks*7)
shiftList = range(num_shifts)
weekList = range(num_weeks)

tot_shifts_to_assign = shifts_per_week * num_weeks
min_shifts_per_nurse = tot_shifts_to_assign // num_nurses
if tot_shifts_to_assign % num_nurses == 0:
    max_shifts_per_nurse = min_shifts_per_nurse
else:
    max_shifts_per_nurse = min_shifts_per_nurse + 1

print("Min shifts per nurse {}".format(min_shifts_per_nurse))
print("Max shifts per nurse {}".format(max_shifts_per_nurse))

maxShifts = max_shifts_per_nurse
minShifts = min_shifts_per_nurse - 1

try:
    # Sample data
    # Sets of days and workers
    # Number of workers required for each shift
    shiftRequirements = {(d, s): 1 for d in dayList for s in shiftList}

    for w in weekList:
        for d in weekdaysList:
            if d < (week_days - 1):
                day = w*7 + d
                for s in [0, 1]:
                    shiftRequirements[day, s] = 0

    # Create availability dictionary to be used in decision variable bounding
    avail = {(n, d, s): 1 for n in nurseList for d in dayList for s in shiftList}
    # MOLINARO
    for w in weekList:
        for d in dayList:
            day = int(w * 7 + d)
            avail[0, day, 2] = 0
            avail[0, day, 3] = 0

    # Create initial model
    model = Model("Turni_Infermieri_Dialisi")

    # Initialize assignment decision variables:
    x = model.addVars(nurseList, dayList, shiftList, ub=avail, vtype=GRB.BINARY, name='x')

    # Constraint: assign exactly shiftRequirements[s] workers
    model.addConstrs((x.sum('*', d, s) == shiftRequirements[d, s] for d in dayList for s in shiftList), name='shiftRequirement')

    # Max daily shifts = 1
    model.addConstrs((x.sum(n, d, '*') <= 1 for n in nurseList for d in dayList), name='dailyshifts')
    ############################################################
    # Set global sense for ALL objectives
    model.ModelSense = GRB.MINIMIZE

    # Set up primary objective
    minShiftsConstr = model.addConstrs(((x.sum(n, '*') >= minShifts for n in nurseList)), name='minShifts')
    maxShiftsConstr = model.addConstrs(((x.sum(n, '*') <= maxShifts for n in nurseList)), name='maxShifts')

    # # balance weeks
    # for w in weekList:
    #     tmpweekList = range(w*7, w*7+6)
    #     name_var = 'weekVar_w{}'.format(w)
    #     week = model.addVars(nurseList, tmpweekList, shiftList, ub=avail, vtype=GRB.BINARY, name=name_var)
    #     name_constr = 'weekConstr_w{}'.format(w)
    #     model.addConstrs(((week.sum(n, '*') <= 2 for n in nurseList)), name=name_constr)

    # TODO add sunday constraint
    # TODO add saturday constraint
    # TODO add turni di prima/turni di seconda constraint
    #model.addConstrs((x.sum(n, d, 0) + x.sum(n, d, 2) <= maxShifts // 2 for n in nurseList for d in dayList), name='maxShiftPrima')
    #model.addConstrs((x.sum(n, d, 0) + x.sum(n, d, 2) >= minShifts // 2 for n in nurseList for d in dayList), name='minShiftPrima')
    #model.addConstrs((x.sum(n, d, 1) + x.sum(n, d, 3) <= maxShifts // 2 for n in nurseList for d in dayList), name='maxShiftSeconda')
    #model.addConstrs((x.sum(n, d, 1) + x.sum(n, d, 3) <= minShifts // 2 for n in nurseList for d in dayList), name='minShiftSeconda')

    # Save problem
    model.write('workforce_VES.lp')

    # Optimize
    model.optimize()

    status = model.Status
    if status == GRB.Status.INF_OR_UNBD or \
            status == GRB.Status.INFEASIBLE or \
            status == GRB.Status.UNBOUNDED:
        print('The model cannot be solved because it is infeasible or unbounded')
        sys.exit(0)

    if status != GRB.Status.OPTIMAL:
        print('Optimization was stopped with status ' + str(status))
        sys.exit(0)

    sol = pd.DataFrame(data={'Solution': model.X}, index=model.VarName)
    sol = sol.iloc[0:len(x)]
    dashboard = pd.DataFrame(index=dayList, columns=shiftList)
    for row in sol.iterrows():
        index = row[0]
        value = row[1].values[0]
        if value:
            index = index.replace('x[','')
            index = index.replace(']','')
            index = index.split(',')
            dashboard.at[int(index[1]), int(index[2])] = index[0]
    solution_filename = 'Solution_workforce.csv'
    dashboard.to_csv(solution_filename)
    print('Done')


except GurobiError as e:
    print('Error code ' + str(e.errno) + ": " + str(e))

except AttributeError as e:
    print('Encountered an attribute error: ' + str(e))
