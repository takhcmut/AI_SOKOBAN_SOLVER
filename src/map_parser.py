class MapParser:
    def __init__(self, filename):
        with open(filename, 'r') as file:
            lines = file.readlines()
        
        self.row = len(lines)
        self.col = len(lines[0].strip())
        self.map = [list(line.strip()) for line in lines]

    def parse(self):
        print(f"{self.col} {self.row}")

        numWalls = 0
        numBoxes = 0
        numStorages = 0
        walls = []
        boxes = []
        storages = []
        pos = []

        for i in range(self.row):
            for j in range(self.col):
                if self.map[i][j] == '#':
                    walls.append(i + 1)
                    walls.append(j + 1)
                    numWalls += 1
                elif self.map[i][j] == '$':
                    boxes.append(i + 1)
                    boxes.append(j + 1)
                    numBoxes += 1
                elif self.map[i][j] == '.':
                    storages.append(i + 1)
                    storages.append(j + 1)
                    numStorages += 1
                elif self.map[i][j] == '@':
                    pos.append(i + 1)
                    pos.append(j + 1)

        print(numWalls, " ".join(map(str, walls)))
        print(numBoxes, " ".join(map(str, boxes)))
        print(numStorages, " ".join(map(str, storages)))
        print(" ".join(map(str, pos)))