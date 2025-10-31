import heapq
import time
import itertools


class Search:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def bfs(self, state):
        start_time = time.time()
        queue = [state]
        visited = set()

        while queue:
            curr = queue.pop(0)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("bfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        queue.append(e)

    def dfs(self, state):
        start_time = time.time()
        stack = [state]
        visited = set()

        while stack:
            curr = stack.pop()
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("dfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        stack.append(e)

    def ids(self, state):
        start_time = time.time()
        limit = 50
        max_limit = 500

        while limit <= max_limit:
            stack = [state]
            visited = set()

            while stack:
                curr = stack.pop()
                visited.add(curr)
                if curr.reached_goal():
                    print("**************** Solution Found ! ******************")
                    print(len(curr.get_move()))
                    print("ids: {:.2f} ms".format((time.time() - start_time) * 1000))
                    return
                else:
                    for e in curr.get_neighbors():
                        if e not in visited and len(e.get_move()) <= limit:
                            stack.append(e)
            limit += 10

    def ucs(self, state):
        start_time = time.time()
        queue = []
        counter = itertools.count()  # dùng để tránh so sánh State trực tiếp
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("ucs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        heapq.heappush(queue, (len(e.get_move()), next(counter), e))

    def greedy(self, state, heuristic):
        start_time = time.time()
        queue = []
        counter = itertools.count()
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("greedy({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                break
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        if heuristic == "euclidean":
                            cost = e.euclidean()
                        elif heuristic == "manhatten":
                            cost = e.manhatten()
                        else:
                            cost = 0
                        heapq.heappush(queue, (cost, next(counter), e))

    def astar(self, state, heuristic):
        start_time = time.time()
        queue = []
        counter = itertools.count()
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("A* ({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                break
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        if heuristic == "euclidean":
                            cost = e.euclidean()
                        elif heuristic == "manhatten":
                            cost = e.manhatten()
                        else:
                            cost = 0
                        heapq.heappush(queue, (len(e.get_move()) + cost, next(counter), e))


        # ================= RETURN PATH VERSIONS ====================

    def bfs_return_path(self, state):
        start_time = time.time()
        queue = [state]
        visited = set()

        while queue:
            curr = queue.pop(0)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("bfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        queue.append(e)
        return []

    def dfs_return_path(self, state):
        start_time = time.time()
        stack = [state]
        visited = set()

        while stack:
            curr = stack.pop()
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("dfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        stack.append(e)
        return []

    def ids_return_path(self, state):
        start_time = time.time()
        limit = 50
        max_limit = 500

        while limit <= max_limit:
            stack = [state]
            visited = set()
            while stack:
                curr = stack.pop()
                visited.add(curr)
                if curr.reached_goal():
                    print("**************** Solution Found ! ******************")
                    print(len(curr.get_move()))
                    print("ids: {:.2f} ms".format((time.time() - start_time) * 1000))
                    return list(curr.get_move())
                else:
                    for e in curr.get_neighbors():
                        if e not in visited and len(e.get_move()) <= limit:
                            stack.append(e)
            limit += 10
        return []

    def ucs_return_path(self, state):
        start_time = time.time()
        queue = []
        counter = itertools.count()
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("ucs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        heapq.heappush(queue, (len(e.get_move()), next(counter), e))
        return []

    def greedy_return_path(self, state, heuristic):
        start_time = time.time()
        queue = []
        counter = itertools.count()
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("greedy({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                return list(curr.get_move())
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        if heuristic == "euclidean":
                            cost = e.euclidean()
                        elif heuristic == "manhatten":
                            cost = e.manhatten()
                        else:
                            cost = 0
                        heapq.heappush(queue, (cost, next(counter), e))
        return []

    def astar_return_path(self, state, heuristic):
        start_time = time.time()
        queue = []
        counter = itertools.count()
        heapq.heappush(queue, (0, next(counter), state))
        visited = set()

        while queue:
            curr_cost, _, curr = heapq.heappop(queue)
            visited.add(curr)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("A* ({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                return list(curr.get_move())
            else:
                for e in curr.get_neighbors():
                    if e not in visited:
                        if heuristic == "euclidean":
                            cost = e.euclidean()
                        elif heuristic == "manhatten":
                            cost = e.manhatten()
                        else:
                            cost = 0
                        heapq.heappush(queue, (len(e.get_move()) + cost, next(counter), e))
        return []

