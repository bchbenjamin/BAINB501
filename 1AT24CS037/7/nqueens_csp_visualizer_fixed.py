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
# Each passenger request contains:
#   SOURCE      -> floor where the passenger is waiting
#   DESTINATION -> floor where the passenger wants to go
#
# The CSP assigns one lift to every request.
# A lift first goes to SOURCE (pickup), then DESTINATION (drop-off).
# ============================================================

import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass
from math import inf
import random


NUM_FLOORS = 5
NUM_LIFTS = 3

FLOORS = list(range(1, NUM_FLOORS + 1))
LIFT_NAMES = ["Lift 1", "Lift 2", "Lift 3"]

INITIAL_POSITIONS = {
    "Lift 1": 1,
    "Lift 2": 3,
    "Lift 3": 5,
}

MOVE_TIME = 700
BATCH_DELAY = 500


@dataclass
class Request:
    request_id: int
    source: int
    destination: int
    assigned_lift: str | None = None
    # WAITING -> ASSIGNED -> ONBOARD -> COMPLETED
    status: str = "WAITING"


class Lift:

    def __init__(self, name, start_floor):
        self.name = name
        self.current_floor = start_floor
        self.target_floor = None

        # (request_id, floor, "PICKUP"/"DROPOFF")
        self.queue = []

        self.moving = False
        self.served = 0
        self.after_id = None
        self.current_request_id = None
        self.current_action = None

    def planned_route(self):
        route = []

        if self.target_floor is not None:
            route.append(self.target_floor)

        route.extend(stop[1] for stop in self.queue)
        return route

    def is_idle(self):
        return (
            not self.moving
            and self.target_floor is None
            and not self.queue
        )


class LiftCSP:

    def __init__(self, lift_positions, lift_routes, requests):
        self.lift_names = list(lift_positions.keys())
        self.lift_positions = dict(lift_positions)

        self.lift_routes = {
            lift: list(route)
            for lift, route in lift_routes.items()
        }

        self.requests = sorted(
            requests,
            key=lambda r: r.request_id
        )

        self.variables = [
            request.request_id
            for request in self.requests
        ]

        self.domains = {
            request.request_id: self.lift_names.copy()
            for request in self.requests
        }

        self.assignment = {}
        self.best_assignment = None
        self.best_objective = (inf, inf, inf)

        self.nodes = 0
        self.backtracks = 0

    @staticmethod
    def compact_route(route):
        result = []

        for floor in route:
            if not result or floor != result[-1]:
                result.append(floor)

        return result

    def fixed_tail(self, lift_name):
        route = self.compact_route(
            self.lift_routes.get(lift_name, [])
        )

        if route:
            return route[-1]

        return self.lift_positions[lift_name]

    def calculate_metrics(self, assignment):
        """
        For each assigned passenger:
            lift -> SOURCE -> DESTINATION

        Waiting distance is measured only until SOURCE,
        because that is when the passenger is picked up.
        """

        total_waiting = 0
        total_travel = 0
        makespan = 0
        per_lift = {}

        for lift_name in self.lift_names:
            position = self.lift_positions[lift_name]

            fixed_route = self.compact_route(
                self.lift_routes.get(lift_name, [])
            )

            fixed_travel = 0

            for floor in fixed_route:
                distance = abs(position - floor)
                fixed_travel += distance
                position = floor

            assigned_requests = [
                request
                for request in self.requests
                if assignment.get(request.request_id) == lift_name
            ]

            assigned_requests.sort(
                key=lambda request: request.request_id
            )

            cumulative_travel = fixed_travel
            request_waits = {}

            for request in assigned_requests:
                # Pickup
                if position != request.source:
                    distance = abs(position - request.source)
                    cumulative_travel += distance
                    position = request.source

                request_waits[request.request_id] = cumulative_travel
                total_waiting += cumulative_travel

                # Drop-off
                if position != request.destination:
                    distance = abs(
                        position - request.destination
                    )
                    cumulative_travel += distance
                    position = request.destination

            total_travel += cumulative_travel

            if assigned_requests:
                makespan = max(
                    makespan,
                    cumulative_travel
                )

            per_lift[lift_name] = {
                "requests": assigned_requests,
                "waits": request_waits,
                "total_travel": cumulative_travel,
            }

        return (
            total_waiting,
            makespan,
            total_travel,
            per_lift,
        )

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
                tail = self.fixed_tail(lift_name)
                distances.append(
                    abs(tail - request.source)
                )

            best = min(distances)
            worst = max(distances)

            return (
                domain_size,
                -(worst - best),
                request_id,
            )

        return min(unassigned, key=ranking)

    def order_values(self, request_id):
        request = next(
            request
            for request in self.requests
            if request.request_id == request_id
        )

        def distance_from_tail(lift_name):
            tail = self.fixed_tail(lift_name)
            return abs(tail - request.source)

        return sorted(
            self.domains[request_id],
            key=lambda lift_name: (
                distance_from_tail(lift_name),
                lift_name,
            )
        )

    def backtrack(self, unassigned):
        self.nodes += 1

        if not unassigned:
            metrics = self.calculate_metrics(
                self.assignment
            )

            objective = (
                metrics[0],
                metrics[1],
                metrics[2],
            )

            if objective < self.best_objective:
                self.best_objective = objective
                self.best_assignment = (
                    self.assignment.copy()
                )

            return

        partial_metrics = self.calculate_metrics(
            self.assignment
        )

        if partial_metrics[0] >= self.best_objective[0]:
            self.backtracks += 1
            return

        request_id = self.select_variable(
            unassigned
        )

        for lift_name in self.order_values(request_id):
            self.assignment[request_id] = lift_name

            self.backtrack(
                unassigned - {request_id}
            )

            del self.assignment[request_id]
            self.backtracks += 1

    def solve(self):
        self.backtrack(set(self.variables))

        return (
            self.best_assignment,
            self.best_objective,
            self.nodes,
            self.backtracks,
        )


class LiftSimulator:

    def __init__(self, root):
        self.root = root
        self.root.title(
            "CSP Lift Scheduling Simulator - Source & Destination"
        )
        self.root.geometry("1280x800")

        self.lifts = {
            name: Lift(
                name,
                INITIAL_POSITIONS[name]
            )
            for name in LIFT_NAMES
        }

        self.requests = {}
        self.next_request_id = 1
        self.batch_after_id = None

        self.last_csp_result = (
            "No CSP optimization has been performed."
        )

        self.canvas = tk.Canvas(
            root,
            width=800,
            height=720,
            bg="white",
        )
        self.canvas.pack(
            side=tk.LEFT,
            padx=10,
            pady=10,
        )

        right = tk.Frame(root)
        right.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        tk.Label(
            right,
            text="CSP LIFT CONTROLLER",
            font=("Arial", 18, "bold"),
        ).pack(pady=8)

        # ---------------- SOURCE / DESTINATION ----------------

        request_frame = tk.LabelFrame(
            right,
            text="Passenger Request",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=8,
        )
        request_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            request_frame,
            text="Source floor:",
        ).grid(row=0, column=0, sticky="w", pady=4)

        self.source_var = tk.StringVar(value="1")

        ttk.Combobox(
            request_frame,
            textvariable=self.source_var,
            values=[str(f) for f in FLOORS],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, padx=5, pady=4)

        tk.Label(
            request_frame,
            text="Destination:",
        ).grid(row=1, column=0, sticky="w", pady=4)

        self.destination_var = tk.StringVar(value="2")

        ttk.Combobox(
            request_frame,
            textvariable=self.destination_var,
            values=[str(f) for f in FLOORS],
            state="readonly",
            width=10,
        ).grid(row=1, column=1, padx=5, pady=4)

        tk.Button(
            request_frame,
            text="REQUEST LIFT",
            width=18,
            height=2,
            font=("Arial", 10, "bold"),
            command=self.submit_request,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            pady=(8, 3),
        )

        # ---------------- QUICK SOURCE BUTTONS ----------------

        tk.Label(
            right,
            text="Quick Source Selection",
            font=("Arial", 11, "bold"),
        ).pack(pady=(8, 3))

        quick_frame = tk.Frame(right)
        quick_frame.pack()

        for floor in FLOORS:
            tk.Button(
                quick_frame,
                text=f"F{floor}",
                width=5,
                command=lambda f=floor:
                    self.select_source(f),
            ).pack(side=tk.LEFT, padx=2)

        # ---------------- CONTROLS ----------------

        tk.Button(
            right,
            text="LOAD CSP TEST SCENARIO",
            width=28,
            height=2,
            command=self.load_test_scenario,
        ).pack(pady=(12, 4))

        tk.Button(
            right,
            text="OPTIMIZE PENDING REQUESTS",
            width=28,
            height=2,
            command=self.optimize_pending,
        ).pack(pady=4)

        tk.Button(
            right,
            text="RANDOM REQUEST",
            width=28,
            height=2,
            command=self.random_request,
        ).pack(pady=4)

        tk.Button(
            right,
            text="RESET",
            width=28,
            height=2,
            command=self.reset,
        ).pack(pady=4)

        tk.Label(
            right,
            text="CURRENT SYSTEM",
            font=("Arial", 11, "bold"),
        ).pack(pady=(10, 3))

        self.system_status = tk.Text(
            right,
            width=47,
            height=17,
            font=("Courier New", 9),
        )
        self.system_status.pack()

        tk.Label(
            right,
            text="CSP DECISION LOG",
            font=("Arial", 11, "bold"),
        ).pack(pady=(8, 3))

        self.log = tk.Text(
            right,
            width=47,
            height=10,
            font=("Courier New", 9),
        )
        self.log.pack()

        self.draw()

    def select_source(self, floor):
        self.source_var.set(str(floor))

    def submit_request(self):
        source = int(self.source_var.get())
        destination = int(self.destination_var.get())

        if source == destination:
            messagebox.showwarning(
                "Invalid Request",
                "Source and destination must be different floors.",
            )
            return

        self.create_request(source, destination)

    def create_request(self, source, destination):
        request = Request(
            self.next_request_id,
            source,
            destination,
        )

        self.requests[request.request_id] = request
        self.next_request_id += 1

        self.write_log(
            f"P{request.request_id}: "
            f"F{source} -> F{destination} "
            f"(waiting for CSP assignment)."
        )

        self.draw()

        if self.batch_after_id is not None:
            self.root.after_cancel(self.batch_after_id)

        self.batch_after_id = self.root.after(
            BATCH_DELAY,
            self.optimize_pending,
        )

    def random_request(self):
        source = random.choice(FLOORS)
        destinations = [
            floor for floor in FLOORS
            if floor != source
        ]
        destination = random.choice(destinations)

        self.source_var.set(str(source))
        self.destination_var.set(str(destination))

        self.create_request(source, destination)

    def get_pending_requests(self):
        return [
            request
            for request in self.requests.values()
            if (
                request.status == "WAITING"
                and request.assigned_lift is None
            )
        ]

    def build_lift_snapshot(self):
        positions = {}
        routes = {}

        for name, lift in self.lifts.items():
            positions[name] = lift.current_floor
            routes[name] = lift.planned_route()

        return positions, routes

    def optimize_pending(self):
        self.batch_after_id = None

        pending = self.get_pending_requests()

        if not pending:
            self.draw()
            return

        positions, routes = self.build_lift_snapshot()

        csp = LiftCSP(
            positions,
            routes,
            pending,
        )

        (
            best_assignment,
            objective,
            nodes,
            backtracks,
        ) = csp.solve()

        if best_assignment is None:
            messagebox.showerror(
                "CSP Error",
                "No valid lift assignment found.",
            )
            return

        for request in pending:
            lift_name = best_assignment[
                request.request_id
            ]

            request.assigned_lift = lift_name
            request.status = "ASSIGNED"

        # Every passenger produces TWO stops:
        #   1. pickup at source
        #   2. drop-off at destination
        for lift_name in LIFT_NAMES:
            assigned_to_lift = [
                request
                for request in pending
                if request.assigned_lift == lift_name
            ]

            assigned_to_lift.sort(
                key=lambda request: request.request_id
            )

            lift = self.lifts[lift_name]

            for request in assigned_to_lift:
                self.append_stop(
                    lift,
                    request.request_id,
                    request.source,
                    "PICKUP",
                )
                self.append_stop(
                    lift,
                    request.request_id,
                    request.destination,
                    "DROPOFF",
                )

        report_lines = [
            "CSP OPTIMIZATION RESULT",
            "=" * 42,
        ]

        for request in pending:
            report_lines.append(
                f"P{request.request_id}: "
                f"F{request.source} -> F{request.destination} "
                f"-> {best_assignment[request.request_id]}"
            )

        report_lines.extend([
            "",
            f"Total pickup waiting : {objective[0]}",
            f"Maximum lift route   : {objective[1]}",
            f"Total lift travel    : {objective[2]}",
            "",
            "Algorithm:",
            "CSP + Backtracking + MRV",
            "Branch-and-Bound Optimization",
            "",
            f"Search nodes         : {nodes}",
            f"Backtracks           : {backtracks}",
        ])

        self.last_csp_result = "\n".join(report_lines)
        self.write_log(self.last_csp_result)

        for lift in self.lifts.values():
            self.start_lift(lift)

        self.draw()

    def append_stop(self, lift, request_id, floor, action):
        lift.queue.append(
            (request_id, floor, action)
        )

    def start_lift(self, lift):
        if lift.moving:
            return

        self.clean_queue(lift)

        if not lift.queue:
            return

        (
            request_id,
            floor,
            action,
        ) = lift.queue.pop(0)

        lift.target_floor = floor
        lift.current_request_id = request_id
        lift.current_action = action
        lift.moving = True

        self.move_lift(lift)

    def clean_queue(self, lift):
        valid_queue = []

        for request_id, floor, action in lift.queue:
            request = self.requests.get(request_id)

            if request is None:
                continue

            if action == "PICKUP":
                valid = request.status == "ASSIGNED"
            else:
                valid = request.status == "ONBOARD"

            if valid:
                valid_queue.append(
                    (request_id, floor, action)
                )

        lift.queue = valid_queue

    def move_lift(self, lift):
        target = lift.target_floor

        if target is None:
            lift.moving = False
            return

        if lift.current_floor == target:
            self.process_stop(
                lift,
                target,
                lift.current_request_id,
                lift.current_action,
            )
            return

        if target > lift.current_floor:
            lift.current_floor += 1
        else:
            lift.current_floor -= 1

        self.draw()

        lift.after_id = self.root.after(
            MOVE_TIME,
            lambda: self.move_lift(lift),
        )

    def process_stop(
        self,
        lift,
        floor,
        request_id,
        action,
    ):
        request = self.requests.get(request_id)

        if request is None:
            self.finish_current_stop(lift)
            return

        if action == "PICKUP":
            if (
                request.status == "ASSIGNED"
                and request.source == floor
            ):
                request.status = "ONBOARD"

                self.write_log(
                    f"{lift.name} picked up "
                    f"P{request.request_id} at F{floor} "
                    f"-> F{request.destination}."
                )

        elif action == "DROPOFF":
            if (
                request.status == "ONBOARD"
                and request.destination == floor
            ):
                request.status = "COMPLETED"
                lift.served += 1

                self.write_log(
                    f"{lift.name} dropped off "
                    f"P{request.request_id} at F{floor}."
                )

        self.finish_current_stop(lift)

    def finish_current_stop(self, lift):
        lift.target_floor = None
        lift.current_request_id = None
        lift.current_action = None

        self.clean_queue(lift)

        if lift.queue:
            (
                request_id,
                floor,
                action,
            ) = lift.queue.pop(0)

            lift.target_floor = floor
            lift.current_request_id = request_id
            lift.current_action = action
            lift.moving = True

            self.draw()
            self.move_lift(lift)
        else:
            lift.moving = False
            self.draw()

    def draw(self):
        self.canvas.delete("all")

        floor_height = 120
        top = 50
        shaft_width = 110
        shaft_x = [130, 345, 560]

        for floor in reversed(FLOORS):
            y = (
                top
                + (NUM_FLOORS - floor) * floor_height
            )

            self.canvas.create_line(
                60, y, 760, y, width=2
            )

            self.canvas.create_text(
                25,
                y + 45,
                text=f"F{floor}",
                font=("Arial", 12, "bold"),
            )

        for i, x in enumerate(shaft_x):
            self.canvas.create_rectangle(
                x,
                top,
                x + shaft_width,
                top + floor_height * NUM_FLOORS,
                outline="black",
                width=2,
            )

            self.canvas.create_text(
                x + shaft_width / 2,
                25,
                text=LIFT_NAMES[i],
                font=("Arial", 12, "bold"),
            )

        for i, lift_name in enumerate(LIFT_NAMES):
            lift = self.lifts[lift_name]

            x = shaft_x[i] + 10
            y = (
                top
                + (NUM_FLOORS - lift.current_floor)
                * floor_height
                + 10
            )

            self.canvas.create_rectangle(
                x,
                y,
                x + shaft_width - 20,
                y + floor_height - 20,
                fill="lightblue",
                outline="black",
                width=2,
            )

            self.canvas.create_text(
                x + (shaft_width - 20) / 2,
                y + 35,
                text=lift.name,
                font=("Arial", 11, "bold"),
            )

            state = f"F{lift.current_floor}"

            if lift.moving:
                state += f" -> F{lift.target_floor}"

            self.canvas.create_text(
                x + (shaft_width - 20) / 2,
                y + 65,
                text=state,
                font=("Arial", 10),
            )

            if lift.current_request_id is not None:
                action_text = lift.current_action
                self.canvas.create_text(
                    x + (shaft_width - 20) / 2,
                    y + 88,
                    text=(
                        f"P{lift.current_request_id} "
                        f"{action_text}"
                    ),
                    font=("Arial", 8),
                )

        floor_people = {
            floor: []
            for floor in FLOORS
        }

        for request in self.requests.values():
            if request.status in ("WAITING", "ASSIGNED"):
                floor_people[request.source].append(request)

        for floor in FLOORS:
            y = (
                top
                + (NUM_FLOORS - floor) * floor_height
                + 85
            )

            for i, request in enumerate(
                floor_people[floor]
            ):
                x = 75 + i * 35

                self.canvas.create_oval(
                    x,
                    y,
                    x + 16,
                    y + 16,
                    fill="black",
                )

                self.canvas.create_text(
                    x + 8,
                    y + 29,
                    text=f"P{request.request_id}",
                    font=("Arial", 8),
                )

                self.canvas.create_text(
                    x + 8,
                    y + 41,
                    text=f"->F{request.destination}",
                    font=("Arial", 7),
                )

        self.update_status()

    def update_status(self):
        self.system_status.delete("1.0", tk.END)

        self.system_status.insert(
            tk.END,
            "LIFT STATUS\n" + "=" * 42 + "\n",
        )

        for lift_name in LIFT_NAMES:
            lift = self.lifts[lift_name]

            state = (
                f"MOVING -> F{lift.target_floor}"
                if lift.moving
                else "IDLE"
            )

            self.system_status.insert(
                tk.END,
                f"{lift.name:<8} "
                f"Floor {lift.current_floor:<3} "
                f"{state}\n",
            )

            queue_display = [
                (f"P{r}", f"F{f}", a)
                for r, f, a in lift.queue
            ]

            self.system_status.insert(
                tk.END,
                f"  Queue : {queue_display}\n",
            )

            self.system_status.insert(
                tk.END,
                f"  Served: {lift.served}\n",
            )

        self.system_status.insert(
            tk.END,
            "\nPEOPLE\n",
        )

        statuses = {
            "WAITING": 0,
            "ASSIGNED": 0,
            "ONBOARD": 0,
            "COMPLETED": 0,
        }

        for request in self.requests.values():
            statuses[request.status] += 1

        self.system_status.insert(
            tk.END,
            f"Waiting   : {statuses['WAITING']}\n"
            f"Assigned  : {statuses['ASSIGNED']}\n"
            f"Onboard   : {statuses['ONBOARD']}\n"
            f"Completed : {statuses['COMPLETED']}\n",
        )

        self.system_status.insert(
            tk.END,
            "\nREQUESTS\n",
        )

        for request in self.requests.values():
            lift = request.assigned_lift or "-"

            self.system_status.insert(
                tk.END,
                f"P{request.request_id}: "
                f"F{request.source}->F{request.destination} "
                f"{request.status:<9} {lift}\n",
            )

        self.system_status.insert(
            tk.END,
            "\n" + self.last_csp_result,
        )

    def write_log(self, message):
        self.log.insert(
            tk.END,
            "\n" + message + "\n",
        )
        self.log.see(tk.END)

    def load_test_scenario(self):
        self.reset(ask=False)

        # (SOURCE, DESTINATION)
        test_requests = [
            (4, 1),
            (2, 5),
            (5, 2),
            (1, 4),
            (4, 3),
            (3, 5),
            (2, 1),
            (5, 4),
        ]

        for source, destination in test_requests:
            request = Request(
                self.next_request_id,
                source,
                destination,
            )

            self.requests[request.request_id] = request
            self.next_request_id += 1

        self.write_log(
            "Loaded test scenario:"
        )
        self.write_log(
            "Requests = " + str(test_requests)
        )

        self.draw()
        self.optimize_pending()

    def reset(self, ask=True):
        if ask:
            result = messagebox.askyesno(
                "Reset",
                "Reset the complete simulator?",
            )

            if not result:
                return

        if self.batch_after_id is not None:
            try:
                self.root.after_cancel(
                    self.batch_after_id
                )
            except tk.TclError:
                pass

            self.batch_after_id = None

        for lift in self.lifts.values():
            if lift.after_id is not None:
                try:
                    self.root.after_cancel(
                        lift.after_id
                    )
                except tk.TclError:
                    pass

            lift.after_id = None

        for lift_name, lift in self.lifts.items():
            lift.current_floor = INITIAL_POSITIONS[lift_name]
            lift.target_floor = None
            lift.queue.clear()
            lift.moving = False
            lift.served = 0
            lift.current_request_id = None
            lift.current_action = None

        self.requests.clear()
        self.next_request_id = 1

        self.last_csp_result = (
            "No CSP optimization has been performed."
        )

        self.log.delete("1.0", tk.END)
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    simulator = LiftSimulator(root)
    root.mainloop()
