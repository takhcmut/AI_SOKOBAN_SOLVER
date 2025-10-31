from point import Point


class State:
    def __init__(self, walls, boxes, storages, player, move, rows, cols, verbose, deadlocks):
        self.walls = walls
        self.boxes = boxes
        self.storages = storages
        self.player = player
        self.neighbors = []
        self.move = move
        self.rows = rows
        self.cols = cols
        self.verbose = verbose
        self.deadlocks = set(deadlocks)

    def get_neighbors(self):
        x, y = self.player.get_x(), self.player.get_y()

        self.try_move(x - 1, y, x - 2, y, "u", self.verbose)
        self.try_move(x + 1, y, x + 2, y, "d", self.verbose)
        self.try_move(x, y - 1, x, y - 2, "l", self.verbose)
        self.try_move(x, y + 1, x, y + 2, "r", self.verbose)

        return self.neighbors

    def inbound(self, x, y):
        return 1 <= x <= self.rows and 1 <= y <= self.cols

    def try_move(self, ax, ay, bx, by, s, verbose):
        if verbose:
            print(f"{self.player} move {s} :")
        if not self.inbound(ax, ay) or not self.inbound(bx, by):
            if verbose:
                print(" not ok.")
            return

        attempt = Point(ax, ay)
        newbox = Point(bx, by)
        changed = False

        if attempt not in self.walls:
            if (attempt not in self.boxes) or (newbox not in self.boxes and newbox not in self.walls):
                if attempt in self.boxes:
                    if newbox in self.deadlocks:
                        return
                    self.boxes.remove(attempt)
                    self.boxes.add(newbox)
                    changed = True
                    if verbose:
                        print(f"success: box moves to {newbox}")

                if verbose:
                    print(f"player moves to {attempt}")
                cur = State(self.walls, set(self.boxes), set(self.storages), attempt, self.move + s, self.rows, self.cols, verbose, self.deadlocks)
                self.neighbors.append(cur)
                if verbose:
                    print(f"({self.player.get_x()},{self.player.get_y()}) -> {s} | total: {cur.get_move()}")
                    cur.load_map()
                    cur.print_map()
                if changed:
                    self.boxes.remove(newbox)
                    self.boxes.add(attempt)
                    changed = False
            else:
                if verbose:
                    print(" not ok.")
        else:
            if verbose:
                print(" not ok.")

    def reached_goal(self):
        return all(box in self.storages for box in self.boxes)

    def euclidean(self):
        x, y = self.player.get_x(), self.player.get_y()

        player_to_boxes = sum(((x - e.get_x()) ** 2 + (y - e.get_y()) ** 2) ** 0.5 for e in self.boxes)

        boxes_to_storages = sum(((ex - mx) ** 2 + (ey - my) ** 2) ** 0.5 for e in self.storages for m in self.boxes for ex, ey in [(e.get_x(), e.get_y())] for mx, my in [(m.get_x(), m.get_y())])
        return player_to_boxes + boxes_to_storages

    def manhatten(self):
        x, y = self.player.get_x(), self.player.get_y()

        player_to_boxes = sum(abs(x - e.get_x()) + abs(y - e.get_y()) for e in self.boxes)

        boxes_to_storages = sum(abs(ex - mx) + abs(ey - my) for e in self.storages for m in self.boxes for ex, ey in [(e.get_x(), e.get_y())] for mx, my in [(m.get_x(), m.get_y())])
        return player_to_boxes + boxes_to_storages

    def get_move(self):
        return self.move

    def get_player(self):
        return self.player

    def load_map(self):
        self.map = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        for e in self.walls:
            self.map[e.get_x() - 1][e.get_y() - 1] = '#'
        for e in self.storages:
            self.map[e.get_x() - 1][e.get_y() - 1] = '!'
        for e in self.boxes:
            self.map[e.get_x() - 1][e.get_y() - 1] = '@'
        self.map[self.player.get_x() - 1][self.player.get_y() - 1] = '*'

    def print_map(self):
        for row in self.map:
            print(' '.join(row))

    def get_size(self):
        return self.rows * self.cols

    def get_boxes(self):
        return self.boxes

    def __str__(self):
        return f"Current status: player at ({self.player.get_x()},{self.player.get_y()}) with path {self.move} and hashcode = {hash(self)}"

    def __hash__(self):
        box_hash_code = 0
        for e in self.boxes:
            box_hash_code += hash(e)
            box_hash_code *= 37
        return self.player.get_x() * 73 + self.player.get_y() + box_hash_code

    def __eq__(self, obj):
        if isinstance(obj, State):
            boxes1 = self.boxes
            boxes2 = obj.get_boxes()
            player2 = obj.get_player()
            return boxes1 == boxes2 and self.player == player2
        return False