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


num_weeks = 16
week_days = 7
num_shifts = 4
sunday_shifts = 4
shifts_per_week = 8
num_nurses = 19
nurseList = range(num_nurses)
nurseList_ = range(1, num_nurses)
weekdaysList = range(week_days)
infrasettimanali = [0, 1, 2, 3, 4, 5]
dayList = range(num_weeks*7)
shiftList = range(num_shifts)
weekList = range(num_weeks)


tot_shifts_to_assign = shifts_per_week * num_weeks
min_shifts_per_nurse = tot_shifts_to_assign // num_nurses
if tot_shifts_to_assign % num_nurses == 0:
    max_shifts_per_nurse = min_shifts_per_nurse
else:
    max_shifts_per_nurse = min_shifts_per_nurse + 1

num_turni_di_prima = max_shifts_per_nurse // 2
num_turni_di_seconda = max_shifts_per_nurse - num_turni_di_prima

weekend_shifts_to_assing = 4 * num_weeks
min_we_shifts_per_nurse = weekend_shifts_to_assing // num_nurses
if weekend_shifts_to_assing % num_nurses == 0:
    max_we_shifts_per_nurse = min_we_shifts_per_nurse
else:
    max_we_shifts_per_nurse = min_we_shifts_per_nurse + 1

print("Min shifts per nurse {}".format(min_shifts_per_nurse))
print("Max shifts per nurse {}".format(max_shifts_per_nurse))
print("Max shifts per nurse di Prima {}".format(num_turni_di_prima))

print("Min WE shifts per nurse {}".format(min_we_shifts_per_nurse))
print("Max WE shifts per nurse {}".format(max_we_shifts_per_nurse))


try:
    # Sample data
    # Sets of days and workers
    # Number of workers required for each shift
    shiftRequirements = {(d, s): 1 for d in dayList for s in shiftList}

    for w in weekList:
        for d in infrasettimanali:
            day = w*7 + d
            shiftRequirements[day, 0] = 0
            shiftRequirements[day, 1] = 0

    # Create availability dictionary to be used in decision variable bounding
    avail = {(n, d, s): 1 for n in nurseList for d in dayList for s in shiftList}
    # MOLINARO
    for w in weekList:
        for d in dayList:
            day = int(w * 7 + d)
            avail[0, day, 2] = 0
            avail[0, day, 3] = 0

    for n in nurseList:
        for w in weekList:
            for d in infrasettimanali:
                day = int(w * 7 + d)
                avail[n, day, 0] = 0
                avail[n, day, 0] = 0

    # Create initial model
    model = Model("Turni_Infermieri_Dialisi")

    # Initialize assignment decision variables:
    x = model.addVars(nurseList, dayList, shiftList, ub=avail, vtype=GRB.BINARY, name='x')

    # Variables to count the total shifts worked by each worker
    totShifts = model.addVars(nurseList, name='TotshiftList')
    # Constraint: assign exactly shiftRequirements[s] workers
    model.addConstrs((x.sum('*', d, s) == shiftRequirements[d, s] for d in dayList for s in shiftList),
                     name='shiftRequirement')

    # Max daily shifts = 1
    model.addConstrs((x.sum(n, d, '*') <= 1 for n in nurseList for d in dayList), name='dailyshifts')

    # Constraint: compute the total number of shifts for each worker
    model.addConstrs((totShifts[n] == x.sum(n, '*') for n in nurseList), name='totShifts')

    # balance weeks
    for w in weekList:
        tmpweekList = range(w*7, w*7+6)
        name_var = 'weekVar_w{}'.format(w)
        # week = model.addVars(nurseList, tmpweekList, shiftList, ub=avail, vtype=GRB.BINARY, name=name_var)
        name_constr = 'weekConstr_w{}'.format(w)
        model.addConstrs(((x.sum(n, tmpweekList, '*') <= 2 for n in nurseList)), name=name_constr)

    turni_di_prima = model.addVars(nurseList, dayList, [0, 2], ub=avail, vtype=GRB.BINARY, name='T_di_Prima')
    turni_di_seconda = model.addVars(nurseList, dayList, [1, 3], ub=avail, vtype=GRB.BINARY, name='T_di_Seconda')
    # Variable to represent these shifts
    totTurnidiPrima = model.addVar(name='totTdiPrima')
    totTurnidiSeconda = model.addVar(name='totTdiSeconda')
    model.addConstrs((totTurnidiPrima == turni_di_prima.sum() for w in nurseList), name='CtotTdPrima')
    model.addConstrs((totTurnidiSeconda == turni_di_seconda.sum() for w in nurseList), name='CtotTdSeconda')

    # Turni del weekend
    # balance weekends
    tmpSundayList = []
    for w in weekList:
        # tmpSundayList.append(w * 7 + 5)
        tmpSundayList.append(w * 7 + 6)
    model.addConstrs((x.sum(n, tmpSundayList, '*') >= min_we_shifts_per_nurse for n in nurseList_
                      for d in tmpSundayList), name='MinTxWeekend')
    model.addConstrs((x.sum(n, tmpSundayList, '*') <= max_we_shifts_per_nurse for n in nurseList
                      for d in tmpSundayList), name='MaxTxWeekend')

    ############################################################
    # Constraint: set minShift/maxShift variable to less/greater than the
    # number of shifts among all workers
    minShift = model.addVar(name='minShift')
    maxShift = model.addVar(name='maxShift')
    numShiftPrima = model.addVar(name='maxShiftP')
    numShiftSeconda = model.addVar(name='maxShiftS')
    # TODO add constrPrima vs Seconda
    # TODO add constr Consecutive shifts

    # Add constraint to the model solver
    model.addGenConstrMin(minShift, totShifts, min_shifts_per_nurse, name='minShift')
    model.addGenConstrMax(maxShift, totShifts, max_shifts_per_nurse, name='maxShift')
    #model.addGenConstrMin(numShiftPrima, turni_di_prima, num_turni_di_prima-1, name='minShiftPr')
    #model.addGenConstrMax(numShiftPrima, turni_di_prima, num_turni_di_prima, name='maxShiftPr')
    #model.addGenConstrMin(numShiftSeconda, turni_di_seconda, num_turni_di_seconda-1, name='minShiftSec')
    #model.addGenConstrMax(numShiftSeconda, turni_di_seconda, num_turni_di_seconda, name='maxShiftSec')
    # model.addGenConstrMin(minShiftWeekend, totShifts, name='minShiftSabDom')
    # model.addGenConstrMax(maxShiftWeekend, totShifts, name='maxShiftSabDom')
    ############################################################
    # Set global sense for ALL objectives
    model.ModelSense = GRB.MINIMIZE

    # Set up secondary objective
    model.setObjectiveN(maxShift - minShift, index=0, priority=2, abstol=2.0, reltol=0.1, name='Fairness')
    # model.setObjectiveN(numShiftPrima - numShiftSeconda, index=1, name='FairnessPrimaSeconda')
    # model.setObjectiveN(maxShiftWeekend - minShiftWeekend, index=2, priority=10, name='FairnessWeekend')

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
