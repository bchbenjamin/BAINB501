"""Romania Map Search Visualizer

Algorithms are intentionally isolated in SearchEngine:
    dfs, bfs, ucs, a_star, befs

The visualization uses Matplotlib embedded in Tkinter. Search methods return a
SearchResult containing a valid parent tree, expansion order, and final path.
Only real graph edges are drawn; consecutive visited nodes are never joined.
"""

from __future__ import annotations

import heapq
import math
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


@dataclass(frozen=True)
class Edge:
    destination: str
    cost: int


@dataclass
class SearchResult:
    algorithm: str
    start: str
    goal: str
    expanded_order: List[str]
    discovery_edges: List[Tuple[str, str]]
    path: List[str]
    path_cost: Optional[int]
    elapsed_ms: float
    found: bool


class RomaniaGraph:
    """Undirected weighted Romania road graph from the supplied map."""

    # Coordinates are in image-like space: x increases rightward and y
    # increases upward for Matplotlib.
    COORDINATES: Dict[str, Tuple[float, float]] = {
        "Oradea": (1.4, 8.6),
        "Zerind": (0.8, 7.1),
        "Arad": (0.2, 5.5),
        "Timisoara": (0.25, 3.3),
        "Lugoj": (2.2, 2.15),
        "Mehadia": (2.2, 0.65),
        "Drobeta": (2.2, -1.05),
        "Craiova": (4.9, -1.45),
        "Sibiu": (5.0, 4.95),
        "Rimnicu Vilcea": (5.85, 3.55),
        "Pitesti": (8.2, 2.25),
        "Fagaras": (8.0, 4.95),
        "Bucharest": (10.4, 0.85),
        "Giurgiu": (9.55, -2.25),
        "Urziceni": (12.1, 2.15),
        "Hirsova": (14.1, 2.15),
        "Eforie": (15.0, -1.05),
        "Vaslui": (13.75, 4.5),
        "Iasi": (12.65, 6.45),
        "Neamt": (10.65, 7.85),
    }

    EDGES = [
        ("Oradea", "Zerind", 71),
        ("Zerind", "Arad", 75),
        ("Arad", "Timisoara", 118),
        ("Timisoara", "Lugoj", 111),
        ("Lugoj", "Mehadia", 70),
        ("Mehadia", "Drobeta", 75),
        ("Drobeta", "Craiova", 120),
        ("Craiova", "Pitesti", 138),
        ("Craiova", "Rimnicu Vilcea", 146),
        ("Rimnicu Vilcea", "Sibiu", 80),
        ("Rimnicu Vilcea", "Pitesti", 97),
        ("Sibiu", "Arad", 140),
        ("Sibiu", "Oradea", 151),
        ("Sibiu", "Fagaras", 99),
        ("Fagaras", "Bucharest", 211),
        ("Pitesti", "Bucharest", 101),
        ("Bucharest", "Giurgiu", 90),
        ("Bucharest", "Urziceni", 85),
        ("Urziceni", "Hirsova", 98),
        ("Hirsova", "Eforie", 86),
        ("Urziceni", "Vaslui", 142),
        ("Vaslui", "Iasi", 92),
        ("Iasi", "Neamt", 87),
    ]

    def __init__(self) -> None:
        self.adjacency: Dict[str, List[Edge]] = {
            city: [] for city in self.COORDINATES
        }
        for first, second, cost in self.EDGES:
            self.adjacency[first].append(Edge(second, cost))
            self.adjacency[second].append(Edge(first, cost))
        # Preserve the road order from the supplied map.
        # This order is intentionally used by DFS to make its traversal
        # deterministic and visually consistent with the map (top/left
        # branches are considered before later branches when pushed onto
        # the stack in reverse order). Do not alphabetically sort here.

        # Heuristic values supplied in the reference slide. These are
        # straight-line estimates to Bucharest and must be used by A* and
        # Greedy Best-First Search when Bucharest is the selected goal.
        self.hsl_to_bucharest: Dict[str, int] = {
            "Arad": 366,
            "Bucharest": 0,
            "Craiova": 160,
            "Drobeta": 242,
            "Eforie": 161,
            "Fagaras": 176,
            "Giurgiu": 77,
            "Hirsova": 151,
            "Iasi": 226,
            "Lugoj": 244,
            "Mehadia": 241,
            "Neamt": 234,
            "Oradea": 380,
            "Pitesti": 100,
            "Rimnicu Vilcea": 193,
            "Sibiu": 253,
            "Timisoara": 329,
            "Urziceni": 80,
            "Vaslui": 199,
            "Zerind": 374,
        }

    def heuristic(self, node: str, goal: str) -> float:
        """Return h(n). The supplied HSL table is for Bucharest.

        For another selected goal, use a geometric lower-bound estimate
        derived from the map coordinates so that the GUI remains flexible
        without incorrectly applying Bucharest-specific HSL values.
        """
        if goal == "Bucharest":
            return float(self.hsl_to_bucharest[node])

        # For non-Bucharest goals, use a conservative geometric estimate.
        # The scale is based on the minimum road-cost / map-distance ratio.
        ratios = []
        for first, second, cost in self.EDGES:
            x1, y1 = self.COORDINATES[first]
            x2, y2 = self.COORDINATES[second]
            distance = math.hypot(x2 - x1, y2 - y1)
            if distance > 0:
                ratios.append(cost / distance)
        scale = min(ratios)
        x1, y1 = self.COORDINATES[node]
        x2, y2 = self.COORDINATES[goal]
        return scale * math.hypot(x2 - x1, y2 - y1)

    def edge_cost(self, first: str, second: str) -> int:
        for edge in self.adjacency[first]:
            if edge.destination == second:
                return edge.cost
        raise ValueError(f"No edge exists between {first} and {second}")


class SearchEngine:
    """Pure search logic. No GUI or plotting code belongs in this class."""

    def __init__(self, graph: RomaniaGraph) -> None:
        self.graph = graph

    def _reconstruct(self, parents: Dict[str, Optional[str]], goal: str) -> List[str]:
        if goal not in parents:
            return []
        path: List[str] = []
        current: Optional[str] = goal
        while current is not None:
            path.append(current)
            current = parents[current]
        return list(reversed(path))

    def _cost(self, path: List[str]) -> Optional[int]:
        if not path:
            return None
        return sum(self.graph.edge_cost(a, b) for a, b in zip(path, path[1:]))

    def _result(
        self,
        algorithm: str,
        start: str,
        goal: str,
        expanded: List[str],
        discovery_edges: List[Tuple[str, str]],
        parents: Dict[str, Optional[str]],
        started: float,
    ) -> SearchResult:
        path = self._reconstruct(parents, goal)
        return SearchResult(
            algorithm=algorithm,
            start=start,
            goal=goal,
            expanded_order=expanded,
            discovery_edges=discovery_edges,
            path=path,
            path_cost=self._cost(path),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            found=bool(path),
        )

    def dfs(self, start: str, goal: str) -> SearchResult:
        """Depth-first graph search using an explicit LIFO stack.

        Nodes are marked when discovered (pushed), so cycles cannot create
        duplicate work. A regular Python list is used as a LIFO stack.
        Neighbours are pushed in reverse map/insertion order so that the
        first neighbour listed by the map is expanded first.
        """
        started = time.perf_counter()
        stack = [start]
        discovered = {start}
        parents: Dict[str, Optional[str]] = {start: None}
        expanded: List[str] = []
        discovery_edges: List[Tuple[str, str]] = []

        while stack:
            current = stack.pop()
            expanded.append(current)

            if current == goal:
                break

            # Stack is LIFO. Reverse the map-preserved adjacency order so
            # the first listed neighbour is expanded first.
            for edge in reversed(self.graph.adjacency[current]):
                neighbor = edge.destination
                if neighbor in discovered:
                    continue
                discovered.add(neighbor)
                parents[neighbor] = current
                discovery_edges.append((current, neighbor))
                stack.append(neighbor)

        return self._result("DFS", start, goal, expanded, discovery_edges, parents, started)

    def bfs(self, start: str, goal: str) -> SearchResult:
        """Breadth-first graph search using a FIFO queue."""
        started = time.perf_counter()
        queue = deque([start])
        discovered = {start}
        parents: Dict[str, Optional[str]] = {start: None}
        expanded: List[str] = []
        discovery_edges: List[Tuple[str, str]] = []

        while queue:
            current = queue.popleft()
            expanded.append(current)
            if current == goal:
                break

            for edge in self.graph.adjacency[current]:
                neighbor = edge.destination
                if neighbor not in discovered:
                    discovered.add(neighbor)
                    parents[neighbor] = current
                    discovery_edges.append((current, neighbor))
                    queue.append(neighbor)

        return self._result("BFS", start, goal, expanded, discovery_edges, parents, started)

    def ucs(self, start: str, goal: str) -> SearchResult:
        """Uniform-cost search ordered by accumulated path cost g(n)."""
        started = time.perf_counter()
        counter = 0
        frontier = [(0, counter, start)]
        best_cost = {start: 0}
        parents: Dict[str, Optional[str]] = {start: None}
        expanded: List[str] = []
        discovery_edges: List[Tuple[str, str]] = []
        closed = set()

        while frontier:
            cost_so_far, _, current = heapq.heappop(frontier)
            if current in closed:
                continue
            closed.add(current)
            expanded.append(current)
            if current == goal:
                break

            for edge in self.graph.adjacency[current]:
                neighbor = edge.destination
                new_cost = cost_so_far + edge.cost
                if new_cost < best_cost.get(neighbor, math.inf):
                    best_cost[neighbor] = new_cost
                    parents[neighbor] = current
                    discovery_edges.append((current, neighbor))
                    counter += 1
                    heapq.heappush(frontier, (new_cost, counter, neighbor))

        return self._result("UCS", start, goal, expanded, discovery_edges, parents, started)

    def a_star(self, start: str, goal: str) -> SearchResult:
        """A* search ordered by f(n) = g(n) + h(n)."""
        started = time.perf_counter()
        counter = 0
        frontier = [(self.graph.heuristic(start, goal), counter, start)]
        best_cost = {start: 0}
        parents: Dict[str, Optional[str]] = {start: None}
        expanded: List[str] = []
        discovery_edges: List[Tuple[str, str]] = []
        closed = set()

        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current in closed:
                continue
            closed.add(current)
            expanded.append(current)
            if current == goal:
                break

            for edge in self.graph.adjacency[current]:
                neighbor = edge.destination
                new_cost = best_cost[current] + edge.cost
                if new_cost < best_cost.get(neighbor, math.inf):
                    best_cost[neighbor] = new_cost
                    parents[neighbor] = current
                    discovery_edges.append((current, neighbor))
                    counter += 1
                    f_score = new_cost + self.graph.heuristic(neighbor, goal)
                    heapq.heappush(frontier, (f_score, counter, neighbor))

        return self._result("A*", start, goal, expanded, discovery_edges, parents, started)

    def befs(self, start: str, goal: str) -> SearchResult:
        """Greedy best-first search ordered only by h(n)."""
        started = time.perf_counter()
        counter = 0
        frontier = [(self.graph.heuristic(start, goal), counter, start)]
        discovered = {start}
        parents: Dict[str, Optional[str]] = {start: None}
        expanded: List[str] = []
        discovery_edges: List[Tuple[str, str]] = []

        while frontier:
            _, _, current = heapq.heappop(frontier)
            expanded.append(current)
            if current == goal:
                break

            for edge in self.graph.adjacency[current]:
                neighbor = edge.destination
                if neighbor not in discovered:
                    discovered.add(neighbor)
                    parents[neighbor] = current
                    discovery_edges.append((current, neighbor))
                    counter += 1
                    heapq.heappush(
                        frontier,
                        (self.graph.heuristic(neighbor, goal), counter, neighbor),
                    )

        return self._result("BEFS", start, goal, expanded, discovery_edges, parents, started)

    def run(self, algorithm: str, start: str, goal: str) -> SearchResult:
        methods = {
            "DFS": self.dfs,
            "BFS": self.bfs,
            "UCS": self.ucs,
            "A*": self.a_star,
            "BEFS": self.befs,
        }
        if algorithm not in methods:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        return methods[algorithm](start, goal)


class SearchVisualizer(tk.Tk):
    ALGORITHMS = ["DFS", "BFS", "UCS", "A*", "BEFS"]
    COLORS = {
        "DFS": "#e74c3c",
        "BFS": "#3498db",
        "UCS": "#9b59b6",
        "A*": "#16a085",
        "BEFS": "#f39c12",
        "path": "#f1c40f",
        "start": "#2ecc71",
        "goal": "#e91e63",
        "edge": "#a0a0a0",
        "node": "#f5f5f5",
        "text": "#202020",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("Romania Map Search Visualizer")
        self.geometry("1540x980")
        self.minsize(1150, 760)
        self.graph = RomaniaGraph()
        self.engine = SearchEngine(self.graph)
        self.results: List[SearchResult] = []
        self.current_result: Optional[SearchResult] = None
        self.animation_job = None
        self.animation_index = 0
        self.show_path = False

        self.algorithm_var = tk.StringVar(value="UCS")
        self.start_var = tk.StringVar(value="Arad")
        self.goal_var = tk.StringVar(value="Bucharest")
        self.delay_var = tk.IntVar(value=120)
        self.status_var = tk.StringVar(value="Select start, goal, and algorithm.")
        self.nodes_var = tk.StringVar(value="Nodes expanded: —")
        self.time_var = tk.StringVar(value="Time: —")
        self.cost_var = tk.StringVar(value="Path cost: —")
        self.path_var = tk.StringVar(value="Path: —")

        self._build_layout()
        self._draw_map()

    def _build_layout(self) -> None:
        controls = ttk.Frame(self, padding=8)
        controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(controls, text="Algorithm:").grid(row=0, column=0, padx=4)
        ttk.Combobox(controls, textvariable=self.algorithm_var, values=self.ALGORITHMS,
                     state="readonly", width=8).grid(row=0, column=1, padx=4)
        ttk.Label(controls, text="Start:").grid(row=0, column=2, padx=4)
        ttk.Combobox(controls, textvariable=self.start_var,
                     values=sorted(self.graph.COORDINATES), state="readonly", width=18).grid(row=0, column=3, padx=4)
        ttk.Label(controls, text="Goal:").grid(row=0, column=4, padx=4)
        ttk.Combobox(controls, textvariable=self.goal_var,
                     values=sorted(self.graph.COORDINATES), state="readonly", width=18).grid(row=0, column=5, padx=4)
        ttk.Label(controls, text="Delay (ms):").grid(row=0, column=6, padx=(16, 4))
        ttk.Scale(controls, from_=20, to=500, variable=self.delay_var,
                  orient=tk.HORIZONTAL, length=140).grid(row=0, column=7, padx=4)
        ttk.Button(controls, text="Run Search", command=self.run_search).grid(row=0, column=8, padx=5)
        ttk.Button(controls, text="Run All", command=self.run_all).grid(row=0, column=9, padx=5)
        ttk.Button(controls, text="Reset View", command=self.reset_view).grid(row=0, column=10, padx=5)
        ttk.Button(controls, text="Clear Table", command=self.clear_table).grid(row=0, column=11, padx=5)

        ttk.Label(self, textvariable=self.status_var).pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0, 4))

        body = ttk.Frame(self, padding=(8, 0, 8, 8))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(12, 7), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.04)
        self.plot_canvas = FigureCanvasTkAgg(self.figure, master=body)
        self.plot_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        side = ttk.Frame(body, width=255, padding=(12, 0, 0, 0))
        side.pack(side=tk.RIGHT, fill=tk.Y)
        side.pack_propagate(False)
        ttk.Label(side, text="Legend", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        for name in self.ALGORITHMS:
            line = tk.Canvas(side, width=24, height=18, highlightthickness=0)
            line.create_rectangle(2, 2, 22, 16, fill=self.COLORS[name], outline="")
            row = ttk.Frame(side)
            row.pack(fill=tk.X, pady=2)
            line.pack(in_=row, side=tk.LEFT, padx=(0, 7))
            ttk.Label(row, text=name).pack(side=tk.LEFT)
        ttk.Label(
            side,
            text=(
                "Yellow = final path\n"
                "Green = start\n"
                "Pink = goal\n"
                "Colored lines = discovery edges\n"
                "A*/BEFS: supplied HSL values for Bucharest"
            ),
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(12, 12))
        ttk.Separator(side).pack(fill=tk.X, pady=5)
        ttk.Label(side, text="Current Metrics", font=("Arial", 12, "bold")).pack(anchor="w", pady=(8, 6))
        for variable in (self.nodes_var, self.time_var, self.cost_var):
            ttk.Label(side, textvariable=variable, wraplength=235).pack(anchor="w", pady=3)
        ttk.Label(side, text="Search Path", font=("Arial", 12, "bold")).pack(anchor="w", pady=(14, 5))
        ttk.Label(side, textvariable=self.path_var, wraplength=235, justify=tk.LEFT).pack(anchor="w")

        table_frame = ttk.LabelFrame(self, text="Algorithm Comparison Log", padding=5)
        table_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
        columns = ("algorithm", "start", "goal", "found", "expanded", "time", "cost", "path")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        headings = {
            "algorithm": "Algorithm", "start": "Start", "goal": "Goal", "found": "Found",
            "expanded": "Nodes Expanded", "time": "Time (ms)", "cost": "Path Cost", "path": "Path"
        }
        widths = {"algorithm": 80, "start": 95, "goal": 95, "found": 65,
                  "expanded": 110, "time": 90, "cost": 80, "path": 650}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor="center")
        self.table.column("path", anchor="w")
        self.table.pack(side=tk.TOP, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.table.xview)
        self.table.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(fill=tk.X)

    def _draw_map(self, result: Optional[SearchResult] = None, visible_count: Optional[int] = None) -> None:
        self.axis.clear()
        self.axis.set_aspect("equal")
        self.axis.axis("off")
        self.axis.set_xlim(-0.8, 15.8)
        self.axis.set_ylim(-2.9, 9.3)

        coords = self.graph.COORDINATES
        # Base roads and distance labels.
        for first, second, cost in self.graph.EDGES:
            x1, y1 = coords[first]
            x2, y2 = coords[second]
            self.axis.plot([x1, x2], [y1, y2], color=self.COLORS["edge"], linewidth=1.5, zorder=1)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self.axis.text(mx, my, str(cost), fontsize=8, ha="center", va="center",
                           bbox=dict(facecolor="white", edgecolor="none", pad=1.3), zorder=2)

        if result is not None:
            edges_to_draw = result.discovery_edges
            if visible_count is not None:
                edges_to_draw = edges_to_draw[:visible_count]
            for first, second in edges_to_draw:
                x1, y1 = coords[first]
                x2, y2 = coords[second]
                self.axis.plot([x1, x2], [y1, y2], color=self.COLORS[result.algorithm],
                               linewidth=3.2, alpha=0.85, zorder=3)

            if self.show_path and result.path:
                for first, second in zip(result.path, result.path[1:]):
                    x1, y1 = coords[first]
                    x2, y2 = coords[second]
                    self.axis.plot([x1, x2], [y1, y2], color=self.COLORS["path"],
                                   linewidth=5.5, solid_capstyle="round", zorder=5)

        for city, (x, y) in coords.items():
            face = self.COLORS["node"]
            edge = "black"
            if result and city == result.start:
                face = self.COLORS["start"]
            elif result and city == result.goal:
                face = self.COLORS["goal"]
            self.axis.scatter([x], [y], s=145, marker="s", facecolor=face,
                              edgecolor=edge, linewidth=1.5, zorder=6)
            self.axis.text(x + 0.13, y + 0.08, city, fontsize=8.5, weight="bold", zorder=7)

        handles = [Line2D([0], [0], color=self.COLORS[name], lw=4, label=name) for name in self.ALGORITHMS]
        if result is not None:
            handles.append(Line2D([0], [0], color=self.COLORS["path"], lw=5, label="Final path"))
        self.axis.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)
        self.plot_canvas.draw_idle()

    def run_search(self) -> None:
        self._cancel_animation()
        start, goal, algorithm = self.start_var.get(), self.goal_var.get(), self.algorithm_var.get()
        if start == goal:
            messagebox.showwarning("Invalid selection", "Start and goal must be different.")
            return

        result = self.engine.run(algorithm, start, goal)
        self.results.append(result)
        self.current_result = result
        self.show_path = False
        self.animation_index = 0
        self._update_metrics(result)
        self._log_result(result)
        self._draw_map(result, 0)
        self.status_var.set(f"Running {algorithm}: exploration trace...")
        self._animate()

    def run_all(self) -> None:
        self._cancel_animation()
        start, goal = self.start_var.get(), self.goal_var.get()
        if start == goal:
            messagebox.showwarning("Invalid selection", "Start and goal must be different.")
            return
        for algorithm in self.ALGORITHMS:
            result = self.engine.run(algorithm, start, goal)
            self.results.append(result)
            self._log_result(result)
        selected = self.results[-1]
        self.current_result = selected
        self._update_metrics(selected)
        self.show_path = True
        self._draw_map(selected, len(selected.discovery_edges))
        self.status_var.set(f"Logged all algorithms for {start} → {goal}. Displaying {selected.algorithm}.")

    def _animate(self) -> None:
        result = self.current_result
        if result is None:
            return
        if self.animation_index < len(result.discovery_edges):
            self.animation_index += 1
            self._draw_map(result, self.animation_index)
            self.status_var.set(
                f"{result.algorithm}: showing discovery edge "
                f"{self.animation_index}/{len(result.discovery_edges)}"
            )
            self.animation_job = self.after(max(20, int(self.delay_var.get())), self._animate)
            return

        self.show_path = True
        self._draw_map(result, len(result.discovery_edges))
        self.status_var.set(
            f"Finished {result.algorithm}: " + ("path found." if result.found else "no path found.")
        )
        self.animation_job = None

    def _update_metrics(self, result: SearchResult) -> None:
        self.nodes_var.set(f"Nodes expanded: {len(result.expanded_order)}")
        self.time_var.set(f"Time: {result.elapsed_ms:.4f} ms")
        self.cost_var.set(f"Path cost: {result.path_cost if result.path_cost is not None else '—'}")
        self.path_var.set("Path: " + (" → ".join(result.path) if result.path else "Not found"))

    def _log_result(self, result: SearchResult) -> None:
        self.table.insert("", "end", values=(
            result.algorithm, result.start, result.goal,
            "Yes" if result.found else "No", len(result.expanded_order),
            f"{result.elapsed_ms:.4f}",
            result.path_cost if result.path_cost is not None else "—",
            " → ".join(result.path) if result.path else "Not found",
        ))

    def _cancel_animation(self) -> None:
        if self.animation_job is not None:
            self.after_cancel(self.animation_job)
            self.animation_job = None

    def reset_view(self) -> None:
        self._cancel_animation()
        self.current_result = None
        self.show_path = False
        self.animation_index = 0
        self.nodes_var.set("Nodes expanded: —")
        self.time_var.set("Time: —")
        self.cost_var.set("Path cost: —")
        self.path_var.set("Path: —")
        self.status_var.set("Select start, goal, and algorithm.")
        self._draw_map()

    def clear_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        self.results.clear()


if __name__ == "__main__":
    app = SearchVisualizer()
    app.mainloop()
