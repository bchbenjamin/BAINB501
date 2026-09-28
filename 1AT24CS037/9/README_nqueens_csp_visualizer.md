# N-Queens CSP Visualizer

A Tkinter visualization of N-Queens solved as a Constraint Satisfaction Problem
using recursive backtracking and forward checking.

## Requirements

- Python 3.9+
- Tkinter

On Fedora, if Tkinter is missing:

```bash
sudo dnf install python3-tkinter
```

## Run

```bash
python3 nqueens_csp_visualizer.py
```

## Controls

- **N**: board size, from 4 to 12
- **Next Step**: advance exactly one search operation
- **Auto Run**: animate the CSP search
- **Speed**: change animation delay
- **Reset**: regenerate the search trace

## CSP model

- Variables: columns Q0 ... Q(n-1)
- Domain: possible row numbers
- Constraints:
  - no shared row
  - no shared diagonal
- Forward checking removes attacked rows from every future variable's domain.
