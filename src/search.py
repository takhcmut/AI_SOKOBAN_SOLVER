# -*- coding: utf-8 -*-
"""
Search algorithms for Sokoban.

- Giữ nguyên thuật toán gốc (BFS/DFS/IDS/UCS/Greedy/A*) và các biến thể
  *_return_path(...) trả về chuỗi move.
- Thêm hỗ trợ HỦY trong nền: tham số tùy chọn `stop_cb` (callable -> bool).
  Khi `stop_cb()` trả về True, thuật toán lập tức kết thúc và trả về [].
- Tối ưu:
  • BFS dùng deque và đánh dấu visited NGAY khi enqueue.
  • UCS/A* dùng best_g (cost-so-far) để tránh đẩy trạng thái tệ hơn.
  • Vòng lặp kiểm tra hủy theo chu kỳ để giảm overhead (CHECK_EVERY).
- Tương thích UI hiện tại: A* nhận heuristic "manhatten" hoặc "euclidean".
"""
from __future__ import annotations

import heapq
import time
import itertools
from collections import deque
from typing import Callable, Iterable, List, Optional


StopFn = Optional[Callable[[], bool]]


class Search:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # kiểm tra hủy mỗi N node để tiết kiệm chi phí hàm gọi
        self.CHECK_EVERY = 2048

    # ---------------------- tiện ích nội bộ ----------------------
    def _should_stop(self, expanded: int, stop_cb: StopFn) -> bool:
        try:
            return bool(stop_cb and expanded % self.CHECK_EVERY == 0 and stop_cb())
        except Exception:
            # nếu callback lỗi, coi như không hủy
            return False

    # ====================== NON-RETURN (in-place print) ======================

    def bfs(self, state, stop_cb: StopFn = None):
        start_time = time.time()
        q = deque([state])
        visited = {state}
        expanded = 0

        while q:
            curr = q.popleft()
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("bfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    q.append(e)

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                break

    def dfs(self, state, stop_cb: StopFn = None):
        start_time = time.time()
        stack = [state]
        visited = {state}
        expanded = 0

        while stack:
            curr = stack.pop()
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("dfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    stack.append(e)

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                break

    def ids(self, state, stop_cb: StopFn = None, depth_step: int = 10, max_limit: int = 500):
        start_time = time.time()
        limit = 50

        while limit <= max_limit:
            stack = [state]
            visited = {state}
            expanded = 0

            while stack:
                curr = stack.pop()
                if curr.reached_goal():
                    print("**************** Solution Found ! ******************")
                    print(len(curr.get_move()))
                    print("ids: {:.2f} ms".format((time.time() - start_time) * 1000))
                    return

                for e in curr.get_neighbors():
                    if e not in visited and len(e.get_move()) <= limit:
                        visited.add(e)
                        stack.append(e)

                expanded += 1
                if self._should_stop(expanded, stop_cb):
                    return
            limit += depth_step

    def ucs(self, state, stop_cb: StopFn = None):
        start_time = time.time()
        pq = []
        counter = itertools.count()
        heapq.heappush(pq, (0, next(counter), state))
        best_g = {state: 0}
        expanded = 0

        while pq:
            g, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("ucs: {:.2f} ms".format((time.time() - start_time) * 1000))
                break

            for e in curr.get_neighbors():
                g2 = len(e.get_move())
                if e not in best_g or g2 < best_g[e]:
                    best_g[e] = g2
                    heapq.heappush(pq, (g2, next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                break

    def greedy(self, state, heuristic, stop_cb: StopFn = None):
        start_time = time.time()
        pq = []
        counter = itertools.count()

        def h(s):
            if heuristic == "euclidean":
                return s.euclidean()
            elif heuristic == "manhatten":
                return s.manhatten()
            return 0

        heapq.heappush(pq, (h(state), next(counter), state))
        visited = {state}
        expanded = 0

        while pq:
            _, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("greedy({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                break

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    heapq.heappush(pq, (h(e), next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                break

    def astar(self, state, heuristic, stop_cb: StopFn = None):
        start_time = time.time()
        pq = []
        counter = itertools.count()

        def h(s):
            if heuristic == "euclidean":
                return s.euclidean()
            elif heuristic == "manhatten":
                return s.manhatten()
            return 0

        heapq.heappush(pq, (0, next(counter), state))
        best_g = {state: 0}
        expanded = 0

        while pq:
            _, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("A* ({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                break

            g = len(curr.get_move())
            for e in curr.get_neighbors():
                g2 = g + 1
                if e not in best_g or g2 < best_g[e]:
                    best_g[e] = g2
                    f = g2 + h(e)
                    heapq.heappush(pq, (f, next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                break

    # ======================= RETURN PATH VERSIONS =======================

    def bfs_return_path(self, state, stop_cb: StopFn = None) -> List[str]:
        start_time = time.time()
        q = deque([state])
        visited = {state}
        expanded = 0

        while q:
            curr = q.popleft()
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("bfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    q.append(e)

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                return []
        return []

    def dfs_return_path(self, state, stop_cb: StopFn = None) -> List[str]:
        start_time = time.time()
        stack = [state]
        visited = {state}
        expanded = 0

        while stack:
            curr = stack.pop()
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("dfs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    stack.append(e)

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                return []
        return []

    def ids_return_path(
        self,
        state,
        stop_cb: StopFn = None,
        depth_step: int = 10,
        max_limit: int = 500
    ) -> List[str]:
        start_time = time.time()
        limit = 50

        while limit <= max_limit:
            stack = [state]
            visited = {state}
            expanded = 0

            while stack:
                curr = stack.pop()
                if curr.reached_goal():
                    print("**************** Solution Found ! ******************")
                    print(len(curr.get_move()))
                    print("ids: {:.2f} ms".format((time.time() - start_time) * 1000))
                    return list(curr.get_move())

                for e in curr.get_neighbors():
                    if e not in visited and len(e.get_move()) <= limit:
                        visited.add(e)
                        stack.append(e)

                expanded += 1
                if self._should_stop(expanded, stop_cb):
                    return []
            limit += depth_step
        return []

    def ucs_return_path(self, state, stop_cb: StopFn = None) -> List[str]:
        start_time = time.time()
        pq = []
        counter = itertools.count()
        heapq.heappush(pq, (0, next(counter), state))
        best_g = {state: 0}
        expanded = 0

        while pq:
            g, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("ucs: {:.2f} ms".format((time.time() - start_time) * 1000))
                return list(curr.get_move())

            for e in curr.get_neighbors():
                g2 = len(e.get_move())
                if e not in best_g or g2 < best_g[e]:
                    best_g[e] = g2
                    heapq.heappush(pq, (g2, next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                return []
        return []

    def greedy_return_path(self, state, heuristic, stop_cb: StopFn = None) -> List[str]:
        start_time = time.time()
        pq = []
        counter = itertools.count()

        def h(s):
            if heuristic == "euclidean":
                return s.euclidean()
            elif heuristic == "manhatten":
                return s.manhatten()
            return 0

        heapq.heappush(pq, (h(state), next(counter), state))
        visited = {state}
        expanded = 0

        while pq:
            _, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("greedy({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                return list(curr.get_move())

            for e in curr.get_neighbors():
                if e not in visited:
                    visited.add(e)
                    heapq.heappush(pq, (h(e), next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                return []
        return []

    def astar_return_path(self, state, heuristic, stop_cb: StopFn = None) -> List[str]:
        start_time = time.time()
        pq = []
        counter = itertools.count()

        def h(s):
            if heuristic == "euclidean":
                return s.euclidean()
            elif heuristic == "manhatten":
                return s.manhatten()
            return 0

        heapq.heappush(pq, (0, next(counter), state))
        best_g = {state: 0}
        expanded = 0

        while pq:
            _, _, curr = heapq.heappop(pq)
            if curr.reached_goal():
                print("**************** Solution Found ! ******************")
                print(len(curr.get_move()))
                print("A* ({}): {:.2f} ms".format(heuristic, (time.time() - start_time) * 1000))
                return list(curr.get_move())

            g = len(curr.get_move())
            for e in curr.get_neighbors():
                g2 = g + 1
                if e not in best_g or g2 < best_g[e]:
                    best_g[e] = g2
                    f = g2 + h(e)
                    heapq.heappush(pq, (f, next(counter), e))

            expanded += 1
            if self._should_stop(expanded, stop_cb):
                return []
        return []
