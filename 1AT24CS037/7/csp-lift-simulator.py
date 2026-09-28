# ============================================================
# CSP-BASED 3-LIFT / 5-FLOOR SIMULATOR
# ============================================================
#
# AI TECHNIQUES USED:
#   1. Constraint Satisfaction Problem (CSP)
#   2. Backtracking Search
#   3. MRV (Minimum Remaining Values)
#   4. Branch-and-Bound Optimization
#
# SYSTEM:
#   - 3 lifts
#   - 5 floors
#   - One common lift-call button on each floor
#
# CSP:
#   Variables -> People / lift requests
#   Domain    -> Lift 1, Lift 2, Lift 3
#   Constraint -> Every request gets exactly one lift
#
# OBJECTIVE:
#   Minimize total passenger pickup waiting distance.
#
# TIE BREAKERS:
#   1. Minimum total passenger waiting distance
#   2. Minimum maximum lift route (makespan)
#   3. Minimum total lift travel distance
#
# NOTE:
#   Requests are served in arrival order on each lift.
# ============================================================

import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass
from math import inf
import random


# ============================================================
# CONFIGURATION
# ============================================================

NUM_FLOORS = 5
NUM_LIFTS = 3

FLOORS = list(range(1, NUM_FLOORS + 1))

LIFT_NAMES = [
    "Lift 1",
    "Lift 2",
    "Lift 3"
]

# Initial positions
INITIAL_POSITIONS = {
    "Lift 1": 1,
    "Lift 2": 3,
    "Lift 3": 5
}

# Animation speed
MOVE_TIME = 700

# Small delay so several people can press buttons and become
# one CSP batch.
BATCH_DELAY = 500


# ============================================================
# REQUEST
# ============================================================

@dataclass
class Request:

    request_id: int
    floor: int

    # None until CSP assigns a lift
    assigned_lift: str | None = None

    # WAITING / ASSIGNED / COMPLETED
    status: str = "WAITING"


# ============================================================
# LIFT
# ============================================================

class Lift:

    def __init__(self, name, start_floor):

        self.name = name

        # Current physical floor
        self.current_floor = start_floor

        # Current destination
        self.target_floor = None

        # Future stops
        self.queue = []

        # Movement state
        self.moving = False

        # Number of passengers served
        self.served = 0

        # Tkinter animation callback
        self.after_id = None

    # --------------------------------------------------------
    # CURRENT ROUTE
    # --------------------------------------------------------

    def planned_route(self):

        route = []

        if self.target_floor is not None:
            route.append(self.target_floor)

        route.extend(self.queue)

        return route

    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------

    def is_idle(self):

        return (
            not self.moving
            and self.target_floor is None
            and len(self.queue) == 0
        )


# ============================================================
# CSP OPTIMIZATION ENGINE
# ============================================================

class LiftCSP:

    def __init__(self, lift_positions, lift_routes, requests):

        # ----------------------------------------------------
        # LIFTS
        # ----------------------------------------------------

        self.lift_names = list(lift_positions.keys())

        self.lift_positions = dict(lift_positions)

        self.lift_routes = {
            lift: list(route)
            for lift, route in lift_routes.items()
        }

        # ----------------------------------------------------
        # REQUESTS
        # ----------------------------------------------------

        self.requests = sorted(
            requests,
            key=lambda r: r.request_id
        )

        # ----------------------------------------------------
        # CSP VARIABLES
        # ----------------------------------------------------
        # R1, R2, R3...
        #
        # Each variable = a person's lift request
        # ----------------------------------------------------

        self.variables = [
            request.request_id
            for request in self.requests
        ]

        # ----------------------------------------------------
        # CSP DOMAINS
        # ----------------------------------------------------
        # Every request can initially use any lift.
        # ----------------------------------------------------

        self.domains = {
            request.request_id:
                self.lift_names.copy()
            for request in self.requests
        }

        # Current partial assignment
        self.assignment = {}

        # Best solution found
        self.best_assignment = None

        self.best_objective = (
            inf,  # total passenger waiting
            inf,  # makespan
            inf   # total travel
        )

        # Search statistics
        self.nodes = 0
        self.backtracks = 0

    # ========================================================
    # REMOVE CONSECUTIVE DUPLICATE STOPS
    # ========================================================

    @staticmethod
    def compact_route(route):

        result = []

        for floor in route:

            if not result or floor != result[-1]:
                result.append(floor)

        return result

    # ========================================================
    # FIXED TAIL OF A LIFT
    # ========================================================
    #
    # The fixed route consists of requests already assigned
    # before the current CSP batch.
    # ========================================================

    def fixed_tail(self, lift_name):

        route = self.compact_route(
            self.lift_routes.get(lift_name, [])
        )

        if route:
            return route[-1]

        return self.lift_positions[lift_name]

    # ========================================================
    # CALCULATE ROUTE / WAITING METRICS
    # ========================================================

    def calculate_metrics(self, assignment):

        total_waiting = 0
        total_travel = 0
        makespan = 0

        per_lift = {}

        # -----------------------------------------------
        # Process every lift independently
        # -----------------------------------------------

        for lift_name in self.lift_names:

            position = self.lift_positions[lift_name]

            # Existing/fixed route
            fixed_route = self.compact_route(
                self.lift_routes.get(lift_name, [])
            )

            fixed_travel = 0

            for floor in fixed_route:

                distance = abs(position - floor)

                fixed_travel += distance

                position = floor

            # -------------------------------------------
            # New requests assigned to this lift
            # -------------------------------------------

            assigned_requests = [
                request
                for request in self.requests
                if assignment.get(request.request_id)
                == lift_name
            ]

            # Requests are always served in arrival order
            assigned_requests.sort(
                key=lambda request: request.request_id
            )

            cumulative_travel = fixed_travel
            request_waits = {}

            for request in assigned_requests:

                # Avoid duplicate consecutive stop
                if position != request.floor:

                    distance = abs(
                        position - request.floor
                    )

                    cumulative_travel += distance

                    position = request.floor

                # Waiting distance for this passenger
                request_waits[
                    request.request_id
                ] = cumulative_travel

                total_waiting += cumulative_travel

            total_travel += cumulative_travel

            if assigned_requests:

                makespan = max(
                    makespan,
                    cumulative_travel
                )

            per_lift[lift_name] = {
                "requests": assigned_requests,
                "waits": request_waits,
                "total_travel": cumulative_travel
            }

        return (
            total_waiting,
            makespan,
            total_travel,
            per_lift
        )

    # ========================================================
    # MRV
    # ========================================================
    #
    # Choose the unassigned request with the smallest
    # remaining domain.
    #
    # If several requests have the same domain size,
    # choose the one with the largest difference between
    # its best and worst lift distances.
    # ========================================================

    def select_variable(self, unassigned):

        request_map = {
            request.request_id: request
            for request in self.requests
        }

        def ranking(request_id):

            domain_size = len(
                self.domains[request_id]
            )

            request = request_map[request_id]

            distances = []

            for lift_name in self.domains[request_id]:

                tail = self.fixed_tail(
                    lift_name
                )

                distance = abs(
                    tail - request.floor
                )

                distances.append(distance)

            best = min(distances)
            worst = max(distances)

            # MRV first
            # Then prioritize requests with larger cost spread
            # Then request order
            return (
                domain_size,
                - (worst - best),
                request_id
            )

        return min(
            unassigned,
            key=ranking
        )

    # ========================================================
    # VALUE ORDERING
    # ========================================================
    #
    # Try the currently closest lift first.
    #
    # This does NOT decide the answer directly.
    # It only makes backtracking search faster.
    # ========================================================

    def order_values(self, request_id):

        request = next(
            request
            for request in self.requests
            if request.request_id == request_id
        )

        def distance_from_tail(lift_name):

            tail = self.fixed_tail(
                lift_name
            )

            return abs(
                tail - request.floor
            )

        return sorted(
            self.domains[request_id],
            key=lambda lift_name: (
                distance_from_tail(lift_name),
                lift_name
            )
        )

    # ========================================================
    # BACKTRACKING + BRANCH AND BOUND
    # ========================================================

    def backtrack(self, unassigned):

        self.nodes += 1

        # ----------------------------------------------------
        # BASE CASE
        # ----------------------------------------------------

        if not unassigned:

            metrics = self.calculate_metrics(
                self.assignment
            )

            objective = (
                metrics[0],
                metrics[1],
                metrics[2]
            )

            if objective < self.best_objective:

                self.best_objective = objective

                self.best_assignment = (
                    self.assignment.copy()
                )

            return

        # ----------------------------------------------------
        # BRANCH AND BOUND
        # ----------------------------------------------------
        #
        # Total waiting distance can only stay the same
        # or increase as more requests are added.
        #
        # Therefore if the partial solution is already worse
        # than the best known solution, stop exploring it.
        # ----------------------------------------------------

        partial_metrics = self.calculate_metrics(
            self.assignment
        )

        partial_waiting = partial_metrics[0]

        if (
            partial_waiting
            >= self.best_objective[0]
        ):

            self.backtracks += 1

            return

        # ----------------------------------------------------
        # MRV
        # ----------------------------------------------------

        request_id = self.select_variable(
            unassigned
        )

        # ----------------------------------------------------
        # TRY EACH POSSIBLE LIFT
        # ----------------------------------------------------

        for lift_name in self.order_values(
            request_id
        ):

            # Assign request
            self.assignment[
                request_id
            ] = lift_name

            # Recursive search
            self.backtrack(
                unassigned - {request_id}
            )

            # Backtrack
            del self.assignment[
                request_id
            ]

            self.backtracks += 1

    # ========================================================
    # SOLVE CSP
    # ========================================================

    def solve(self):

        self.backtrack(
            set(self.variables)
        )

        return (
            self.best_assignment,
            self.best_objective,
            self.nodes,
            self.backtracks
        )


# ============================================================
# GUI SIMULATOR
# ============================================================

class LiftSimulator:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "CSP Lift Scheduling Simulator"
        )

        self.root.geometry(
            "1200x760"
        )

        # ----------------------------------------------------
        # LIFTS
        # ----------------------------------------------------

        self.lifts = {
            name: Lift(
                name,
                INITIAL_POSITIONS[name]
            )
            for name in LIFT_NAMES
        }

        # ----------------------------------------------------
        # REQUESTS
        # ----------------------------------------------------

        self.requests = {}

        self.next_request_id = 1

        # ----------------------------------------------------
        # BATCH TIMER
        # ----------------------------------------------------

        self.batch_after_id = None

        # ----------------------------------------------------
        # LAST CSP RESULTS
        # ----------------------------------------------------

        self.last_csp_result = (
            "No CSP optimization has been performed."
        )

        # ----------------------------------------------------
        # LEFT CANVAS
        # ----------------------------------------------------

        self.canvas = tk.Canvas(
            root,
            width=800,
            height=700,
            bg="white"
        )

        self.canvas.pack(
            side=tk.LEFT,
            padx=10,
            pady=10
        )

        # ----------------------------------------------------
        # RIGHT PANEL
        # ----------------------------------------------------

        right = tk.Frame(root)

        right.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        tk.Label(
            right,
            text="CSP LIFT CONTROLLER",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        # ----------------------------------------------------
        # CALL BUTTONS
        # ----------------------------------------------------

        tk.Label(
            right,
            text="One Common Call Button",
            font=("Arial", 12, "bold")
        ).pack(pady=5)

        self.floor_buttons = {}

        for floor in reversed(FLOORS):

            button = tk.Button(
                right,
                text=f"CALL LIFT  •  FLOOR {floor}",
                width=28,
                height=2,
                font=("Arial", 10, "bold"),
                command=lambda f=floor:
                    self.call_lift(f)
            )

            button.pack(
                pady=3
            )

            self.floor_buttons[floor] = button

        # ----------------------------------------------------
        # CONTROL BUTTONS
        # ----------------------------------------------------

        tk.Button(
            right,
            text="LOAD CSP TEST SCENARIO",
            width=28,
            height=2,
            command=self.load_test_scenario
        ).pack(pady=(15, 4))

        tk.Button(
            right,
            text="OPTIMIZE PENDING REQUESTS",
            width=28,
            height=2,
            command=self.optimize_pending
        ).pack(pady=4)

        tk.Button(
            right,
            text="RANDOM REQUEST",
            width=28,
            height=2,
            command=self.random_request
        ).pack(pady=4)

        tk.Button(
            right,
            text="RESET",
            width=28,
            height=2,
            command=self.reset
        ).pack(pady=4)

        # ----------------------------------------------------
        # CURRENT STATUS
        # ----------------------------------------------------

        tk.Label(
            right,
            text="CURRENT SYSTEM",
            font=("Arial", 12, "bold")
        ).pack(pady=(15, 5))

        self.system_status = tk.Text(
            right,
            width=44,
            height=16,
            font=("Courier New", 9)
        )

        self.system_status.pack()

        # ----------------------------------------------------
        # EVENT LOG
        # ----------------------------------------------------

        tk.Label(
            right,
            text="CSP DECISION LOG",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5))

        self.log = tk.Text(
            right,
            width=44,
            height=11,
            font=("Courier New", 9)
        )

        self.log.pack()

        # ----------------------------------------------------
        # INITIAL DRAW
        # ----------------------------------------------------

        self.draw()

    # ========================================================
    # ADD REQUEST
    # ========================================================

    def call_lift(self, floor):

        request = Request(
            self.next_request_id,
            floor
        )

        self.requests[
            request.request_id
        ] = request

        self.next_request_id += 1

        self.write_log(
            f"P{request.request_id} called "
            f"from Floor {floor}."
        )

        self.draw()

        # ----------------------------------------------------
        # Delay optimization slightly.
        #
        # This allows multiple people pressing buttons quickly
        # to become one CSP batch.
        # ----------------------------------------------------

        if self.batch_after_id is not None:

            self.root.after_cancel(
                self.batch_after_id
            )

        self.batch_after_id = self.root.after(
            BATCH_DELAY,
            self.optimize_pending
        )

    # ========================================================
    # RANDOM REQUEST
    # ========================================================

    def random_request(self):

        floor = random.choice(
            FLOORS
        )

        self.call_lift(floor)

    # ========================================================
    # GET UNASSIGNED REQUESTS
    # ========================================================

    def get_pending_requests(self):

        return [
            request
            for request in self.requests.values()
            if (
                request.status == "WAITING"
                and request.assigned_lift is None
            )
        ]

    # ========================================================
    # BUILD LIFT SNAPSHOT
    # ========================================================

    def build_lift_snapshot(self):

        positions = {}

        routes = {}

        for name, lift in self.lifts.items():

            positions[name] = (
                lift.current_floor
            )

            routes[name] = (
                lift.planned_route()
            )

        return positions, routes

    # ========================================================
    # CSP OPTIMIZATION
    # ========================================================

    def optimize_pending(self):

        self.batch_after_id = None

        pending = self.get_pending_requests()

        if not pending:

            self.draw()

            return

        # ----------------------------------------------------
        # Take a snapshot of current lift state
        # ----------------------------------------------------

        positions, routes = (
            self.build_lift_snapshot()
        )

        # ----------------------------------------------------
        # CREATE CSP
        # ----------------------------------------------------

        csp = LiftCSP(
            positions,
            routes,
            pending
        )

        # ----------------------------------------------------
        # SOLVE
        # ----------------------------------------------------

        (
            best_assignment,
            objective,
            nodes,
            backtracks
        ) = csp.solve()

        if best_assignment is None:

            messagebox.showerror(
                "CSP Error",
                "No valid lift assignment found."
            )

            return

        # ----------------------------------------------------
        # APPLY CSP ASSIGNMENT
        # ----------------------------------------------------

        for request in pending:

            lift_name = best_assignment[
                request.request_id
            ]

            request.assigned_lift = (
                lift_name
            )

            request.status = "ASSIGNED"

        # ----------------------------------------------------
        # APPEND REQUESTS TO LIFT QUEUES
        # ----------------------------------------------------

        for lift_name in LIFT_NAMES:

            assigned_to_lift = [
                request
                for request in pending
                if request.assigned_lift
                == lift_name
            ]

            assigned_to_lift.sort(
                key=lambda request:
                request.request_id
            )

            lift = self.lifts[
                lift_name
            ]

            for request in assigned_to_lift:

                self.append_stop(
                    lift,
                    request.floor
                )

        # ----------------------------------------------------
        # CSP REPORT
        # ----------------------------------------------------

        total_waiting = objective[0]
        makespan = objective[1]
        total_travel = objective[2]

        report_lines = []

        report_lines.append(
            "CSP OPTIMIZATION RESULT"
        )

        report_lines.append(
            "=" * 38
        )

        for request in pending:

            report_lines.append(
                f"P{request.request_id} "
                f"(F{request.floor}) -> "
                f"{best_assignment[request.request_id]}"
            )

        report_lines.append("")
        report_lines.append(
            f"Total waiting distance : "
            f"{total_waiting}"
        )

        report_lines.append(
            f"Maximum lift route     : "
            f"{makespan}"
        )

        report_lines.append(
            f"Total lift travel      : "
            f"{total_travel}"
        )

        report_lines.append("")
        report_lines.append(
            "Algorithm:"
        )

        report_lines.append(
            "CSP + Backtracking + MRV"
        )

        report_lines.append(
            "Branch-and-Bound Optimization"
        )

        report_lines.append("")
        report_lines.append(
            f"Search nodes           : "
            f"{nodes}"
        )

        report_lines.append(
            f"Backtracks             : "
            f"{backtracks}"
        )

        self.last_csp_result = (
            "\n".join(report_lines)
        )

        self.write_log(
            "\n".join(report_lines)
        )

        # ----------------------------------------------------
        # START IDLE LIFTS
        # ----------------------------------------------------

        for lift in self.lifts.values():

            self.start_lift(
                lift
            )

        self.draw()

    # ========================================================
    # APPEND STOP
    # ========================================================

    def append_stop(self, lift, floor):

        route = lift.planned_route()

        # Don't create duplicate consecutive stops
        if route and route[-1] == floor:
            return

        lift.queue.append(
            floor
        )

    # ========================================================
    # START LIFT
    # ========================================================

    def start_lift(self, lift):

        if lift.moving:
            return

        # Remove useless queue entries
        self.clean_queue(
            lift
        )

        if not lift.queue:
            return

        lift.target_floor = (
            lift.queue.pop(0)
        )

        lift.moving = True

        self.move_lift(
            lift
        )

    # ========================================================
    # REMOVE COMPLETED QUEUE ENTRIES
    # ========================================================

    def clean_queue(self, lift):

        valid_queue = []

        for floor in lift.queue:

            waiting_exists = any(
                request.status == "ASSIGNED"
                and request.assigned_lift
                == lift.name
                and request.floor
                == floor
                for request in
                self.requests.values()
            )

            if waiting_exists:
                valid_queue.append(
                    floor
                )

        lift.queue = valid_queue

    # ========================================================
    # MOVE LIFT
    # ========================================================

    def move_lift(self, lift):

        target = lift.target_floor

        # ----------------------------------------------------
        # Reached destination
        # ----------------------------------------------------

        if lift.current_floor == target:

            self.pickup_people(
                lift,
                target
            )

            return

        # ----------------------------------------------------
        # Move up
        # ----------------------------------------------------

        if target > lift.current_floor:

            lift.current_floor += 1

        # ----------------------------------------------------
        # Move down
        # ----------------------------------------------------

        else:

            lift.current_floor -= 1

        self.draw()

        lift.after_id = self.root.after(
            MOVE_TIME,
            lambda:
                self.move_lift(lift)
        )

    # ========================================================
    # PICK UP PEOPLE
    # ========================================================

    def pickup_people(self, lift, floor):

        picked = []

        for request in self.requests.values():

            if (
                request.status == "ASSIGNED"
                and request.assigned_lift
                == lift.name
                and request.floor == floor
            ):

                request.status = "COMPLETED"

                picked.append(
                    request.request_id
                )

        if picked:

            lift.served += len(
                picked
            )

            people = ", ".join(
                f"P{rid}"
                for rid in picked
            )

            self.write_log(
                f"{lift.name} picked up "
                f"{people} at Floor {floor}."
            )

        # ----------------------------------------------------
        # Continue route
        # ----------------------------------------------------

        lift.target_floor = None

        self.clean_queue(
            lift
        )

        if lift.queue:

            lift.target_floor = (
                lift.queue.pop(0)
            )

            self.move_lift(
                lift
            )

        else:

            lift.moving = False

            self.draw()

    # ========================================================
    # DRAW BUILDING
    # ========================================================

    def draw(self):

        self.canvas.delete(
            "all"
        )

        floor_height = 120

        top = 50

        shaft_width = 110

        shaft_x = [
            130,
            345,
            560
        ]

        # ----------------------------------------------------
        # FLOOR LINES
        # ----------------------------------------------------

        for floor in reversed(
            FLOORS
        ):

            y = (
                top
                + (NUM_FLOORS - floor)
                * floor_height
            )

            self.canvas.create_line(
                60,
                y,
                760,
                y,
                width=2
            )

            self.canvas.create_text(
                25,
                y + 45,
                text=f"F{floor}",
                font=(
                    "Arial",
                    12,
                    "bold"
                )
            )

        # ----------------------------------------------------
        # LIFT SHAFTS
        # ----------------------------------------------------

        for i, x in enumerate(
            shaft_x
        ):

            self.canvas.create_rectangle(
                x,
                top,
                x + shaft_width,
                top + floor_height * NUM_FLOORS,
                outline="black",
                width=2
            )

            self.canvas.create_text(
                x + shaft_width / 2,
                25,
                text=LIFT_NAMES[i],
                font=(
                    "Arial",
                    12,
                    "bold"
                )
            )

        # ----------------------------------------------------
        # DRAW LIFTS
        # ----------------------------------------------------

        for i, lift_name in enumerate(
            LIFT_NAMES
        ):

            lift = self.lifts[
                lift_name
            ]

            x = shaft_x[i] + 10

            y = (
                top
                + (
                    NUM_FLOORS
                    - lift.current_floor
                ) * floor_height
                + 10
            )

            self.canvas.create_rectangle(
                x,
                y,
                x + shaft_width - 20,
                y + floor_height - 20,
                fill="lightblue",
                outline="black",
                width=2
            )

            self.canvas.create_text(
                x + (
                    shaft_width - 20
                ) / 2,
                y + 35,
                text=lift.name,
                font=(
                    "Arial",
                    11,
                    "bold"
                )
            )

            state = (
                f"F{lift.current_floor}"
            )

            if lift.moving:

                state += (
                    f" → F"
                    f"{lift.target_floor}"
                )

            self.canvas.create_text(
                x + (
                    shaft_width - 20
                ) / 2,
                y + 65,
                text=state,
                font=(
                    "Arial",
                    10
                )
            )

        # ----------------------------------------------------
        # DRAW WAITING PEOPLE
        # ----------------------------------------------------

        floor_people = {
            floor: []
            for floor in FLOORS
        }

        for request in (
            self.requests.values()
        ):

            if request.status in (
                "WAITING",
                "ASSIGNED"
            ):

                floor_people[
                    request.floor
                ].append(request)

        for floor in FLOORS:

            y = (
                top
                + (
                    NUM_FLOORS - floor
                ) * floor_height
                + 85
            )

            for i, request in enumerate(
                floor_people[floor]
            ):

                x = (
                    75
                    + i * 28
                )

                self.canvas.create_oval(
                    x,
                    y,
                    x + 16,
                    y + 16,
                    fill="black"
                )

                self.canvas.create_text(
                    x + 8,
                    y + 28,
                    text=f"P{request.request_id}",
                    font=("Arial", 8)
                )

        self.update_status()

    # ========================================================
    # UPDATE SYSTEM STATUS
    # ========================================================

    def update_status(self):

        self.system_status.delete(
            "1.0",
            tk.END
        )

        self.system_status.insert(
            tk.END,
            "LIFT STATUS\n"
        )

        self.system_status.insert(
            tk.END,
            "=" * 38
            + "\n"
        )

        for lift_name in LIFT_NAMES:

            lift = self.lifts[
                lift_name
            ]

            if lift.moving:

                state = (
                    f"MOVING -> F"
                    f"{lift.target_floor}"
                )

            else:

                state = "IDLE"

            self.system_status.insert(
                tk.END,
                f"{lift.name:<8} "
                f"Floor {lift.current_floor:<3} "
                f"{state}\n"
            )

            self.system_status.insert(
                tk.END,
                f"  Queue : "
                f"{lift.queue}\n"
            )

            self.system_status.insert(
                tk.END,
                f"  Served: "
                f"{lift.served}\n"
            )

        # ----------------------------------------------------
        # PEOPLE
        # ----------------------------------------------------

        self.system_status.insert(
            tk.END,
            "\nPEOPLE\n"
        )

        waiting = [
            request
            for request in
            self.requests.values()
            if request.status == "WAITING"
        ]

        assigned = [
            request
            for request in
            self.requests.values()
            if request.status == "ASSIGNED"
        ]

        completed = [
            request
            for request in
            self.requests.values()
            if request.status == "COMPLETED"
        ]

        self.system_status.insert(
            tk.END,
            f"Waiting   : {len(waiting)}\n"
        )

        self.system_status.insert(
            tk.END,
            f"Assigned  : {len(assigned)}\n"
        )

        self.system_status.insert(
            tk.END,
            f"Completed : {len(completed)}\n"
        )

        self.system_status.insert(
            tk.END,
            "\n"
        )

        self.system_status.insert(
            tk.END,
            self.last_csp_result
        )

    # ========================================================
    # LOG
    # ========================================================

    def write_log(self, message):

        self.log.insert(
            tk.END,
            "\n"
            + message
            + "\n"
        )

        self.log.see(
            tk.END
        )

    # ========================================================
    # LOAD TEST SCENARIO
    # ========================================================

    def load_test_scenario(self):

        # Clear current system
        self.reset(
            ask=False
        )

        # Example requests
        test_floors = [
            4,
            2,
            5,
            1,
            4,
            3,
            2,
            5
        ]

        for floor in test_floors:

            request = Request(
                self.next_request_id,
                floor
            )

            self.requests[
                request.request_id
            ] = request

            self.next_request_id += 1

        self.write_log(
            "Loaded test scenario:"
        )

        self.write_log(
            "Floors = "
            + str(test_floors)
        )

        self.draw()

        # Solve all requests together
        self.optimize_pending()

    # ========================================================
    # RESET
    # ========================================================

    def reset(self, ask=True):

        if ask:

            result = messagebox.askyesno(
                "Reset",
                "Reset the complete simulator?"
            )

            if not result:
                return

        # ----------------------------------------------------
        # Cancel animations
        # ----------------------------------------------------

        for lift in self.lifts.values():

            if lift.after_id is not None:

                try:
                    self.root.after_cancel(
                        lift.after_id
                    )
                except tk.TclError:
                    pass

            lift.after_id = None

        # ----------------------------------------------------
        # Reset lifts
        # ----------------------------------------------------

        for lift_name, lift in (
            self.lifts.items()
        ):

            lift.current_floor = (
                INITIAL_POSITIONS[
                    lift_name
                ]
            )

            lift.target_floor = None
            lift.queue.clear()
            lift.moving = False
            lift.served = 0

        # ----------------------------------------------------
        # Reset people
        # ----------------------------------------------------

        self.requests.clear()

        self.next_request_id = 1

        self.last_csp_result = (
            "No CSP optimization has been performed."
        )

        self.log.delete(
            "1.0",
            tk.END
        )

        self.draw()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    simulator = LiftSimulator(
        root
    )

    root.mainloop()