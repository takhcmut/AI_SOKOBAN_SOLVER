from point import Point


class DeadLockDetector:
    def __init__(self, sokoban):
        self.soku = sokoban
        self.walls = self.soku.get_walls()
        self.storages = self.soku.get_storages()
        self.width = self.soku.get_width()
        self.height = self.soku.get_height()
        self.map = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        self.deadlocks = set()
        self.load_map()

    def find_deadlock(self):
        for i in range(1, self.height + 1):
            for j in range(1, self.width + 1):
                current = Point(i, j)
                if current not in self.walls and current not in self.storages:
                    if self.corner_test(current):
                        self.deadlocks.add(current)
                        self.map[i - 1][j - 1] = '^'
                    elif self.boundary_test(current):
                        self.deadlocks.add(current)
                        self.map[i - 1][j - 1] = '?'

    def load_map(self):
        for e in self.walls:
            self.map[e.get_x() - 1][e.get_y() - 1] = '#'
        for e in self.storages:
            self.map[e.get_x() - 1][e.get_y() - 1] = '!'
        for e in self.soku.get_boxes():
            self.map[e.get_x() - 1][e.get_y() - 1] = '@'
        self.map[self.soku.get_player().get_x() - 1][self.soku.get_player().get_y() - 1] = '*'

    def print_map(self):
        for row in self.map:
            print(' '.join(row))

    def corner_test(self, current):
        up = self.get_up_neighbor(current)
        down = self.get_down_neighbor(current)
        right = self.get_right_neighbor(current)
        left = self.get_left_neighbor(current)

        return ((up in self.walls and right in self.walls) or
                (up in self.walls and left in self.walls) or
                (down in self.walls and left in self.walls) or
                (down in self.walls and right in self.walls))

    def boundary_test(self, current):
        x = current.get_x()
        y = current.get_y()

        if self.get_left_neighbor(current) in self.walls:
            upbound = self.find_nearest_upbound(current)
            downbound = self.find_nearest_downbound(current)

            if upbound == -1 or downbound == -1:
                return False
            else:
                for m in range(upbound + 1, downbound):
                    b = Point(m, y - 1)
                    if b not in self.walls:
                        return False
                return True

        if self.get_right_neighbor(current) in self.walls:
            upbound = self.find_nearest_upbound(current)
            downbound = self.find_nearest_downbound(current)

            if upbound == -1 or downbound == -1:
                return False
            else:
                for m in range(upbound + 1, downbound):
                    b = Point(m, y + 1)
                    if b not in self.walls:
                        return False
                return True

        if self.get_up_neighbor(current) in self.walls:
            rightbound = self.find_nearest_rightbound(current)
            leftbound = self.find_nearest_leftbound(current)

            if leftbound == -1 or rightbound == -1:
                return False
            else:
                for m in range(leftbound + 1, rightbound):
                    b = Point(x - 1, m)
                    if b not in self.walls:
                        return False
                return True

        if self.get_down_neighbor(current) in self.walls:
            rightbound = self.find_nearest_rightbound(current)
            leftbound = self.find_nearest_leftbound(current)

            if leftbound == -1 or rightbound == -1:
                return False
            else:
                for m in range(leftbound + 1, rightbound):
                    b = Point(x + 1, m)
                    if b not in self.walls:
                        return False
                return True

        return False

    def get_right_neighbor(self, current):
        return Point(current.get_x(), current.get_y() + 1)

    def get_left_neighbor(self, current):
        return Point(current.get_x(), current.get_y() - 1)

    def get_up_neighbor(self, current):
        return Point(current.get_x() - 1, current.get_y())

    def get_down_neighbor(self, current):
        return Point(current.get_x() + 1, current.get_y())

    def find_nearest_upbound(self, a):
        y = a.get_y()
        x = a.get_x() - 1

        while x >= 0:
            temp = Point(x, y)
            if temp in self.walls:
                return x
            elif temp in self.storages:
                return -1
            x -= 1
        return 0

    def find_nearest_downbound(self, a):
        y = a.get_y()
        x = a.get_x() + 1

        while x < self.height:
            temp = Point(x, y)
            if temp in self.walls:
                return x
            elif temp in self.storages:
                return -1
            x += 1
        return self.height

    def find_nearest_rightbound(self, a):
        y = a.get_y() + 1
        x = a.get_x()

        while y < self.width:
            temp = Point(x, y)
            if temp in self.walls:
                return y
            elif temp in self.storages:
                return -1
            y += 1
        return self.width

    def find_nearest_leftbound(self, a):
        y = a.get_y() - 1
        x = a.get_x()

        while y >= 0:
            temp = Point(x, y)
            if temp in self.walls:
                return y
            elif temp in self.storages:
                return -1
            y -= 1
        return 0

    def get_deadlock(self):
        self.find_deadlock()
        return set(self.deadlocks)

    def __str__(self):
        return ' '.join(str(e) for e in self.deadlocks)