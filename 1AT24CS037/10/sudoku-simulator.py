# ============================================================
# SUDOKU SOLVER USING CSP
# Backtracking + MRV + Forward Checking
# ============================================================

import tkinter as tk
from tkinter import messagebox


# ============================================================
# CONSTANTS
# ============================================================

SIZE = 9
BOX_SIZE = 3

DIGITS = set(range(1, 10))


# ============================================================
# SUDOKU SOLVER
# ============================================================

class SudokuSolver:

    def __init__(self, grid):
        """
        grid:
            9x9 list of lists.
            0 represents an empty cell.
        """

        self.grid = [row[:] for row in grid]

        self.nodes_visited = 0
        self.backtracks = 0

    # --------------------------------------------------------
    # CHECK WHETHER A NUMBER CAN BE PLACED
    # --------------------------------------------------------

    def is_valid(self, row, col, number):

        # Check row
        for c in range(SIZE):
            if c != col and self.grid[row][c] == number:
                return False

        # Check column
        for r in range(SIZE):
            if r != row and self.grid[r][col] == number:
                return False

        # Check 3x3 box
        box_row = (row // BOX_SIZE) * BOX_SIZE
        box_col = (col // BOX_SIZE) * BOX_SIZE

        for r in range(box_row, box_row + BOX_SIZE):
            for c in range(box_col, box_col + BOX_SIZE):

                if (r != row or c != col) and \
                   self.grid[r][c] == number:
                    return False

        return True

    # --------------------------------------------------------
    # GET DOMAIN / CANDIDATES
    # --------------------------------------------------------

    def get_candidates(self, row, col):

        # Already filled
        if self.grid[row][col] != 0:
            return set()

        used = set()

        # Row
        for c in range(SIZE):
            if self.grid[row][c] != 0:
                used.add(self.grid[row][c])

        # Column
        for r in range(SIZE):
            if self.grid[r][col] != 0:
                used.add(self.grid[r][col])

        # 3x3 box
        box_row = (row // BOX_SIZE) * BOX_SIZE
        box_col = (col // BOX_SIZE) * BOX_SIZE

        for r in range(box_row, box_row + BOX_SIZE):
            for c in range(box_col, box_col + BOX_SIZE):
                if self.grid[r][c] != 0:
                    used.add(self.grid[r][c])

        return DIGITS - used

    # --------------------------------------------------------
    # FIND EMPTY CELL USING MRV
    # --------------------------------------------------------

    def find_mrv_cell(self):

        best_cell = None
        best_candidates = None

        for row in range(SIZE):
            for col in range(SIZE):

                if self.grid[row][col] == 0:

                    candidates = self.get_candidates(
                        row,
                        col
                    )

                    # ------------------------------------------------
                    # Forward checking:
                    # if any empty cell has no candidates,
                    # the current branch is impossible.
                    # ------------------------------------------------

                    if len(candidates) == 0:
                        return None, set()

                    # ------------------------------------------------
                    # MRV:
                    # choose the cell with the smallest domain.
                    # ------------------------------------------------

                    if (
                        best_candidates is None
                        or len(candidates) < len(best_candidates)
                    ):
                        best_cell = (row, col)
                        best_candidates = candidates

                        # Perfect MRV value
                        if len(best_candidates) == 1:
                            return best_cell, best_candidates

        return best_cell, best_candidates

    # --------------------------------------------------------
    # FORWARD CHECKING
    # --------------------------------------------------------

    def forward_check(self):

        for row in range(SIZE):
            for col in range(SIZE):

                if self.grid[row][col] == 0:

                    candidates = self.get_candidates(
                        row,
                        col
                    )

                    # No possible number
                    if len(candidates) == 0:
                        return False

        return True

    # --------------------------------------------------------
    # CHECK WHETHER SOLVED
    # --------------------------------------------------------

    def is_complete(self):

        for row in range(SIZE):
            for col in range(SIZE):

                if self.grid[row][col] == 0:
                    return False

        return True

    # --------------------------------------------------------
    # BACKTRACKING SEARCH
    # --------------------------------------------------------

    def solve(self):

        # ----------------------------------------------------
        # BASE CASE
        # ----------------------------------------------------

        if self.is_complete():
            return True

        # ----------------------------------------------------
        # MRV SELECTION
        # ----------------------------------------------------

        cell, candidates = self.find_mrv_cell()

        # No valid cell / contradiction
        if cell is None:
            self.backtracks += 1
            return False

        row, col = cell

        # ----------------------------------------------------
        # TRY EACH CANDIDATE
        # ----------------------------------------------------

        # Sorting gives deterministic output.
        for number in sorted(candidates):

            self.nodes_visited += 1

            # Extra safety check
            if not self.is_valid(row, col, number):
                continue

            # ------------------------------------------------
            # ASSIGN
            # ------------------------------------------------

            self.grid[row][col] = number

            # ------------------------------------------------
            # FORWARD CHECKING
            # ------------------------------------------------

            if self.forward_check():

                # --------------------------------------------
                # RECURSIVE SEARCH
                # --------------------------------------------

                if self.solve():
                    return True

            # ------------------------------------------------
            # BACKTRACK
            # ------------------------------------------------

            self.grid[row][col] = 0

            self.backtracks += 1

        return False

    # --------------------------------------------------------
    # VERIFY FINAL SOLUTION
    # --------------------------------------------------------

    def verify_solution(self):

        # Check every row
        for row in range(SIZE):

            values = self.grid[row]

            if set(values) != DIGITS:
                return False

        # Check every column
        for col in range(SIZE):

            values = {
                self.grid[row][col]
                for row in range(SIZE)
            }

            if values != DIGITS:
                return False

        # Check every 3x3 box
        for box_row in range(0, SIZE, BOX_SIZE):
            for box_col in range(0, SIZE, BOX_SIZE):

                values = set()

                for r in range(
                    box_row,
                    box_row + BOX_SIZE
                ):
                    for c in range(
                        box_col,
                        box_col + BOX_SIZE
                    ):
                        values.add(self.grid[r][c])

                if values != DIGITS:
                    return False

        return True


# ============================================================
# GUI
# ============================================================

class SudokuGUI:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Sudoku Solver - CSP + MRV + Backtracking"
        )

        self.root.geometry("650x780")

        self.entries = []

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = tk.Label(
            root,
            text="SUDOKU CSP SOLVER",
            font=("Arial", 22, "bold")
        )

        title.pack(pady=15)

        subtitle = tk.Label(
            root,
            text="Backtracking + MRV + Forward Checking",
            font=("Arial", 11)
        )

        subtitle.pack(pady=(0, 15))

        # ----------------------------------------------------
        # GRID FRAME
        # ----------------------------------------------------

        grid_frame = tk.Frame(root)

        grid_frame.pack()

        # ----------------------------------------------------
        # CREATE 9x9 GRID
        # ----------------------------------------------------

        for row in range(SIZE):

            row_entries = []

            for col in range(SIZE):

                entry = tk.Entry(
                    grid_frame,
                    width=2,
                    font=("Arial", 22, "bold"),
                    justify="center"
                )

                # Thick boundaries around 3x3 boxes
                padx_left = 3 if col % 3 == 0 else 1
                padx_right = 3 if col == 8 else 1
                pady_top = 3 if row % 3 == 0 else 1
                pady_bottom = 3 if row == 8 else 1

                entry.grid(
                    row=row,
                    column=col,
                    padx=(padx_left, padx_right),
                    pady=(pady_top, pady_bottom),
                    ipadx=5,
                    ipady=5
                )

                # Limit input to 1 digit
                entry.bind(
                    "<KeyRelease>",
                    self.validate_input
                )

                row_entries.append(entry)

            self.entries.append(row_entries)

        # ----------------------------------------------------
        # BUTTON FRAME
        # ----------------------------------------------------

        button_frame = tk.Frame(root)

        button_frame.pack(pady=20)

        solve_button = tk.Button(
            button_frame,
            text="SOLVE",
            width=14,
            font=("Arial", 11, "bold"),
            command=self.solve_sudoku
        )

        solve_button.grid(
            row=0,
            column=0,
            padx=8
        )

        clear_button = tk.Button(
            button_frame,
            text="CLEAR",
            width=14,
            font=("Arial", 11, "bold"),
            command=self.clear_grid
        )

        clear_button.grid(
            row=0,
            column=1,
            padx=8
        )

        example_button = tk.Button(
            button_frame,
            text="LOAD EXAMPLE",
            width=14,
            font=("Arial", 11, "bold"),
            command=self.load_example
        )

        example_button.grid(
            row=0,
            column=2,
            padx=8
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status = tk.Label(
            root,
            text="Enter a Sudoku puzzle or load the example.",
            font=("Arial", 11),
            justify="center"
        )

        self.status.pack(pady=10)

        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        self.stats = tk.Label(
            root,
            text="",
            font=("Courier New", 10),
            justify="left"
        )

        self.stats.pack(pady=10)

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    def validate_input(self, event=None):

        widget = event.widget

        value = widget.get()

        # Allow only 1-9
        if value not in "":
            if value not in "123456789":
                widget.delete(0, tk.END)

            elif len(value) > 1:
                widget.delete(0, tk.END)
                widget.insert(0, value[-1])

    # ========================================================
    # READ GRID
    # ========================================================

    def read_grid(self):

        grid = []

        for row in range(SIZE):

            row_values = []

            for col in range(SIZE):

                value = self.entries[row][col].get().strip()

                if value == "":
                    row_values.append(0)

                elif value in "123456789":
                    row_values.append(int(value))

                else:
                    raise ValueError(
                        "Only numbers 1-9 are allowed."
                    )

            grid.append(row_values)

        return grid

    # ========================================================
    # VALIDATE INITIAL PUZZLE
    # ========================================================

    def validate_initial_grid(self, grid):

        # Create temporary solver
        solver = SudokuSolver(grid)

        # Check every given number
        for row in range(SIZE):

            for col in range(SIZE):

                if grid[row][col] != 0:

                    number = grid[row][col]

                    # Temporarily remove number
                    solver.grid[row][col] = 0

                    if not solver.is_valid(
                        row,
                        col,
                        number
                    ):

                        solver.grid[row][col] = number

                        return False

                    solver.grid[row][col] = number

        return True

    # ========================================================
    # SOLVE
    # ========================================================

    def solve_sudoku(self):

        try:

            original_grid = self.read_grid()

        except ValueError as error:

            messagebox.showerror(
                "Invalid Input",
                str(error)
            )

            return

        # Validate puzzle
        if not self.validate_initial_grid(
            original_grid
        ):

            messagebox.showerror(
                "Invalid Sudoku",
                "The puzzle contains a duplicate "
                "number in a row, column, or 3x3 box."
            )

            return

        # Create solver
        solver = SudokuSolver(original_grid)

        self.status.config(
            text="Solving using CSP + MRV + Backtracking..."
        )

        self.root.update()

        # Solve
        solved = solver.solve()

        if not solved:

            self.status.config(
                text="No solution exists for this Sudoku."
            )

            self.stats.config(
                text=(
                    f"Nodes visited : {solver.nodes_visited}\n"
                    f"Backtracks    : {solver.backtracks}"
                )
            )

            messagebox.showwarning(
                "No Solution",
                "This Sudoku has no valid solution."
            )

            return

        # Verify
        if not solver.verify_solution():

            messagebox.showerror(
                "Solver Error",
                "A solution was generated but failed "
                "verification."
            )

            return

        # Display solution
        self.display_grid(
            solver.grid
        )

        self.status.config(
            text="Sudoku solved successfully."
        )

        self.stats.config(
            text=(
                f"Nodes visited : {solver.nodes_visited}\n"
                f"Backtracks    : {solver.backtracks}\n"
                f"Technique     : MRV + Forward Checking"
            )
        )

    # ========================================================
    # DISPLAY GRID
    # ========================================================

    def display_grid(self, grid):

        for row in range(SIZE):

            for col in range(SIZE):

                entry = self.entries[row][col]

                # Do not overwrite original givens styling
                if entry.get() == "":

                    entry.insert(
                        0,
                        str(grid[row][col])
                    )

                else:

                    entry.delete(
                        0,
                        tk.END
                    )

                    entry.insert(
                        0,
                        str(grid[row][col])
                    )

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_grid(self):

        for row in range(SIZE):

            for col in range(SIZE):

                self.entries[row][col].delete(
                    0,
                    tk.END
                )

        self.status.config(
            text="Grid cleared."
        )

        self.stats.config(
            text=""
        )

    # ========================================================
    # LOAD EXAMPLE
    # ========================================================

    def load_example(self):

        example = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],

            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],

            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]

        self.clear_grid()

        for row in range(SIZE):

            for col in range(SIZE):

                value = example[row][col]

                if value != 0:

                    self.entries[row][col].insert(
                        0,
                        str(value)
                    )

        self.status.config(
            text="Example Sudoku loaded."
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = SudokuGUI(root)

    root.mainloop()