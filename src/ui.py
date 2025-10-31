# src/ui.py
import pygame
import sys
import os
import time
from typing import List

# import backend của bạn
from sokoban import Sokoban
from state import State
from search import Search
from deadlock_detector import DeadLockDetector
from point import Point

# --- CONFIG ---
SCREEN_W, SCREEN_H = 1024, 768
ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
MAP_DIR = os.path.join(os.path.dirname(__file__), "..", "formal_inputs")
FONT_PATH = os.path.join(ASSET_DIR, "NotoSans-Regular.ttf")

TILE = 48  # kích thước ô (ghi nhớ map có thể nhỏ/ lớn; UI cố gắng fit xuống nếu cần)
ANIM_DELAY_MS = 150  # độ trễ mỗi bước

# --- helper load ---
def load_image(name):
    p = os.path.join(ASSET_DIR, name)
    if not os.path.isfile(p):
        return None
    try:
        im = pygame.image.load(p).convert_alpha()
        return im
    except Exception:
        return None

# --- Khởi tạo pygame ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Sokoban Solver Visualizer")
if os.path.isfile(FONT_PATH):
    font = pygame.font.Font(FONT_PATH, 20)
    font_big = pygame.font.Font(FONT_PATH, 28)
else:
    font = pygame.font.SysFont(None, 20)
    font_big = pygame.font.SysFont(None, 28)

# --- Load assets ---
img_bg = load_image("bg.png")
img_wall = load_image("wall.png")
img_box = load_image("box.png")
img_box_goal = load_image("box_goal.png")
img_player = load_image("player.png")
img_goal = load_image("goal.png")

# scale images to TILE
def scale_if(img):
    if not img: return None
    return pygame.transform.smoothscale(img, (TILE, TILE))

img_wall = scale_if(img_wall)
img_box = scale_if(img_box)
img_box_goal = scale_if(img_box_goal)
img_player = scale_if(img_player)
img_goal = scale_if(img_goal)
if img_bg:
    img_bg = pygame.transform.smoothscale(img_bg, (TILE, TILE))  # will tile it

# --- UI helpers ---
def draw_text(surf, text, x, y, col=(255,255,255), big=False):
    f = font_big if big else font
    surf.blit(f.render(text, True, col), (x, y))

def list_maps():
    if not os.path.isdir(MAP_DIR):
        return []
    files = [f for f in os.listdir(MAP_DIR) if f.endswith(".txt")]
    files.sort()
    return files

# --- Core: render sokoban state ---
def draw_board(surf, sokoban: Sokoban, origin_x=20, origin_y=20):
    # fit board into available area (simple: left-top anchor)
    sokoban.load_map()  # ensure sokoban.map consistent with sets
    h = sokoban.get_height()
    w = sokoban.get_width()
    # calculate tile size to fit if too large
    max_w = SCREEN_W - 280  # reserve right panel
    max_h = SCREEN_H - 40
    t = TILE
    if w * t > max_w or h * t > max_h:
        t = min(max_w // max(1,w), max_h // max(1,h), TILE)
    ox = origin_x
    oy = origin_y
    # background tiles
    if img_bg:
        for i in range(h):
            for j in range(w):
                surf.blit(img_bg, (ox + j*t, oy + i*t))
    else:
        pygame.draw.rect(surf, (40,40,40), (ox, oy, w*t, h*t))
    # draw walls, goals, boxes, player
    # walls
    for p in sokoban.get_walls():
        x = p.get_y()-1  # sokoban.map uses map[row][col], p.get_x() is row, p.get_y() is col
        y = p.get_x()-1
        # Note: original code used map[row][col]; to place at correct axes we use (col,row)
        # But above mapping was inconsistent across code; keep consistent with sokoban.map indexing:
        # sokoban.map[row][col] => draw at (col, row)
        surf_x = ox + (p.get_y()-1) * t
        surf_y = oy + (p.get_x()-1) * t
        if img_wall:
            surf.blit(pygame.transform.smoothscale(img_wall, (t,t)), (surf_x, surf_y))
        else:
            pygame.draw.rect(surf, (80,80,80), (surf_x, surf_y, t, t))
    # goals
    goals = { (g.get_x(), g.get_y()) for g in sokoban.get_storages() }
    for gx, gy in goals:
        surf_x = ox + (gy-1) * t
        surf_y = oy + (gx-1) * t
        if img_goal:
            surf.blit(pygame.transform.smoothscale(img_goal, (t,t)), (surf_x, surf_y))
        else:
            pygame.draw.circle(surf, (230,200,60), (surf_x + t//2, surf_y + t//2), max(3, t//6))
    # boxes (draw box_goal if on goal)
    for b in sokoban.get_boxes():
        bx, by = b.get_x(), b.get_y()
        surf_x = ox + (by-1) * t
        surf_y = oy + (bx-1) * t
        if (bx, by) in goals and img_box_goal:
            surf.blit(pygame.transform.smoothscale(img_box_goal, (t,t)), (surf_x, surf_y))
        elif img_box:
            surf.blit(pygame.transform.smoothscale(img_box, (t,t)), (surf_x, surf_y))
        else:
            pygame.draw.rect(surf, (200,150,0), (surf_x, surf_y, t, t))
    # player
    p = sokoban.get_player()
    surf_x = ox + (p.get_y()-1) * t
    surf_y = oy + (p.get_x()-1) * t
    if img_player:
        surf.blit(pygame.transform.smoothscale(img_player, (t,t)), (surf_x, surf_y))
    else:
        pygame.draw.rect(surf, (72,160,255), (surf_x+3, surf_y+3, t-6, t-6))

# --- Movement helpers (Sokoban stores Points 1-based) ---
DIRS = {
    "u": (-1, 0),
    "d": (1, 0),
    "l": (0, -1),
    "r": (0, 1),
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

def apply_move_to_sokoban(sokoban: Sokoban, mv: str):
    """Áp dụng 1 move ('u','d','l','r') lên đối tượng sokoban.
    Nếu player đẩy box, cập nhật set boxes. Trả về True nếu thay đổi hợp lệ."""
    dx, dy = DIRS.get(mv, (0,0))
    player = sokoban.get_player()
    px, py = player.get_x(), player.get_y()
    ax, ay = px + dx, py + dy  # attempt square (1-based)
    # check if wall
    walls_coords = {(w.get_x(), w.get_y()) for w in sokoban.get_walls()}
    boxes_coords = {(b.get_x(), b.get_y()) for b in sokoban.get_boxes()}
    if (ax, ay) in walls_coords:
        return False
    if (ax, ay) in boxes_coords:
        # we will push box to bx2, by2
        bx2, by2 = ax + dx, ay + dy
        if (bx2, by2) in walls_coords or (bx2, by2) in boxes_coords:
            return False
        # move box: create new set of Points
        new_boxes = set()
        for b in sokoban.get_boxes():
            if (b.get_x(), b.get_y()) == (ax, ay):
                new_boxes.add(Point(bx2, by2))
            else:
                new_boxes.add(Point(b.get_x(), b.get_y()))
        sokoban.set_boxes(new_boxes)
    # move player
    sokoban.set_player(Point(ax, ay))
    # refresh internal map
    sokoban.load_map()
    return True

# --- Main application ---
def main():
    clock = pygame.time.Clock()
    running = True

    # UI state
    maps = list_maps()
    map_index = 0 if maps else -1
    algo_list = ["BFS", "A*"]
    algo_index = 1  # default A*
    scene = "menu"  # or "running" or "finished"
    sokoban = None
    root_state = None
    moves: List[str] = []
    move_idx = 0
    start_time = 0.0
    elapsed_ms = 0.0
    solved = False
    auto_replay = False

    search = Search(False)

    # simple buttons: rectangles
    btn_load = pygame.Rect(520, 120, 100, 36)
    btn_play = pygame.Rect(640, 120, 100, 36)
    btn_back = pygame.Rect(520, 520, 100, 36)
    btn_replay = pygame.Rect(640, 520, 100, 36)

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if scene == "menu":
                    # left click change selection
                    if 50 <= mx <= 460 and 100 <= my <= 140:
                        # click map area -> cycle
                        map_index = (map_index + 1) % max(1, len(maps))
                    if 50 <= mx <= 460 and 160 <= my <= 200:
                        algo_index = (algo_index + 1) % len(algo_list)
                    if btn_load.collidepoint(ev.pos):
                        maps = list_maps()
                        if map_index >= len(maps):
                            map_index = 0 if maps else -1
                    if btn_play.collidepoint(ev.pos):
                        # start run
                        if map_index < 0 or map_index >= len(maps):
                            # nothing
                            pass
                        else:
                            # init sokoban from file
                            filename = os.path.join(MAP_DIR, maps[map_index])
                            try:
                                sokoban = Sokoban(filename)
                                detector = DeadLockDetector(sokoban)
                                deadlocks = detector.get_deadlock()
                                root_state = State(sokoban.get_walls(), sokoban.get_boxes(),
                                                   sokoban.get_storages(), sokoban.get_player(),
                                                   "", sokoban.get_height(), sokoban.get_width(), False, deadlocks)
                                # choose solver
                                algo = algo_list[algo_index]
                                moves = []
                                t0 = time.time()
                                if algo == "BFS":
                                    moves = search.bfs_return_path(root_state)
                                else:
                                    moves = search.astar_return_path(root_state, "manhatten")
                                elapsed_ms = (time.time() - t0) * 1000.0
                                move_idx = 0
                                start_time = time.time()
                                scene = "running"
                                solved = False
                                # make sure sokoban inits map reflects sets
                                sokoban.load_map()
                            except Exception as ex:
                                print("Load map error:", ex)
                elif scene == "running":
                    # no manual moves; allow clicking Back to return to menu early
                    if btn_back.collidepoint(ev.pos):
                        scene = "menu"
                    # allow clicking Replay while running to restart
                    if btn_replay.collidepoint(ev.pos):
                        # reset sokoban and restart animation
                        if sokoban and map_index >= 0:
                            filename = os.path.join(MAP_DIR, maps[map_index])
                            sokoban = Sokoban(filename)
                            sokoban.load_map()
                            move_idx = 0
                            start_time = time.time()
                            solved = False
                elif scene == "finished":
                    if btn_back.collidepoint(ev.pos):
                        scene = "menu"
                    if btn_replay.collidepoint(ev.pos):
                        # restart same map and re-run moves
                        if sokoban and map_index >= 0:
                            filename = os.path.join(MAP_DIR, maps[map_index])
                            sokoban = Sokoban(filename)
                            sokoban.load_map()
                            move_idx = 0
                            start_time = time.time()
                            scene = "running"
                            solved = False

            elif ev.type == pygame.KEYDOWN:
                if scene == "menu":
                    if ev.key == pygame.K_RIGHT:
                        map_index = (map_index + 1) % max(1, len(maps))
                    elif ev.key == pygame.K_LEFT:
                        map_index = (map_index - 1) % max(1, len(maps))
                    elif ev.key == pygame.K_DOWN or ev.key == pygame.K_UP:
                        algo_index = (algo_index + 1) % len(algo_list)
                    elif ev.key == pygame.K_RETURN:
                        # same as Play
                        if map_index >= 0 and map_index < len(maps):
                            filename = os.path.join(MAP_DIR, maps[map_index])
                            try:
                                sokoban = Sokoban(filename)
                                detector = DeadLockDetector(sokoban)
                                deadlocks = detector.get_deadlock()
                                root_state = State(sokoban.get_walls(), sokoban.get_boxes(),
                                                   sokoban.get_storages(), sokoban.get_player(),
                                                   "", sokoban.get_height(), sokoban.get_width(), False, deadlocks)
                                algo = algo_list[algo_index]
                                t0 = time.time()
                                if algo == "BFS":
                                    moves = search.bfs_return_path(root_state)
                                else:
                                    moves = search.astar_return_path(root_state, "manhatten")
                                elapsed_ms = (time.time() - t0) * 1000.0
                                move_idx = 0
                                start_time = time.time()
                                scene = "running"
                                solved = False
                                sokoban.load_map()
                            except Exception as ex:
                                print("Load map error:", ex)

        # --- update animation when running ---
        if scene == "running" and sokoban is not None:
            if move_idx < len(moves):
                now = time.time()
                # step based on delay
                # we'll use pygame clock tick to regulate
                # move one step every ANIM_DELAY_MS
                if (time.time() - start_time) * 1000.0 >= move_idx * ANIM_DELAY_MS:
                    mv = moves[move_idx]
                    applied = apply_move_to_sokoban(sokoban, mv)
                    move_idx += 1
                    # check goal
                    if sokoban.get_boxes():
                        all_on_goal = True
                        goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
                        for b in sokoban.get_boxes():
                            if (b.get_x(), b.get_y()) not in goals:
                                all_on_goal = False
                                break
                        if all_on_goal:
                            solved = True
                            scene = "finished"
            else:
                # finished sequence
                # check if solved
                goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
                all_on_goal = True
                for b in sokoban.get_boxes():
                    if (b.get_x(), b.get_y()) not in goals:
                        all_on_goal = False
                        break
                solved = all_on_goal
                scene = "finished"

        # --- draw ---
        screen.fill((20,20,24))
        if scene == "menu":
            # left panel
            draw_text(screen, "Sokoban Solver (Visualizer)", 30, 20, big=True)
            draw_text(screen, "Map (click or ←/→):", 30, 100)
            draw_text(screen, maps[map_index] if map_index >=0 and maps else "(no maps)", 40, 125, (220,200,100))
            draw_text(screen, "Algorithm (click or ↑/↓):", 30, 160)
            draw_text(screen, algo_list[algo_index], 40, 185, (220,200,100))
            # buttons
            pygame.draw.rect(screen, (60,60,70), btn_load, border_radius=6)
            draw_text(screen, "Load Maps", btn_load.x+12, btn_load.y+8)
            pygame.draw.rect(screen, (50,150,100), btn_play, border_radius=6)
            draw_text(screen, "Play", btn_play.x+34, btn_play.y+8)
            # hint
            draw_text(screen, "Use arrow keys or click to pick map/algorithm. Press Enter or Play.", 30, 240, (180,180,180))
            # preview small board if map exists
            if map_index >= 0 and maps:
                try:
                    preview_path = os.path.join(MAP_DIR, maps[map_index])
                    preview_sok = Sokoban(preview_path)
                    preview_sok.load_map()
                    # preview at right
                    draw_board(screen, preview_sok, origin_x=320, origin_y=80)
                except Exception:
                    pass

        elif scene in ("running", "finished"):
            # draw board
            if sokoban:
                draw_board(screen, sokoban, origin_x=20, origin_y=20)
            # right panel info
            rx = SCREEN_W - 240
            draw_text(screen, "Info", rx+16, 16, big=True)
            draw_text(screen, f"Map: {maps[map_index] if maps else ''}", rx+16, 60)
            draw_text(screen, f"Algo: {algo_list[algo_index]}", rx+16, 90)
            draw_text(screen, f"Step: {min(move_idx, len(moves))}/{len(moves)}", rx+16, 130)
            draw_text(screen, f"Time (ms): {elapsed_ms:.2f}", rx+16, 160)
            if scene == "finished":
                st = "SOLVED!" if solved else "FAILED"
                draw_text(screen, st, rx+16, 210, (120,220,120) if solved else (220,100,100), big=True)
            # buttons
            pygame.draw.rect(screen, (60,60,70), btn_back, border_radius=6)
            draw_text(screen, "Back", btn_back.x+22, btn_back.y+8)
            pygame.draw.rect(screen, (50,120,200), btn_replay, border_radius=6)
            draw_text(screen, "Replay", btn_replay.x+20, btn_replay.y+8)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
