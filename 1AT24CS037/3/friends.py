import pandas

df = pandas.read_csv('3/friends.csv')
print(df)

# Build adjacency list
data = {}

for i in range(len(df)):
    name = df.iloc[i]["Person"]
    friend = df.iloc[i]["Friend"]

    data.setdefault(name, []).append(friend)

del df


def mutuals_using_bfs(start: str) -> str:
    """Return all friends reachable from start using BFS."""
    if start not in data:
        return "Invalid input"

    visited = {start}
    queue = [start]
    mutuals = set()

    while queue:
        person = queue.pop(0)

        for friend in data.get(person, []):
            if friend not in visited:
                visited.add(friend)
                queue.append(friend)

                if friend != start:
                    mutuals.add(friend)

    return ','.join(sorted(mutuals))


def shortest_path_bfs(start: str, target: str) -> str:
    """Find the shortest path from start to target using BFS."""

    if start not in data:
        return "Invalid start"

    if target not in data:
        return "Invalid target"

    if start == target:
        return start

    visited = {start}
    queue = [start]

    # parent[child] = node we came from
    parent = {start: None}

    while queue:
        person = queue.pop(0)

        for friend in data.get(person, []):
            if friend in visited:
                continue

            visited.add(friend)
            parent[friend] = person

            # Target found
            if friend == target:
                path = []
                current = target

                while current is not None:
                    path.append(current)
                    current = parent[current]

                path.reverse()
                return ' -> '.join(path)

            queue.append(friend)

    return "No path"


print("Mutuals:", mutuals_using_bfs("Alice"))
print("Shortest path:", shortest_path_bfs("Alice", "Bob"))
