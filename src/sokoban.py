from point import Point

class Sokoban:
    """
    Định dạng file map (5 dòng, toạ độ 1-based):
      1) rows cols
      2) wall_count   r1 c1 r2 c2 ...
      3) boxes_count  r1 c1 r2 c2 ...
      4) goals_count  r1 c1 r2 c2 ...
      5) player_r player_c

    Nội bộ giữ Point theo 1-based (phù hợp với cách bạn đang -1 khi ghi vào mảng).
    Bản đồ ASCII được dựng theo lớp:
      walls '#', goals '.', boxes '$' (hoặc '*' nếu trên goal), player '@' (hoặc '+' nếu trên goal).
    """

    def __init__(self, filename):
        # dữ liệu 1-based (giữ set để tra nhanh, tránh trùng)
        self.walls     = set()  # set[Point]
        self.storages  = set()  # goals
        self.boxes     = set()
        self.player    = None

        self.width  = 0  # = cols
        self.height = 0  # = rows

        self.read_input(filename)
        self.load_map()

    # --------------------- đọc file 5 dòng số ---------------------

    def read_input(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            # bỏ dòng trống / comment
            lines = [ln.strip() for ln in f.readlines()
                     if ln.strip() and not ln.lstrip().startswith("#")]

        if len(lines) < 5:
            raise ValueError("Map không đủ 5 dòng (rows/cols, walls, boxes, goals, player).")

        # 1) rows cols (theo chuẩn: rows - cols)
        parts = lines[0].split()
        if len(parts) != 2:
            raise ValueError("Dòng 1 phải có đúng 2 số: rows cols.")
        rows, cols = map(int, parts)
        if rows <= 0 or cols <= 0:
            raise ValueError("rows/cols phải > 0.")
        self.height = rows
        self.width  = cols

        # 2) 3) 4) các cặp toạ độ 1-based
        self._parse_and_load_pairs(lines[1], self.walls,    "WALLS",    rows, cols)
        self._parse_and_load_pairs(lines[2], self.boxes,    "BOXES",    rows, cols)
        self._parse_and_load_pairs(lines[3], self.storages, "GOALS",    rows, cols)

        # 5) player_r player_c (1-based)
        pos = list(map(int, lines[4].split()))
        if len(pos) != 2:
            raise ValueError("Dòng 5 phải có 2 số: player_r player_c.")
        pr, pc = pos
        if not (1 <= pr <= rows and 1 <= pc <= cols):
            raise ValueError(f"PLAYER vượt biên: ({pr}, {pc}) trong {rows}x{cols}.")
        self.player = Point(pr, pc)

        # kiểm tra va chạm với tường
        if Point(pr, pc) in self.walls:
            raise ValueError("PLAYER đè lên tường.")
        for b in self.boxes:
            if b in self.walls:
                raise ValueError(f"BOX đè lên tường tại ({b.get_x()}, {b.get_y()}).")

    def _parse_and_load_pairs(self, line, target_set, label, rows, cols):
        """
        line: "count r1 c1 r2 c2 ..."
        target_set: set[Point]
        """
        tokens = list(map(int, line.split()))
        if not tokens:
            raise ValueError(f"{label}: dòng rỗng.")
        count = tokens[0]
        coords = tokens[1:]
        if count < 0:
            raise ValueError(f"{label}: số lượng âm.")
        if len(coords) != count * 2:
            raise ValueError(f"{label}: khai báo {count} cặp nhưng thực tế có {len(coords)//2} cặp.")
        for i in range(0, len(coords), 2):
            r, c = coords[i], coords[i + 1]  # 1-based
            if not (1 <= r <= rows and 1 <= c <= cols):
                raise ValueError(f"{label}: toạ độ ({r}, {c}) vượt biên {rows}x{cols}.")
            target_set.add(Point(r, c))

    # --------------------- dựng ASCII map đúng lớp ---------------------

    def load_map(self):
        # ma trận [rows][cols]
        self.map = [[' ' for _ in range(self.width)] for _ in range(self.height)]

        # 1) walls
        for e in self.walls:
            self.map[e.get_x() - 1][e.get_y() - 1] = '#'

        # 2) goals (đừng ghi đè tường)
        for e in self.storages:
            if self.map[e.get_x() - 1][e.get_y() - 1] != '#':
                self.map[e.get_x() - 1][e.get_y() - 1] = '.'

        # 3) boxes (biến thành '*' nếu đang là goal)
        for e in self.boxes:
            r = e.get_x() - 1
            c = e.get_y() - 1
            if self.map[r][c] == '#':
                raise ValueError(f"BOX đè lên tường tại ({e.get_x()}, {e.get_y()}).")
            self.map[r][c] = '*' if self.map[r][c] == '.' else '$'

        # 4) player (thành '+' nếu đứng trên goal)
        pr = self.player.get_x() - 1
        pc = self.player.get_y() - 1
        if self.map[pr][pc] == '#':
            raise ValueError("PLAYER đè lên tường.")
        self.map[pr][pc] = '+' if self.map[pr][pc] == '.' else '@'

    # --------------------- tiện ích ---------------------

    def print_map(self):
        print("-------------Initial Map---------------------")
        print("The map is as follows:")
        for row in self.map:
            print(''.join(row))  # không thêm khoảng trống giữa ký tự

    # Giữ các getter/setter cũ để không vỡ code nơi khác
    def get_width(self):  return self.width
    def set_width(self, width): self.width = width
    def get_height(self): return self.height
    def set_height(self, height): self.height = height
    def get_walls(self): return self.walls
    def set_walls(self, walls): self.walls = walls
    def get_storages(self): return self.storages
    def set_storages(self, storages): self.storages = storages
    def get_boxes(self): return self.boxes
    def set_boxes(self, boxes): self.boxes = boxes
    def get_player(self): return self.player
    def set_player(self, player): self.player = player
