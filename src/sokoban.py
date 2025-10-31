from point import Point


class Sokoban:
    def __init__(self, filename):
        self.walls = set()
        self.storages = set()
        self.boxes = set()
        self.read_input(filename)
        self.load_map()

    def read_input(self, filename):
        with open(filename, 'r') as file:
            sizes = file.readline().strip().split()
            n_walls = file.readline().strip().split()
            n_boxes = file.readline().strip().split()
            n_storages = file.readline().strip().split()
            pos = file.readline().strip().split()

            # Handle sizes
            self.width = int(sizes[0])
            self.height = int(sizes[1])

            # Handle objects
            self.load(n_walls, self.walls, "walls")
            self.load(n_boxes, self.boxes, "boxes")
            self.load(n_storages, self.storages, "storages")

            # Handle player
            self.player = Point(int(pos[0]), int(pos[1]))

    def load(self, arr, hst, name):
        num = int(arr[0]) - 1
        for i in range(num):
            hst.add(Point(int(arr[2 * i + 1]), int(arr[2 * i + 2])))

    def load_map(self):
        self.map = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        for e in self.walls:
            self.map[e.get_x() - 1][e.get_y() - 1] = '#'
        for e in self.boxes:
            self.map[e.get_x() - 1][e.get_y() - 1] = '$'
        for e in self.storages:
            self.map[e.get_x() - 1][e.get_y() - 1] = '.'
        self.map[self.player.get_x() - 1][self.player.get_y() - 1] = '@'

    def print_map(self):
        print("-------------Initial Map---------------------")
        print("The map is as follows:")
        for row in self.map:
            print(' '.join(row))

    def get_width(self):
        return self.width

    def set_width(self, width):
        self.width = width

    def get_height(self):
        return self.height

    def set_height(self, height):
        self.height = height

    def get_walls(self):
        return self.walls

    def set_walls(self, walls):
        self.walls = walls

    def get_storages(self):
        return self.storages

    def set_storages(self, storages):
        self.storages = storages

    def get_boxes(self):
        return self.boxes

    def set_boxes(self, boxes):
        self.boxes = boxes

    def get_player(self):
        return self.player

    def set_player(self, player):
        self.player = player