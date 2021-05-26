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
import numpy as np

try:
    # Sample data
    # Sets of days and workers
    shiftList = ["Lun_Notte", "Mar_Notte", "Mer_Notte", "Gio_Notte", "Ven_Notte", "Sab_Notte", "Dom_Giorno", "Dom_Notte"]
    workerList = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19"]

    # Number of workers required for each shift
    S = [2, 2, 2, 2, 2, 2, 2, 2]
    shiftRequirements = {s: S[i] for i, s in enumerate(shiftList)}

    availability = pd.DataFrame(np.ones((len(workerList), len(shiftList))), index=workerList, columns=shiftList)
    # Set Molinaro availabiity (only Sunday morning)
    availability.at["1", "Lun_Notte"] = 0
    availability.at["1", "Mar_Notte"] = 0
    availability.at["1", "Mer_Notte"] = 0
    availability.at["1", "Gio_Notte"] = 0
    availability.at["1", "Ven_Notte"] = 0
    availability.at["1", "Sab_Notte"] = 0
    availability.at["1", "Dom_Notte"] = 0

    # Create availability dictionary to be used in decision variable bounding
    avail = {(w, s): availability.loc[w, s] for w in workerList for s in shiftList}

    # Create initial model
    model = Model("Turni_Infermieri_Dialisi")

    # Initialize assignment decision variables:
    # x[w][s] == 1 if worker w is assigned to shift s.
    # This is no longer a pure assignment model, so we must
    # use binary variables.
    x = model.addVars(avail.keys(), ub=avail, vtype=GRB.BINARY, name='x')

    # Slack variables for each shift constraint so that the shifts can
    # be satisfied
    slacks = model.addVars(shiftList, name='Slack')

    # Variable to represent the total slack
    totSlack = model.addVar(name='totSlack')

    # Variables to count the total shifts worked by each worker
    totShifts = model.addVars(workerList, name='TotshiftList')

    # Constraint: assign exactly shiftRequirements[s] workers
    # to each shift s, plus the slack
    model.addConstrs((x.sum('*', s) + slacks[s] == shiftRequirements[s] for s in shiftList), name='shiftRequirement')

    # Constraint: set totSlack equal to the total slack
    model.addConstr(totSlack == slacks.sum(), name='totSlack')

    # Constraint: compute the total number of shifts for each worker
    model.addConstrs((totShifts[w] == x.sum(w, '*') for w in workerList), name='totShifts')

    # Constraint: set minShift/maxShift variable to less/greater than the
    # number of shifts among all workers
    minShift = model.addVar(name='minShift')
    maxShift = model.addVar(name='maxShift')
    model.addGenConstrMin(minShift, totShifts, name='minShift')
    model.addGenConstrMax(maxShift, totShifts, name='maxShift')

    ############################################################
    # Cost of a regular shift
    # regCost = [100, 100, 100, 110, 100, 200, 200, 200]
    # regHours = model.addVars(workerList, name='regHrs')
    # regularCost = {w: regCost[i] for i, w in enumerate(shiftList)}
    # Cost = 0
    # Cost += (quicksum(regularCost[w] * regHours[w] for w in shiftList))

    # model.setObjective(Cost)

    # Set global sense for ALL objectives
    model.ModelSense = GRB.MINIMIZE

    # Set up primary objective
    model.setObjectiveN(totSlack, index=0, priority=2, abstol=2.0, reltol=0.1, name='TotalSlack')

    # Set up secondary objective
    model.setObjectiveN(maxShift - minShift, index=1, priority=1, name='Fairness')

    # Save problem
    model.write('workforce5.lp')

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

    # Print total slack and the number of shifts worked for each worker
    print('')
    print('Total slack required: ' + str(totSlack.X))
    for w in workerList:
        print(w + ' worked ' + str(totShifts[w].X) + ' shifts')
    print('')

    sol = pd.DataFrame(data={'Solution': model.X}, index=model.VarName)
    sol = sol.iloc[0:len(x)]

    dashboard = pd.DataFrame(index=workerList, columns=shiftList)
    for w in workerList:
        for s in shiftList:
            dashboard.at[w, s] = sol.loc['x[' + w + ',' + s + ']',][0]
    shiftAssignments = {}
    for s in shiftList:
        shiftAssignments.update({s: list(dashboard[dashboard[s] == 1].loc[:, ].index)})

    print(shiftAssignments)

except GurobiError as e:
    print('Error code ' + str(e.errno) + ": " + str(e))

except AttributeError as e:
    print('Encountered an attribute error: ' + str(e))
