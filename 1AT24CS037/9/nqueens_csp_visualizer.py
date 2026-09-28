import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set


@dataclass
class Snapshot:
    board: List[int]                 # board[col] = row, -1 if unassigned
    domains: List[List[int]]
    current_col: Optional[int]
    current_row: Optional[int]
    action: str
    detail: str
    nodes: int
    backtracks: int
    conflicts: int
    solutions: int


class NQueensCSPVisualizer:
    """
    N-Queens as a Constraint Satisfaction Problem (CSP).

    Variable:
        Each column is a variable.

    Domain:
        Each variable's domain is the set of currently legal rows.

    Constraints:
        Two queens may not share:
          1. the same row
          2. the same diagonal

    Search:
        Depth-first backtracking with forward checking.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("N-Queens CSP — Backtracking + Forward Checking")
        self.root.geometry("1250x820")
        self.root.minsize(1050, 720)

        self.n = 8
        self.delay = 120
        self.snapshots: List[Snapshot] = []
        self.step_index = 0
        self.running = False

        self._build_ui()
        self.reset()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="N =", font=("Arial", 11, "bold")).pack(side="left")
        self.n_var = tk.IntVar(value=8)
        self.n_spin = tk.Spinbox(
            top, from_=4, to=12, width=4, textvariable=self.n_var,
            command=self.reset
        )
        self.n_spin.pack(side="left", padx=(5, 15))

        ttk.Label(top, text="Speed:").pack(side="left")
        self.speed_var = tk.IntVar(value=120)
        self.speed = ttk.Scale(
            top, from_=20, to=600, variable=self.speed_var,
            orient="horizontal", length=150
        )
        self.speed.pack(side="left", padx=5)

        self.start_btn = ttk.Button(top, text="▶ Auto Run", command=self.auto_run)
        self.start_btn.pack(side="left", padx=5)

        self.next_btn = ttk.Button(top, text="Next Step", command=self.next_step)
        self.next_btn.pack(side="left", padx=5)

        self.reset_btn = ttk.Button(top, text="↻ Reset", command=self.reset)
        self.reset_btn.pack(side="left", padx=5)

        ttk.Label(
            top,
            text="CSP: column = variable | row = domain | diagonals = constraints",
            foreground="#555"
        ).pack(side="right")

        main = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main.pack(fill="both", expand=True)

        # Left: board
        left = ttk.LabelFrame(main, text="Chess Board / Search State", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.canvas = tk.Canvas(left, background="#222222", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        # Right: CSP information
        right = ttk.Frame(main, width=430)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        stats = ttk.LabelFrame(right, text="Search Statistics", padding=10)
        stats.pack(fill="x")

        self.stats_text = tk.StringVar()
        ttk.Label(
            stats, textvariable=self.stats_text,
            justify="left", font=("Consolas", 10)
        ).pack(anchor="w")

        action = ttk.LabelFrame(right, text="Current CSP Operation", padding=10)
        action.pack(fill="x", pady=8)

        self.action_text = tk.StringVar()
        ttk.Label(
            action, textvariable=self.action_text,
            justify="left", wraplength=390,
            font=("Arial", 10)
        ).pack(anchor="w")

        domains = ttk.LabelFrame(right, text="Forward-Checking Domains", padding=8)
        domains.pack(fill="both", expand=True)

        self.domain_text = tk.Text(
            domains, width=48, height=22,
            font=("Consolas", 10), state="disabled",
            wrap="none"
        )
        self.domain_text.pack(fill="both", expand=True)

        legend = ttk.LabelFrame(right, text="Legend", padding=8)
        legend.pack(fill="x", pady=(8, 0))

        ttk.Label(
            legend,
            text=(
                "♕  Queen currently assigned\n"
                "●  Candidate row in current domain\n"
                "×  Row eliminated by forward checking\n"
                "■  Current variable / column"
            ),
            justify="left"
        ).pack(anchor="w")

        bottom = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")

        self.progress_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.progress_var).pack(side="left")

    # ------------------------------------------------------------------
    # CSP solver — creates a sequence of visual states
    # ------------------------------------------------------------------

    def reset(self):
        self.running = False
        try:
            n = int(self.n_var.get())
            if not 4 <= n <= 12:
                raise ValueError
        except ValueError:
            self.n_var.set(8)
            n = 8

        self.n = n
        self.snapshots = []
        self.step_index = 0

        initial_domains = [list(range(n)) for _ in range(n)]

        self._record(
            board=[-1] * n,
            domains=initial_domains,
            current_col=None,
            current_row=None,
            action="INITIAL CSP",
            detail=(
                f"Created {n} variables: Q0 ... Q{n-1}.\n"
                f"Each variable initially has domain {{0 ... {n-1}}}."
            ),
            nodes=0, backtracks=0, conflicts=0, solutions=0
        )

        self._generate_search_states()
        self.draw()

    def _generate_search_states(self):
        """Generate all visual states using recursive backtracking + FC."""

        board = [-1] * self.n
        domains = [list(range(self.n)) for _ in range(self.n)]

        counters = {
            "nodes": 0,
            "backtracks": 0,
            "conflicts": 0,
            "solutions": 0
        }

        def legal(col: int, row: int) -> bool:
            for c in range(col):
                r = board[c]
                if r == -1:
                    continue
                if r == row:
                    return False
                if abs(r - row) == abs(c - col):
                    return False
            return True

        def forward_check(col: int, row: int) -> Tuple[bool, List[List[int]]]:
            new_domains = [d[:] for d in domains]
            new_domains[col] = [row]

            for c in range(col + 1, self.n):
                filtered = []
                for r in new_domains[c]:
                    if r == row:
                        continue
                    if abs(r - row) == abs(c - col):
                        continue
                    filtered.append(r)

                new_domains[c] = filtered

                if not filtered:
                    return False, new_domains

            return True, new_domains

        def search(col: int) -> bool:
            if col == self.n:
                counters["solutions"] += 1
                self._record(
                    board=board[:],
                    domains=[d[:] for d in domains],
                    current_col=None,
                    current_row=None,
                    action="✓ SOLUTION FOUND",
                    detail="Every column has a queen and all CSP constraints are satisfied.",
                    **counters
                )
                return True

            # Try values in the current variable's domain.
            candidates = domains[col][:]

            self._record(
                board=board[:],
                domains=[d[:] for d in domains],
                current_col=col,
                current_row=None,
                action=f"SELECT VARIABLE Q{col}",
                detail=(
                    f"Assigning the next CSP variable Q{col}.\n"
                    f"Current domain: {candidates}"
                ),
                **counters
            )

            for row in candidates:
                counters["nodes"] += 1

                if not legal(col, row):
                    counters["conflicts"] += 1
                    self._record(
                        board=board[:],
                        domains=[d[:] for d in domains],
                        current_col=col,
                        current_row=row,
                        action=f"✗ CONFLICT: Q{col} = row {row}",
                        detail="The candidate violates an existing row or diagonal constraint.",
                        **counters
                    )
                    continue

                board[col] = row

                self._record(
                    board=board[:],
                    domains=[d[:] for d in domains],
                    current_col=col,
                    current_row=row,
                    action=f"PLACE Q{col} → row {row}",
                    detail=(
                        f"Candidate is consistent with assigned queens.\n"
                        f"Now apply forward checking to Q{col + 1} ... Q{self.n - 1}."
                    ),
                    **counters
                )

                ok, new_domains = forward_check(col, row)

                self._record(
                    board=board[:],
                    domains=new_domains,
                    current_col=col,
                    current_row=row,
                    action=(
                        "FORWARD CHECK ✓" if ok
                        else "FORWARD CHECK ✗ — EMPTY DOMAIN"
                    ),
                    detail=(
                        "Removed rows attacked by the new queen from future domains."
                        if ok else
                        "A future variable has an empty domain, so this branch cannot work."
                    ),
                    **counters
                )

                if ok:
                    old_domains = [d[:] for d in domains]
                    domains[:] = new_domains

                    if search(col + 1):
                        return True

                    domains[:] = old_domains

                board[col] = -1
                counters["backtracks"] += 1

                self._record(
                    board=board[:],
                    domains=[d[:] for d in domains],
                    current_col=col,
                    current_row=row,
                    action=f"↩ BACKTRACK from Q{col}",
                    detail=(
                        f"Remove Q{col} = row {row} and try the next candidate."
                    ),
                    **counters
                )

            board[col] = -1
            return False

        search(0)

        # Add a terminal state if no solution was recorded.
        if counters["solutions"] == 0:
            self._record(
                board=board[:],
                domains=[d[:] for d in domains],
                current_col=None,
                current_row=None,
                action="NO SOLUTION",
                detail=f"No solution exists for N={self.n}.",
                **counters
            )

    def _record(
        self,
        board,
        domains,
        current_col,
        current_row,
        action,
        detail,
        nodes,
        backtracks,
        conflicts,
        solutions
    ):
        self.snapshots.append(
            Snapshot(
                board=board[:],
                domains=[d[:] for d in domains],
                current_col=current_col,
                current_row=current_row,
                action=action,
                detail=detail,
                nodes=nodes,
                backtracks=backtracks,
                conflicts=conflicts,
                solutions=solutions
            )
        )

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def draw(self):
        self.canvas.delete("all")

        if not self.snapshots:
            return

        snap = self.snapshots[min(self.step_index, len(self.snapshots) - 1)]

        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 500)

        margin = 35
        board_size = min(w - 2 * margin, h - 2 * margin)
        cell = board_size / self.n

        x0 = (w - board_size) / 2
        y0 = (h - board_size) / 2

        # Board.
        for row in range(self.n):
            for col in range(self.n):
                x1 = x0 + col * cell
                y1 = y0 + row * cell
                x2 = x1 + cell
                y2 = y1 + cell

                light = (row + col) % 2 == 0
                fill = "#F0D9B5" if light else "#B58863"

                if snap.current_col == col:
                    fill = "#F6D365" if light else "#D99A2B"

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill, outline="#333333", width=1
                )

        # Coordinate labels.
        for col in range(self.n):
            x = x0 + col * cell + cell / 2
            self.canvas.create_text(
                x, y0 - 12,
                text=str(col),
                font=("Arial", 9, "bold")
            )

        for row in range(self.n):
            y = y0 + row * cell + cell / 2
            self.canvas.create_text(
                x0 - 14, y,
                text=str(row),
                font=("Arial", 9, "bold")
            )

        # Candidate dots from the current variable's domain.
        if snap.current_col is not None:
            col = snap.current_col
            domain = snap.domains[col] if col < len(snap.domains) else []

            for row in domain:
                cx = x0 + col * cell + cell / 2
                cy = y0 + row * cell + cell / 2
                radius = max(3, cell * 0.09)

                self.canvas.create_oval(
                    cx - radius, cy - radius,
                    cx + radius, cy + radius,
                    fill="#2E7D32",
                    outline=""
                )

        # Queens.
        for col, row in enumerate(snap.board):
            if row < 0:
                continue

            cx = x0 + col * cell + cell / 2
            cy = y0 + row * cell + cell / 2

            font_size = max(16, int(cell * 0.60))
            color = "#222222"

            self.canvas.create_text(
                cx, cy,
                text="♛",
                font=("DejaVu Sans", font_size),
                fill=color
            )

        # Highlight current candidate.
        if snap.current_col is not None and snap.current_row is not None:
            col = snap.current_col
            row = snap.current_row

            x1 = x0 + col * cell
            y1 = y0 + row * cell
            x2 = x1 + cell
            y2 = y1 + cell

            self.canvas.create_rectangle(
                x1 + 3, y1 + 3, x2 - 3, y2 - 3,
                outline="#C62828", width=max(2, int(cell * 0.05))
            )

        # Current variable marker.
        if snap.current_col is not None:
            x1 = x0 + snap.current_col * cell
            self.canvas.create_rectangle(
                x1 + 2, y0 + 2,
                x1 + cell - 2, y0 + board_size - 2,
                outline="#1565C0", width=3
            )

        # Update right panel.
        self.stats_text.set(
            f"Step:        {self.step_index + 1}/{len(self.snapshots)}\n"
            f"Assignments: {snap.nodes}\n"
            f"Backtracks:  {snap.backtracks}\n"
            f"Conflicts:   {snap.conflicts}\n"
            f"Solutions:   {snap.solutions}"
        )

        self.action_text.set(
            f"{snap.action}\n\n{snap.detail}"
        )

        self.domain_text.configure(state="normal")
        self.domain_text.delete("1.0", "end")

        for col, domain in enumerate(snap.domains):
            if snap.board[col] != -1:
                state = f"Q{col}: {{{snap.board[col]}}}  [ASSIGNED]"
            elif not domain:
                state = f"Q{col}: ∅  [FAILURE]"
            else:
                state = f"Q{col}: {{{', '.join(map(str, domain))}}}"

            self.domain_text.insert("end", state + "\n")

        self.domain_text.configure(state="disabled")

        self.progress_var.set(
            "Next Step = advance one CSP operation   |   "
            "Auto Run = animate the search"
        )

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def next_step(self):
        if self.step_index < len(self.snapshots) - 1:
            self.step_index += 1
            self.draw()
        else:
            self.running = False

    def auto_run(self):
        if self.running:
            self.running = False
            self.start_btn.configure(text="▶ Auto Run")
            return

        self.running = True
        self.start_btn.configure(text="⏸ Pause")
        self._animate()

    def _animate(self):
        if not self.running:
            return

        if self.step_index >= len(self.snapshots) - 1:
            self.running = False
            self.start_btn.configure(text="▶ Auto Run")
            self.draw()
            return

        self.step_index += 1
        self.draw()

        # Smaller slider value = faster animation.
        delay = max(15, int(self.speed_var.get()))
        self.root.after(delay, self._animate)


def main():
    root = tk.Tk()
    app = NQueensCSPVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
