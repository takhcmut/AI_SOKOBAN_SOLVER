# -*- coding: utf-8 -*-
"""
Sokoban Solver Visualizer (UI)
Hotkeys:
  • ↑/↓: chuyển mục focus (Algorithm / Map / Solve / Back)
  • ←/→: đổi Algorithm (BFS/A*) hoặc đổi Map
  • Enter:
      - Ở mục Map: chuyển sang map kế tiếp (không auto-solve)
      - Ở mục Solve: bắt đầu solve
      - Ở màn Finished: sang map kế tiếp & quay lại menu
  • S: Solve nhanh
  • R: Replay khi đang Running/Finished
  • Esc hoặc C: Cancel khi đang Solving…
  • B: Back về menu
"""

import os
import sys
import time
import threading
from typing import List, Optional

import pygame

# ---- Paths ----
SCREEN_W, SCREEN_H = 1200, 760
ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
MAP_DIR = os.path.join(os.path.dirname(__file__), "..", "formal_inputs")
FONT_PATH = os.path.join(ASSET_DIR, "NotoSans-Regular.ttf")

# ---- Visual config ----
FPS = 90
TILE = 50
ANIM_DELAY_MS = 120

# Theme (Gen-Z pastel + dark)
COL_BG = (17, 19, 23)
COL_PANEL = (30, 34, 40)
COL_CARD = (40, 46, 54)
COL_ACCENT = (78, 156, 255)     # primary
COL_ACCENT_2 = (120, 220, 160)  # success
COL_MUTED = (160, 168, 180)
COL_TEXT = (230, 232, 236)
COL_BAD = (230, 110, 110)
COL_BTN = (58, 110, 210)
COL_BTN_DARK = (42, 86, 172)
RADIUS = 14

# ---- Backend imports ----
from sokoban import Sokoban
from state import State
from search import Search
from deadlock_detector import DeadLockDetector
from point import Point

# ------------- Helpers -------------
def load_image(path):
    full = os.path.join(ASSET_DIR, path)
    if not os.path.isfile(full):
        return None
    try:
        return pygame.image.load(full).convert_alpha()
    except Exception:
        return None

def list_maps():
    if not os.path.isdir(MAP_DIR):
        return []
    files = [f for f in os.listdir(MAP_DIR) if f.endswith(".txt")]
    files.sort()
    return files

# ------------- Pygame init -------------
pygame.init()
pygame.key.set_repeat(220, 45)  # repeat: delay, interval (ms)
flags = pygame.SCALED
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
pygame.display.set_caption("Sokoban Solver Visualizer")

if os.path.isfile(FONT_PATH):
    font = pygame.font.Font(FONT_PATH, 18)
    font_big = pygame.font.Font(FONT_PATH, 30)
    font_mid = pygame.font.Font(FONT_PATH, 22)
else:
    font = pygame.font.SysFont(None, 18)
    font_big = pygame.font.SysFont(None, 30)
    font_mid = pygame.font.SysFont(None, 22)

# ---- Assets ----
img_bg = load_image("bg.png")
img_wall = load_image("wall.png")
img_box = load_image("box.png")
img_box_goal = load_image("box_goal.png")
img_player = load_image("player.png")
img_goal = load_image("goal.png")

def scale_tile(img, t):
    return pygame.transform.smoothscale(img, (t, t)) if img else None

# ------------- Board rendering -------------
def draw_board(surface, sokoban: Sokoban, area, tile=TILE):
    """area: pygame.Rect vị trí render board"""
    sokoban.load_map()
    h = sokoban.get_height()
    w = sokoban.get_width()

    # fit
    max_w = area.w
    max_h = area.h
    t = tile
    if w * t > max_w or h * t > max_h:
        t = max(16, min(max_w // max(1, w), max_h // max(1, h)))

    # center
    ox = area.x + (max_w - w * t) // 2
    oy = area.y + (max_h - h * t) // 2

    # tile-cache by size
    wall = scale_tile(img_wall, t)
    box = scale_tile(img_box, t)
    box_goal = scale_tile(img_box_goal, t)
    player = scale_tile(img_player, t)
    goal = scale_tile(img_goal, t)
    bg = scale_tile(img_bg, t)

    # background grid
    if bg:
        for i in range(h):
            for j in range(w):
                surface.blit(bg, (ox + j * t, oy + i * t))
    else:
        pygame.draw.rect(surface, (245, 246, 250), (ox, oy, w * t, h * t), border_radius=8)

    # walls
    for p in sokoban.get_walls():
        x = ox + (p.get_y() - 1) * t
        y = oy + (p.get_x() - 1) * t
        if wall:
            surface.blit(wall, (x, y))
        else:
            pygame.draw.rect(surface, (82, 86, 98), (x, y, t, t), border_radius=6)

    # goals
    goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
    for gx, gy in goals:
        x = ox + (gy - 1) * t
        y = oy + (gx - 1) * t
        if goal:
            surface.blit(goal, (x, y))
        else:
            pygame.draw.circle(surface, (240, 205, 80), (x + t // 2, y + t // 2), max(4, t // 6))

    # boxes
    for b in sokoban.get_boxes():
        bx, by = b.get_x(), b.get_y()
        x = ox + (by - 1) * t
        y = oy + (bx - 1) * t
        if (bx, by) in goals and box_goal:
            surface.blit(box_goal, (x, y))
        elif box:
            surface.blit(box, (x, y))
        else:
            pygame.draw.rect(surface, (180, 140, 90), (x, y, t, t), border_radius=6)

    # player
    p = sokoban.get_player()
    x = ox + (p.get_y() - 1) * t
    y = oy + (p.get_x() - 1) * t
    if player:
        surface.blit(player, (x, y))
    else:
        pygame.draw.rect(surface, (72, 160, 255), (x + 3, y + 3, t - 6, t - 6), border_radius=6)

# ------------- Movement -------------
DIRS = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1),
        "U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

def apply_move_to_sokoban(sokoban: Sokoban, mv: str) -> bool:
    dx, dy = DIRS.get(mv, (0, 0))
    player = sokoban.get_player()
    px, py = player.get_x(), player.get_y()
    ax, ay = px + dx, py + dy

    walls = {(w.get_x(), w.get_y()) for w in sokoban.get_walls()}
    boxes = {(b.get_x(), b.get_y()) for b in sokoban.get_boxes()}

    if (ax, ay) in walls:
        return False
    if (ax, ay) in boxes:
        bx2, by2 = ax + dx, ay + dy
        if (bx2, by2) in walls or (bx2, by2) in boxes:
            return False
        new_boxes = set()
        for b in sokoban.get_boxes():
            if (b.get_x(), b.get_y()) == (ax, ay):
                new_boxes.add(Point(bx2, by2))
            else:
                new_boxes.add(Point(b.get_x(), b.get_y()))
        sokoban.set_boxes(new_boxes)

    sokoban.set_player(Point(ax, ay))
    sokoban.load_map()
    return True

# ------------- UI widgets -------------
def draw_panel(rect, title=None):
    pygame.draw.rect(screen, COL_PANEL, rect, border_radius=RADIUS)
    if title:
        txt = font_big.render(title, True, COL_TEXT)
        screen.blit(txt, (rect.x + 16, rect.y + 10))

def draw_button(rect, label, active=True, focused=False):
    col = COL_BTN if active else (60, 64, 72)
    if focused:
        # subtle glow
        pygame.draw.rect(screen, (90, 120, 220), rect.inflate(10, 10), border_radius=RADIUS)
    pygame.draw.rect(screen, col, rect, border_radius=RADIUS)
    t = font_mid.render(label, True, (255, 255, 255))
    screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

def draw_selector(rect, label, value, focused=False):
    pygame.draw.rect(screen, COL_CARD, rect, border_radius=RADIUS)
    l = font_mid.render(label, True, COL_MUTED)
    v = font_mid.render(value, True, COL_TEXT if not focused else COL_ACCENT)
    screen.blit(l, (rect.x + 14, rect.y + 10))
    screen.blit(v, (rect.x + 14, rect.y + 38))
    # arrows
    arw = "◀", "▶"
    aL = font_mid.render(arw[0], True, COL_MUTED)
    aR = font_mid.render(arw[1], True, COL_MUTED)
    screen.blit(aL, (rect.right - 70, rect.y + 36))
    screen.blit(aR, (rect.right - 34, rect.y + 36))

def draw_info(rect, info_lines):
    pygame.draw.rect(screen, COL_CARD, rect, border_radius=RADIUS)
    y = rect.y + 12
    for line, col in info_lines:
        t = font_mid.render(line, True, col)
        screen.blit(t, (rect.x + 14, y))
        y += t.get_height() + 6

# spinner overlay
def draw_spinner_overlay(text_top="Solving...", text_bottom="BFS/A* đang chạy ở nền, vui lòng chờ.", alpha=180, t=0.0):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))

    # center texts
    tt = font_big.render(text_top, True, (235, 235, 240))
    tb = font_mid.render(text_bottom, True, (220, 220, 228))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    # spinner (12 dots)
    R = 36
    n = 12
    for i in range(n):
        ang = (t * 4.0 + i) / n * 6.28318
        x = cx + int(R * 1.1 * pygame.math.Vector2(1, 0).rotate_rad(ang).x)
        y = cy + int(R * 1.1 * pygame.math.Vector2(1, 0).rotate_rad(ang).y)
        k = (i + (t * 12) % n) % n / (n - 1)
        col = (120 + int(80 * k), 170 + int(50 * k), 255)
        pygame.draw.circle(screen, col, (x, y), 5)

    screen.blit(tt, (cx - tt.get_width() // 2, cy - 70))
    screen.blit(tb, (cx - tb.get_width() // 2, cy + 40))

# ------------- Main -------------
def main():
    clock = pygame.time.Clock()

    # state
    maps = list_maps()
    map_index = 0 if maps else -1
    algo_list = ["BFS", "A*"]
    algo_index = 1  # default A*
    focus = 0       # 0: algo, 1: map, 2: solve, 3: back

    scene = "menu"  # menu | solving | running | finished
    sokoban: Optional[Sokoban] = None
    moves: List[str] = []
    move_idx = 0
    elapsed_ms = 0.0
    solved = False

    # solving thread
    solving = False
    cancel_evt = threading.Event()
    solver_thread: Optional[threading.Thread] = None
    solver_done = False
    solver_result: List[str] = []
    solver_elapsed = 0.0

    search = Search(False)

    # layout
    board_rect = pygame.Rect(20, 20, 760, 720)
    side_rect = pygame.Rect(800, 20, 380, 720)

    sel_algo = pygame.Rect(side_rect.x + 16, side_rect.y + 60, side_rect.w - 32, 90)
    sel_map = pygame.Rect(side_rect.x + 16, side_rect.y + 160, side_rect.w - 32, 90)
    info_rect = pygame.Rect(side_rect.x + 16, side_rect.y + 270, side_rect.w - 32, 210)

    btn_solve = pygame.Rect(side_rect.x + 16, side_rect.bottom - 120, 150, 48)
    btn_back = pygame.Rect(side_rect.right - 16 - 150, side_rect.bottom - 120, 150, 48)
    btn_replay = pygame.Rect(side_rect.right - 16 - 150, side_rect.bottom - 60, 150, 48)

    def current_map_path():
        return os.path.join(MAP_DIR, maps[map_index]) if (0 <= map_index < len(maps)) else None

    def load_preview():
        if map_index < 0 or map_index >= len(maps):
            return None
        try:
            s = Sokoban(current_map_path())
            s.load_map()
            return s
        except Exception:
            return None

    preview = load_preview()

    def cycle_map(delta):
        nonlocal map_index, preview
        if not maps:
            return
        map_index = (map_index + delta) % len(maps)
        preview = load_preview()

    def cycle_algo(delta):
        nonlocal algo_index
        algo_index = (algo_index + delta) % len(algo_list)

    def start_solve():
        nonlocal solving, solver_thread, cancel_evt, solver_done, solver_result, solver_elapsed, scene, elapsed_ms
        if map_index < 0 or map_index >= len(maps):
            return
        try:
            sk = Sokoban(current_map_path())
            detector = DeadLockDetector(sk)
            deadlocks = detector.get_deadlock()
            root = State(sk.get_walls(), sk.get_boxes(), sk.get_storages(), sk.get_player(),
                         "", sk.get_height(), sk.get_width(), False, deadlocks)

            cancel_evt.clear()
            solver_done = False
            solver_result = []
            solver_elapsed = 0.0

            def _worker():
                nonlocal solver_result, solver_elapsed, solver_done
                t0 = time.time()
                if algo_list[algo_index] == "BFS":
                    solver_result = search.bfs_return_path(root, stop_cb=cancel_evt.is_set)
                else:
                    solver_result = search.astar_return_path(root, "manhatten", stop_cb=cancel_evt.is_set)
                solver_elapsed = (time.time() - t0) * 1000.0
                solver_done = True

            solver_thread = threading.Thread(target=_worker, daemon=True)
            solver_thread.start()
            solving = True
            scene = "solving"
        except Exception as ex:
            print("Load map error:", ex)

    def apply_solution_and_run():
        nonlocal sokoban, moves, move_idx, elapsed_ms, solved, scene
        sokoban = Sokoban(current_map_path())
        sokoban.load_map()
        moves = list(solver_result)
        move_idx = 0
        elapsed_ms = solver_elapsed
        solved = False
        scene = "running"

    # main loop
    t_spin = 0.0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        t_spin += dt

        # handle solver completion
        if scene == "solving" and solving:
            if cancel_evt.is_set():
                solving = False
                scene = "menu"
            elif solver_done:
                solving = False
                if solver_result:
                    apply_solution_and_run()
                else:
                    # canceled hoặc không có lời giải
                    scene = "menu"

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                # global
                if ev.key == pygame.K_ESCAPE:
                    if scene == "solving":
                        cancel_evt.set()
                    elif scene in ("running", "finished"):
                        scene = "menu"
                # menu interactions
                if scene == "menu":
                    if ev.key == pygame.K_UP:
                        focus = (focus - 1) % 4
                    elif ev.key == pygame.K_DOWN:
                        focus = (focus + 1) % 4
                    elif ev.key == pygame.K_LEFT:
                        if focus == 0:
                            cycle_algo(-1)
                        elif focus == 1:
                            cycle_map(-1)
                    elif ev.key == pygame.K_RIGHT:
                        if focus == 0:
                            cycle_algo(1)
                        elif focus == 1:
                            cycle_map(1)
                    elif ev.key == pygame.K_RETURN:
                        if focus == 1:
                            cycle_map(1)  # enter trên map = next map (không auto-solve)
                        elif focus == 2:
                            start_solve()  # enter trên Solve => solve
                    elif ev.key == pygame.K_s:
                        start_solve()
                    elif ev.key == pygame.K_b:
                        preview = load_preview()  # refresh
                elif scene == "solving":
                    if ev.key in (pygame.K_c, pygame.K_ESCAPE):
                        cancel_evt.set()
                elif scene == "running":
                    if ev.key == pygame.K_r:
                        # replay
                        if map_index >= 0:
                            sokoban = Sokoban(current_map_path())
                            sokoban.load_map()
                            move_idx = 0
                            solved = False
                    elif ev.key == pygame.K_b:
                        scene = "menu"
                elif scene == "finished":
                    if ev.key == pygame.K_r:
                        # replay từ đầu
                        if map_index >= 0:
                            sokoban = Sokoban(current_map_path())
                            sokoban.load_map()
                            move_idx = 0
                            solved = False
                            scene = "running"
                    elif ev.key == pygame.K_RETURN:
                        # next map, quay lại menu
                        cycle_map(1)
                        scene = "menu"
                    elif ev.key == pygame.K_b:
                        scene = "menu"

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if scene == "menu":
                    if sel_algo.collidepoint(mx, my):
                        focus = 0
                    elif sel_map.collidepoint(mx, my):
                        focus = 1
                    elif btn_solve.collidepoint(mx, my):
                        focus = 2
                        start_solve()
                    elif btn_back.collidepoint(mx, my):
                        focus = 3
                        preview = load_preview()
                elif scene in ("running", "finished"):
                    if btn_back.collidepoint(mx, my):
                        scene = "menu"
                    elif btn_replay.collidepoint(mx, my):
                        if map_index >= 0:
                            sokoban = Sokoban(current_map_path())
                            sokoban.load_map()
                            move_idx = 0
                            solved = False
                            scene = "running"

        # --- update running animation ---
        if scene == "running" and sokoban is not None:
            if move_idx < len(moves):
                if (pygame.time.get_ticks() >= move_idx * ANIM_DELAY_MS):
                    mv = moves[move_idx]
                    apply_move_to_sokoban(sokoban, mv)
                    move_idx += 1
            else:
                # check goal
                goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
                solved = all((b.get_x(), b.get_y()) in goals for b in sokoban.get_boxes())
                scene = "finished"

        # --- draw ---
        screen.fill(COL_BG)

        # board card
        pygame.draw.rect(screen, COL_PANEL, board_rect, border_radius=RADIUS)
        inner = board_rect.inflate(-24, -24)
        pygame.draw.rect(screen, (26, 28, 34), inner, border_radius=RADIUS)

        # right panel
        draw_panel(side_rect, "Sokoban Solver")

        # content
        if scene in ("menu", "solving"):
            # preview board
            if preview:
                draw_board(screen, preview, inner)
        else:
            if sokoban:
                draw_board(screen, sokoban, inner)

        # selectors + info
        algo_val = algo_list[algo_index]
        map_val = maps[map_index] if maps else "(no maps)"
        draw_selector(sel_algo, "Algorithm", algo_val, focused=(scene == "menu" and focus == 0))
        draw_selector(sel_map, "Map", map_val, focused=(scene == "menu" and focus == 1))

        # info block
        info = []
        info.append((f"Map:  {map_val}", COL_TEXT))
        info.append((f"Algo: {algo_val}", COL_TEXT))
        if scene in ("running", "finished"):
            info.append((f"Step: {min(move_idx, len(moves))}/{len(moves)}", COL_TEXT))
            info.append((f"Time (ms): {elapsed_ms:.2f}", COL_TEXT))
            if scene == "finished":
                info.append(("SOLVED!" if solved else "FAILED", COL_ACCENT_2 if solved else COL_BAD))
        draw_info(info_rect, info)

        # buttons
        if scene == "menu":
            draw_button(btn_solve, "Solve (S)", focused=(focus == 2))
            draw_button(btn_back, "Back", focused=(focus == 3))
        else:
            draw_button(btn_back, "Back", active=True, focused=False)
            draw_button(btn_replay, "Replay (R)", active=True, focused=False)

        # solving overlay
        if scene == "solving":
            draw_spinner_overlay(t=t_spin)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
