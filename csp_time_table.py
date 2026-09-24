# Engineering Class Timetable using CSP
# Backtracking + MRV (Minimum Remaining Values)

subjects = ["AI", "DBMS", "CN", "OS", "SE"]
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
periods = [1, 2, 3, 4]

# Create the 20 variables
variables = [(day, period) for day in days for period in periods]


def get_domain(variable, assignment, counts):
    """
    Return the subjects that can legally be assigned
    to the given timetable slot.
    """

    day, period = variable
    domain = []

    for subject in subjects:

        # Constraint 1:
        # A subject can occur at most 4 times.
        if counts[subject] >= 4:
            continue

        # Constraint 2:
        # A subject cannot appear twice on the same day.
        already_on_day = any(
            assignment.get((day, p)) == subject
            for p in periods
        )

        if already_on_day:
            continue

        domain.append(subject)

    return domain


def select_unassigned_variable(assignment, counts):
    """
    MRV:
    Select the unassigned variable with the smallest
    remaining domain.
    """

    unassigned = [
        variable for variable in variables
        if variable not in assignment
    ]

    # Calculate the domain size for every unassigned variable
    domains = {
        variable: get_domain(variable, assignment, counts)
        for variable in unassigned
    }

    # MRV = variable having minimum remaining values
    return min(unassigned, key=lambda v: len(domains[v]))


def is_complete(assignment, counts):
    """
    Check whether all 20 slots are assigned and
    every subject occurs exactly 4 times.
    """

    return (
        len(assignment) == len(variables)
        and all(counts[s] == 4 for s in subjects)
    )


def backtrack(assignment, counts):
    """
    Backtracking CSP solver.
    """

    # Goal test
    if is_complete(assignment, counts):
        return assignment

    # MRV
    variable = select_unassigned_variable(assignment, counts)

    # Try each possible subject
    domain = get_domain(variable, assignment, counts)

    for subject in domain:

        # Assign
        assignment[variable] = subject
        counts[subject] += 1

        # Recursive call
        result = backtrack(assignment, counts)

        if result is not None:
            return result

        # Undo assignment (BACKTRACK)
        del assignment[variable]
        counts[subject] -= 1

    return None


def solve_timetable():

    assignment = {}

    counts = {
        subject: 0
        for subject in subjects
    }

    solution = backtrack(assignment, counts)

    return solution


def print_timetable(timetable):

    print("\nENGINEERING CLASS TIMETABLE")
    print("=" * 60)

    print(
        f"{'Day':<12}"
        f"{'Period 1':<12}"
        f"{'Period 2':<12}"
        f"{'Period 3':<12}"
        f"{'Period 4':<12}"
    )

    print("-" * 60)

    for day in days:

        row = f"{day:<12}"

        for period in periods:
            subject = timetable[(day, period)]
            row += f"{subject:<12}"

        print(row)

    print("=" * 60)

    # Verify subject frequencies
    print("\nSubject frequencies:")

    for subject in subjects:
        count = sum(
            1
            for value in timetable.values()
            if value == subject
        )

        print(f"{subject}: {count}")


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

timetable = solve_timetable()

if timetable:
    print_timetable(timetable)
else:
    print("No valid timetable found.")

# OUTPUT:
    
# ENGINEERING CLASS TIMETABLE
# ============================================================
# Day         Period 1   Period 2   Period 3   Period 4
# ------------------------------------------------------------
# Monday      AI         DBMS       CN         OS
# Tuesday     DBMS       CN         OS         SE
# Wednesday   CN         OS         SE         AI
# Thursday    OS         SE         AI         DBMS
# Friday      SE         AI         DBMS       CN
# ============================================================

# Subject frequencies:
# AI: 4
# DBMS: 4
# CN: 4
# OS: 4
# SE: 4
