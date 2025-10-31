# -*- coding: utf-8 -*-
"""
state.py — Trạng thái Sokoban (tọa độ 1-based: x=row, y=col).

- Mục tiêu: biểu diễn nút trạng thái cho BFS/A*, sinh lân cận hợp lệ,
  hash/equality ổn định để dùng trong set/dict, và cung cấp heuristic admissible.

- Thành phần:
  * walls, boxes, storages: set[Point]
  * player: Point
  * move: chuỗi "udlr" từ đầu đến hiện tại (dùng để phát lại lời giải)
  * rows, cols: kích thước bản đồ
  * deadlocks: tập các ô "chết" (đẩy box vào là thua chắc), từ DeadLockDetector

- Heuristic:
  * manhatten(): admissible, nhanh — player→box gần nhất + Σ(box→goal gần nhất)
  * euclidean(): cùng ý tưởng, dùng khoảng cách Euclid (ít được dùng cho A* trong grid với đẩy hộp)

Lưu ý:
- __hash__ phải khớp __eq__: nếu boxes & player giống nhau ⇒ hash giống nhau.
- get_neighbors() KHÔNG làm thay đổi trạng thái gốc (copy set khi cần).
"""

from __future__ import annotations
from typing import Iterable, List, Set, Tuple
from point import Point


class State:
    __slots__ = (
        "walls", "boxes", "storages",
        "player", "move",
        "rows", "cols",
        "verbose", "deadlocks",
        "_neighbors_cache",
    )

    def __init__(
        self,
        walls: Iterable[Point],
        boxes: Iterable[Point],
        storages: Iterable[Point],
        player: Point,
        move: str,
        rows: int,
        cols: int,
        verbose: bool,
        deadlocks: Iterable[Point],
    ) -> None:
        # Sao chép vào set để trạng thái độc lập, tránh side-effect
        self.walls: Set[Point] = set(walls)
        self.boxes: Set[Point] = set(boxes)
        self.storages: Set[Point] = set(storages)
        self.player: Point = player
        self.move: str = move
        self.rows: int = int(rows)
        self.cols: int = int(cols)
        self.verbose: bool = bool(verbose)
        self.deadlocks: Set[Point] = set(deadlocks)
        self._neighbors_cache: List[State] | None = None

    # ------------------------- tiện ích cơ bản -------------------------

    def inbound(self, x: int, y: int) -> bool:
        """Ô (x,y) có nằm trong bản đồ không (1-based)."""
        return 1 <= x <= self.rows and 1 <= y <= self.cols

    def reached_goal(self) -> bool:
        """Tất cả box đều đứng trên goal (cho phép số goal ≥ số box)."""
        return all(b in self.storages for b in self.boxes)

    def get_move(self) -> str:
        return self.move

    def get_player(self) -> Point:
        return self.player

    def get_boxes(self) -> Set[Point]:
        return self.boxes

    # --------------------------- sinh lân cận --------------------------

    def get_neighbors(self) -> List["State"]:
        """
        Trả về danh sách trạng thái kề theo thứ tự U, D, L, R.
        Cache lần đầu để tránh tạo lại khi đã expand nút này.
        """
        if self._neighbors_cache is not None:
            return list(self._neighbors_cache)

        res: List[State] = []
        x, y = self.player.get_x(), self.player.get_y()
        self._try_move(res, x - 1, y, x - 2, y, "u")  # Up
        self._try_move(res, x + 1, y, x + 2, y, "d")  # Down
        self._try_move(res, x, y - 1, x, y - 2, "l")  # Left
        self._try_move(res, x, y + 1, x, y + 2, "r")  # Right
        self._neighbors_cache = res
        return res

    def _try_move(self, out: List["State"], ax: int, ay: int, bx: int, by: int, m: str) -> None:
        """
        Player thử bước sang (ax,ay). Nếu đó là hộp, hộp bị đẩy sang (bx,by).

        Hợp lệ khi:
          - (ax,ay) trong biên và không phải tường
          - Nếu (ax,ay) là box thì (bx,by) trong biên, không tường/không box,
            và KHÔNG thuộc deadlocks.
        """
        # Kiểm tra biên cho cả ô người đứng và ô đẩy box
        if not self.inbound(ax, ay):
            return
        if (ax, ay) in ((w.get_x(), w.get_y()) for w in self.walls):
            return

        attempt = Point(ax, ay)

        # Nếu là ô trống → bước thường
        if attempt not in self.boxes:
            out.append(
                State(
                    self.walls, self.boxes, self.storages,
                    attempt, self.move + m,
                    self.rows, self.cols, self.verbose, self.deadlocks,
                )
            )
            return

        # Nếu là hộp → đẩy sang (bx,by)
        if not self.inbound(bx, by):
            return
        newbox = Point(bx, by)
        if (newbox in self.walls) or (newbox in self.boxes):
            return
        if newbox in self.deadlocks:
            # Chặn sớm nhánh vô vọng
            return

        new_boxes = set(self.boxes)
        new_boxes.remove(attempt)
        new_boxes.add(newbox)

        out.append(
            State(
                self.walls, new_boxes, self.storages,
                attempt, self.move + m,
                self.rows, self.cols, self.verbose, self.deadlocks,
            )
        )

    # ----------------------------- heuristic -----------------------------

    def manhatten(self) -> int:
        """
        Heuristic Manhattan (admissible):
          H = (player → box gần nhất) + Σ(box → goal gần nhất)
        """
        # player → box gần nhất
        if self.boxes:
            px, py = self.player.get_x(), self.player.get_y()
            p2b = min(abs(px - b.get_x()) + abs(py - b.get_y()) for b in self.boxes)
        else:
            p2b = 0

        # mỗi box → goal gần nhất
        goals: List[Tuple[int, int]] = [(g.get_x(), g.get_y()) for g in self.storages]
        b2g = 0
        for b in self.boxes:
            bx, by = b.get_x(), b.get_y()
            b2g += min(abs(bx - gx) + abs(by - gy) for gx, gy in goals)

        return p2b + b2g

    def euclidean(self) -> float:
        """
        Heuristic Euclid: tương tự manhattan nhưng dùng sqrt.
        Chủ yếu để so sánh; trong grid 4 hướng, manhattan thường tốt hơn.
        """
        from math import hypot
        if self.boxes:
            px, py = self.player.get_x(), self.player.get_y()
            p2b = min(hypot(px - b.get_x(), py - b.get_y()) for b in self.boxes)
        else:
            p2b = 0.0

        goals: List[Tuple[int, int]] = [(g.get_x(), g.get_y()) for g in self.storages]
        b2g = 0.0
        for b in self.boxes:
            bx, by = b.get_x(), b.get_y()
            b2g += min(hypot(bx - gx, by - gy) for gx, gy in goals)

        return p2b + b2g

    # --------------------------- hash / equality --------------------------

    def __hash__(self) -> int:
        """
        Hash ổn định theo (vị trí player, tập boxes đã sort).
        Dùng tuple sorted để đảm bảo thứ tự không ảnh hưởng kết quả.
        """
        boxes_sorted = tuple(sorted((b.get_x(), b.get_y()) for b in self.boxes))
        return hash((self.player.get_x(), self.player.get_y(), boxes_sorted))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, State)
            and self.player == other.player
            and self.boxes == other.boxes
        )

    # ------------------------------- debug --------------------------------

    def load_map(self) -> None:
        """Dựng mảng ký tự để in debug khi cần (không dùng cho UI)."""
        self.map = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        for e in self.walls:
            self.map[e.get_x() - 1][e.get_y() - 1] = '#'
        for e in self.storages:
            self.map[e.get_x() - 1][e.get_y() - 1] = '.'
        for e in self.boxes:
            self.map[e.get_x() - 1][e.get_y() - 1] = '$'
        self.map[self.player.get_x() - 1][self.player.get_y() - 1] = '@'

    def print_map(self) -> None:
        for row in getattr(self, "map", []):
            print(' '.join(row))

    def __repr__(self) -> str:
        return f"State(player=({self.player.get_x()},{self.player.get_y()}), boxes={len(self.boxes)}, move='{self.move}')"
