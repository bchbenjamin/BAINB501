from collections import deque
import time
import tracemalloc

class State:
    def __init__(
        self,
        initial_state: tuple[int, ...],
        parent: "State | None" = None
    ):
        self.initial_state = initial_state
        self.parent = parent
        if parent is None: self.parent = self
        self.children = []

    def __str__(self):
        output = "_"*5 + '\n'
        output += "\n".join(
            " ".join(map(str, row))
            for row in [
                self.initial_state[i:i + 3]
                for i in range(0, 9, 3)
            ]
        )
        output += '\n'+"_"*5 + '\n'
        return output

    def load_children(self, visited: set[tuple[int, ...]]):
        # Find the position of 0
        zero_index = self.initial_state.index(0)
        row = zero_index // 3
        col = zero_index % 3

        for dr, dc in [(-1, 0),(1, 0),(0, -1),(0, 1)]: # This loops 4 times
            new_row = row + dr
            new_col = col + dc

            # Check whether the move is legal
            if 0 <= new_row < 3 and 0 <= new_col < 3:

                new_zero_index = new_row * 3 + new_col

                # Swap 0 with the adjacent tile
                new_state = list(self.initial_state)
                new_state[zero_index], new_state[new_zero_index] = new_state[new_zero_index], new_state[zero_index]
                new_state = tuple(new_state)

                # O(1) average-time lookup
                if new_state not in visited:
                    visited.add(new_state)

                    child = State(
                        initial_state=new_state,
                        parent=self
                    )

                    self.children.append(child)


def bfs(initial_state: tuple[int, ...], goal_state: tuple[int, ...]):
    visited = {initial_state}

    root = State(initial_state)
    queue = deque([root])

    while queue:
        current = queue.popleft()
        if current.initial_state == goal_state:
            output = current
            while current.parent != current:
                print(current)
                current = current.parent
            return output
        current.load_children(visited)
        queue.extend(current.children)

    return None

def dfs(initial_state: tuple[int, ...], goal_state: tuple[int, ...]):
    visited = {initial_state}

    root = State(initial_state)
    queue = deque([root])

    while queue:
        current = queue.pop()
        if current.initial_state == goal_state:
            output = current
            while current.parent != current:
                print(current)
                current = current.parent
            return output
        current.load_children(visited)
        queue.extend(reversed(current.children))

    return None

starting = (7,2,4, 5,0,6, 8,3,1)
# starting = (1,2,3, 4,5,6, 0,7,8)
goal = (1,2,3, 4,5,6, 7,8,0)

# _______ BFS _________
start = time.perf_counter()
tracemalloc.start()
bfs(starting, goal)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
end = time.perf_counter()
bfs_stats = "BFS\n"
bfs_stats += "Time: " + str(end - start) + " seconds " + '\n'
bfs_stats += "Current memory: " + str(current / 1024) + " KB" + '\n'
bfs_stats += "Peak memory: " +str(peak / 1024)+ " KB" + '\n'

# _______ DFS _________
start = time.perf_counter()
tracemalloc.start()
dfs(starting, goal)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
end = time.perf_counter()
dfs_stats = "DFS\n"
dfs_stats += "Time: " + str(end - start) + " seconds " + '\n'
dfs_stats += "Current memory: " + str(current / 1024) + " KB" + '\n'
dfs_stats += "Peak memory: " +str(peak / 1024)+ " KB" + '\n'

print(bfs_stats, dfs_stats, sep="\n")