# -*- coding: utf-8 -*-
"""
Sokoban Solver Visualizer (UI) — bản hoàn chỉnh, ổn định

Tính năng:
- Speed chỉ chỉnh ở MENU qua selector (←/→, hoặc Q/E). Khi Running/Finished KHÔNG vẽ slider.
- Enter ở MENU: nếu focus=Map -> next map; ngược lại -> Solve ngay.
- Enter ở FINISHED: next map + về MENU.
- Chevron (mũi tên trái/phải) vẽ bằng polygon, không phụ thuộc font.
- Tên map 'đẹp' + hiển thị chỉ số (i/total).
- Đo bộ nhớ: psutil (RSS) + tracemalloc peak (nếu có) — tự động tắt nếu không cài.
- Solver chạy trong thread + cancel; tương thích search cũ (không có stop_cb) bằng try/except TypeError.

Hotkeys:
  ↑/↓           : chuyển focus (Algorithm / Map / Speed / Solve / Back)
  ←/→  hoặc Q/E : đổi Algorithm / Map / Speed (tuỳ focus)
  Enter         : MENU -> Solve (trừ khi focus=Map -> Next map) ; FINISHED -> Next map
  R             : Replay (khi Running/Finished) hoặc Solve nhanh ở MENU
  B / Esc       : Back về menu (hoặc Cancel khi Solving)
"""

import os
import time
import threading
from typing import List, Optional

import pygame

# -------- Paths & constants --------
SCREEN_W, SCREEN_H = 1200, 760
ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
MAP_DIR   = os.path.join(os.path.dirname(__file__), "..", "formal_inputs")
FONT_PATH = os.path.join(ASSET_DIR, "NotoSans-Regular.ttf")

FPS = 120
TILE = 50
RADIUS = 14

# Speed presets (ms/step)
SPEED_PRESETS = [
    ("Turbo", 30),
    ("Fast", 60),
    ("Normal", 120),
    ("Chill", 200),
    ("Snail", 350),
]
DEFAULT_SPEED_INDEX = 3  # Chill

# Theme
COL_BG     = (17, 19, 23)
COL_PANEL  = (30, 34, 40)
COL_CARD   = (40, 46, 54)
COL_ACCENT = (78, 156, 255)
COL_OK     = (120, 220, 160)
COL_MUTED  = (160, 168, 180)
COL_TEXT   = (230, 232, 236)
COL_BAD    = (230, 110, 110)
COL_BTN    = (58, 110, 210)
COL_BTN_OFF= (68, 72, 82)
COL_INNER  = (26, 28, 34)

# --- Optional memory measurement
_have_psutil = False
_have_tracemalloc = False
try:
    import psutil
    _have_psutil = True
except Exception:
    pass
try:
    import tracemalloc
    _have_tracemalloc = True
except Exception:
    pass

# -------- Backend imports --------
from sokoban import Sokoban
from state import State
from search import Search
from deadlock_detector import DeadLockDetector
from point import Point

# -------- Pygame init --------
pygame.init()
pygame.key.set_repeat(220, 45)
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED)
pygame.display.set_caption("Sokoban Solver Visualizer")

if os.path.isfile(FONT_PATH):
    font     = pygame.font.Font(FONT_PATH, 18)
    font_mid = pygame.font.Font(FONT_PATH, 22)
    font_big = pygame.font.Font(FONT_PATH, 30)
else:
    font     = pygame.font.SysFont(None, 18)
    font_mid = pygame.font.SysFont(None, 22)
    font_big = pygame.font.SysFont(None, 30)

# -------- Assets (optional) --------
def _load_img(name):
    p = os.path.join(ASSET_DIR, name)
    if not os.path.isfile(p): return None
    try:
        return pygame.image.load(p).convert_alpha()
    except Exception:
        return None

img_bg       = _load_img("bg.png")
img_wall     = _load_img("wall.png")
img_box      = _load_img("box.png")
img_box_goal = _load_img("box_goal.png")
img_player   = _load_img("player.png")
img_goal     = _load_img("goal.png")

def tscale(img, t):
    return pygame.transform.smoothscale(img, (t, t)) if img else None

# -------- Helpers --------
def list_maps():
    if not os.path.isdir(MAP_DIR): return []
    fs = [f for f in os.listdir(MAP_DIR) if f.endswith(".txt")]
    fs.sort()
    return fs

def round_rect(surf, rect, col, radius=RADIUS):
    pygame.draw.rect(surf, col, rect, border_radius=radius)

def draw_chevron(surface, center, size=10, direction="right", color=COL_MUTED):
    """Vẽ chevron polygon (không lệ thuộc font)."""
    cx, cy = center
    w = size
    h = int(size * 1.4)
    if direction == "right":
        pts = [(cx - w//2, cy - h//2), (cx - w//2, cy + h//2), (cx + w//2, cy)]
    else:
        pts = [(cx + w//2, cy - h//2), (cx + w//2, cy + h//2), (cx - w//2, cy)]
    pygame.draw.polygon(surface, color, pts)

def beautify_map_name(name: str) -> str:
    # bỏ .txt, đổi _ -> " · "
    if name.endswith(".txt"):
        name = name[:-4]
    return " · ".join(part for part in name.split("_") if part)

# -------- Board rendering --------
def draw_board(surface, sokoban: Sokoban, area: pygame.Rect, tile=TILE):
    sokoban.load_map()
    h, w = sokoban.get_height(), sokoban.get_width()

    t = tile
    if w*t > area.w or h*t > area.h:
        t = max(16, min(area.w // max(1, w), area.h // max(1, h)))

    ox = area.x + (area.w - w*t)//2
    oy = area.y + (area.h - h*t)//2

    bg       = tscale(img_bg, t)
    wall     = tscale(img_wall, t)
    box      = tscale(img_box, t)
    box_goal = tscale(img_box_goal, t)
    player   = tscale(img_player, t)
    goal     = tscale(img_goal, t)

    if bg:
        for i in range(h):
            for j in range(w):
                surface.blit(bg, (ox + j*t, oy + i*t))
    else:
        pygame.draw.rect(surface, (246, 247, 250), (ox, oy, w*t, h*t), border_radius=8)

    for p in sokoban.get_walls():
        x = ox + (p.get_y()-1)*t
        y = oy + (p.get_x()-1)*t
        if wall: surface.blit(wall, (x, y))
        else: pygame.draw.rect(surface, (84, 88, 100), (x, y, t, t), border_radius=6)

    goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
    for gx, gy in goals:
        x = ox + (gy-1)*t
        y = oy + (gx-1)*t
        if goal: surface.blit(goal, (x, y))
        else: pygame.draw.circle(surface, (240, 205, 80), (x + t//2, y + t//2), max(4, t//6))

    for b in sokoban.get_boxes():
        bx, by = b.get_x(), b.get_y()
        x = ox + (by-1)*t; y = oy + (bx-1)*t
        if (bx, by) in goals and box_goal: surface.blit(box_goal, (x, y))
        elif box: surface.blit(box, (x, y))
        else: pygame.draw.rect(surface, (180, 140, 90), (x, y, t, t), border_radius=6)

    p = sokoban.get_player()
    x = ox + (p.get_y()-1)*t; y = oy + (p.get_x()-1)*t
    if player: surface.blit(player, (x, y))
    else: pygame.draw.rect(surface, (72, 160, 255), (x+3, y+3, t-6, t-6), border_radius=6)

# -------- Movement --------
DIRS = {"u": (-1,0), "d": (1,0), "l": (0,-1), "r": (0,1),
        "U": (-1,0), "D": (1,0), "L": (0,-1), "R": (0,1)}

def apply_move_to_sokoban(sokoban: Sokoban, mv: str) -> bool:
    dx, dy = DIRS.get(mv, (0,0))
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

# -------- UI widgets --------
def draw_panel(rect, title=None):
    round_rect(screen, rect, COL_PANEL)
    if title:
        t = font_big.render(title, True, COL_TEXT)
        screen.blit(t, (rect.x + 16, rect.y + 10))

def draw_selector(rect, label, value, focused=False):
    round_rect(screen, rect, COL_CARD)
    l = font_mid.render(label, True, COL_MUTED)
    v = font_mid.render(value, True, COL_ACCENT if focused else COL_TEXT)
    screen.blit(l, (rect.x + 14, rect.y + 10))
    screen.blit(v, (rect.x + 14, rect.y + 38))
    # chevrons
    draw_chevron(screen, (rect.right - 70, rect.y + 48), size=12, direction="left",
                 color=COL_MUTED if not focused else COL_TEXT)
    draw_chevron(screen, (rect.right - 34, rect.y + 48), size=12, direction="right",
                 color=COL_MUTED if not focused else COL_TEXT)

def draw_button(rect, label, focused=False, active=True):
    col = COL_BTN if active else COL_BTN_OFF
    if focused:
        pygame.draw.rect(screen, (90, 120, 220), rect.inflate(10, 10), border_radius=RADIUS)
    round_rect(screen, rect, col)
    t = font_mid.render(label, True, (255, 255, 255))
    screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

def draw_info(rect, lines):
    round_rect(screen, rect, COL_CARD)
    y = rect.y + 12
    for s, c in lines:
        t = font_mid.render(s, True, c)
        screen.blit(t, (rect.x + 14, y))
        y += t.get_height() + 6  # <-- fixed: không còn dấu ')' thừa

# --- Keycap helpers for finished overlay ---
def keycap_size(text, pad_x=10, pad_y=6):
    w, h = font_mid.size(text)
    return (w + 2*pad_x + 2, h + 2*pad_y + 2)

def draw_keycap(surface, x, y, text, pad_x=10, pad_y=6):
    w, h = keycap_size(text, pad_x, pad_y)
    rect = pygame.Rect(x, y, w, h)
    # viền + nền
    pygame.draw.rect(surface, (54, 58, 68), rect, border_radius=8)
    pygame.draw.rect(surface, (90, 94, 106), rect, width=2, border_radius=8)
    t = font_mid.render(text, True, COL_TEXT)
    surface.blit(t, (rect.x + pad_x, rect.y + pad_y))
    return rect

def draw_spinner_overlay(text_top="Solving...", text_bottom="BFS/A* đang chạy ở nền, vui lòng chờ.", alpha=180, t=0.0):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))

    tt = font_big.render(text_top, True, (235, 235, 240))
    tb = font_mid.render(text_bottom, True, (220, 220, 228))
    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    R, n = 36, 12
    for i in range(n):
        ang = (t * 4.0 + i) / n * 6.28318
        v = pygame.math.Vector2(1, 0).rotate_rad(ang)
        x = cx + int(R * 1.1 * v.x)
        y = cy + int(R * 1.1 * v.y)
        k = (i + (t * 12) % n) % n / (n - 1)
        col = (120 + int(80 * k), 170 + int(50 * k), 255)
        pygame.draw.circle(screen, col, (x, y), 5)

    screen.blit(tt, (cx - tt.get_width() // 2, cy - 70))
    screen.blit(tb, (cx - tb.get_width() // 2, cy + 40))

def draw_finished_overlay(solved: bool):
    # lớp mờ
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 168))
    screen.blit(overlay, (0, 0))

    cx, cy = SCREEN_W // 2, SCREEN_H // 2

    # card trung tâm
    card_w, card_h = 760, 180
    card = pygame.Rect(cx - card_w//2, cy - card_h//2, card_w, card_h)
    pygame.draw.rect(screen, COL_PANEL, card, border_radius=16)
    pygame.draw.rect(screen, (60, 66, 76), card, width=2, border_radius=16)

    # tiêu đề + icon
    title = "SOLVED!" if solved else "FAILED"
    col   = COL_OK if solved else COL_BAD
    t1    = font_big.render(title, True, col)
    screen.blit(t1, (cx - t1.get_width()//2, card.y + 18))

    # icon check/x viền tròn
    ic_r = 14
    ic_c = (card.x + 28 + ic_r, card.y + 26 + ic_r)
    pygame.draw.circle(screen, (48, 52, 60), ic_c, ic_r + 2)
    pygame.draw.circle(screen, col, ic_c, ic_r, width=3)
    if solved:
        pygame.draw.lines(screen, col, False, [
            (ic_c[0]-7, ic_c[1]-1), (ic_c[0]-2, ic_c[1]+6), (ic_c[0]+8, ic_c[1]-7)
        ], 3)
    else:
        pygame.draw.line(screen, col, (ic_c[0]-7, ic_c[1]-7), (ic_c[0]+7, ic_c[1]+7), 3)
        pygame.draw.line(screen, col, (ic_c[0]-7, ic_c[1]+7), (ic_c[0]+7, ic_c[1]-7), 3)

    # hàng keycap
    items = [
        ("Enter", "Next map"),
        ("R",     "Replay"),
        ("B",     "Back"),
        ("Esc",   "Back"),
    ]
    GAP = 22
    KC_TXT_GAP = 10
    total_w = 0
    for key, desc in items:
        kc_w, kc_h = keycap_size(key)
        desc_w, _  = font_mid.size(desc)
        total_w += kc_w + KC_TXT_GAP + desc_w + GAP
    total_w -= GAP

    x = cx - total_w // 2
    y = card.y + 98

    for key, desc in items:
        kc = draw_keycap(screen, x, y, key)
        x = kc.right + KC_TXT_GAP
        t = font_mid.render(desc, True, (235, 235, 240))
        screen.blit(t, (x, y + (kc.height - t.get_height()) // 2))
        x += t.get_width() + GAP  # <-- fixed: không còn ')' thừa

# -------- Main --------
def main():
    clock = pygame.time.Clock()

    # menu state
    maps = list_maps()
    total_maps = len(maps)
    map_index = 0 if maps else -1
    algo_list = ["BFS", "A*"]
    algo_index = 1  # A* default
    speed_idx  = DEFAULT_SPEED_INDEX

    focus = 0  # 0: algo, 1: map, 2: speed, 3: solve, 4: back

    # scene state
    scene = "menu"  # menu | solving | running | finished
    preview: Optional[Sokoban] = None
    sokoban: Optional[Sokoban] = None

    # solution state
    moves: List[str] = []
    move_idx = 0
    elapsed_ms = 0.0
    solved = False

    # mem stats
    rss_before = rss_after = rss_delta = 0.0
    peak_mb = 0.0

    # animation
    anim_delay_ms = SPEED_PRESETS[speed_idx][1]
    step_accum_ms = 0.0

    # solver thread
    cancel_evt = threading.Event()
    solver_done = False
    solver_result: List[str] = []
    solver_elapsed = 0.0

    search = Search(False)

    # layout
    board_rect = pygame.Rect(20, 20, 760, 720)
    side_rect  = pygame.Rect(800, 20, 380, 720)

    sel_algo  = pygame.Rect(side_rect.x + 16, side_rect.y + 60,  side_rect.w - 32, 90)
    sel_map   = pygame.Rect(side_rect.x + 16, side_rect.y + 160, side_rect.w - 32, 90)
    sel_speed = pygame.Rect(side_rect.x + 16, side_rect.y + 260, side_rect.w - 32, 90)
    info_rect = pygame.Rect(side_rect.x + 16, side_rect.y + 370, side_rect.w - 32, 240)

    btn_solve = pygame.Rect(side_rect.x + 16, side_rect.bottom - 120, 180, 48)
    btn_back  = pygame.Rect(side_rect.right - 16 - 150, side_rect.bottom - 120, 150, 48)
    btn_repl  = pygame.Rect(side_rect.right - 16 - 150, side_rect.bottom - 60, 150, 48)

    def current_map_path():
        return os.path.join(MAP_DIR, maps[map_index]) if 0 <= map_index < len(maps) else None

    def load_preview():
        nonlocal preview
        if map_index < 0 or map_index >= len(maps):
            preview = None; return
        try:
            s = Sokoban(current_map_path()); s.load_map()
            preview = s
        except Exception:
            preview = None

    load_preview()

    def cycle_map(delta):
        nonlocal map_index
        if not maps: return
        map_index = (map_index + delta) % len(maps)
        load_preview()

    def cycle_algo(delta):
        nonlocal algo_index
        algo_index = (algo_index + delta) % len(algo_list)

    def cycle_speed(delta):
        nonlocal speed_idx, anim_delay_ms
        speed_idx = (speed_idx + delta) % len(SPEED_PRESETS)
        anim_delay_ms = SPEED_PRESETS[speed_idx][1]

    def start_solve():
        nonlocal solver_done, solver_result, solver_elapsed
        nonlocal rss_before, peak_mb
        if map_index < 0 or map_index >= len(maps): return False
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

            # memory before
            rss_before = psutil.Process(os.getpid()).memory_info().rss / (1024*1024) if _have_psutil else 0.0
            if _have_tracemalloc:
                try: tracemalloc.stop()
                except Exception: pass
                tracemalloc.start()

            def _worker():
                nonlocal solver_result, solver_elapsed, solver_done, peak_mb
                t0 = time.time()
                try:
                    if algo_list[algo_index] == "BFS":
                        try:
                            solver_result = search.bfs_return_path(root, stop_cb=cancel_evt.is_set)
                        except TypeError:
                            solver_result = search.bfs_return_path(root)
                    else:
                        try:
                            solver_result = search.astar_return_path(root, "manhatten", stop_cb=cancel_evt.is_set)
                        except TypeError:
                            solver_result = search.astar_return_path(root, "manhatten")
                finally:
                    solver_elapsed = (time.time() - t0) * 1000.0
                    if _have_tracemalloc:
                        try:
                            _, peak = tracemalloc.get_traced_memory()
                            peak_mb = peak / (1024*1024)
                        except Exception:
                            peak_mb = 0.0
                        try: tracemalloc.stop()
                        except Exception: pass
                    solver_done = True

            threading.Thread(target=_worker, daemon=True).start()
            return True
        except Exception as ex:
            print("Load/solve error:", ex)
            return False

    def apply_solution_and_run():
        nonlocal sokoban, moves, move_idx, elapsed_ms, solved, scene, step_accum_ms
        nonlocal rss_after, rss_delta
        sokoban = Sokoban(current_map_path()); sokoban.load_map()
        moves = list(solver_result)
        move_idx = 0
        elapsed_ms = solver_elapsed
        solved = False
        step_accum_ms = 0.0
        # memory after
        rss_after = psutil.Process(os.getpid()).memory_info().rss / (1024*1024) if _have_psutil else 0.0
        rss_delta = max(0.0, rss_after - rss_before) if (rss_after and rss_before) else 0.0
        scene = "running"

    # loop
    t_spin = 0.0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        t_spin += dt

        # Complete solving
        if scene == "solving":
            if cancel_evt.is_set():
                scene = "menu"
            elif solver_done:
                if solver_result:
                    apply_solution_and_run()
                else:
                    scene = "menu"

        # Events
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                # Global back/cancel
                if ev.key in (pygame.K_ESCAPE, pygame.K_b):
                    if scene == "solving":
                        cancel_evt.set()
                    else:
                        scene = "menu"

                # MENU
                if scene == "menu":
                    if ev.key == pygame.K_UP:   focus = (focus - 1) % 5
                    elif ev.key == pygame.K_DOWN: focus = (focus + 1) % 5
                    elif ev.key in (pygame.K_LEFT, pygame.K_q):
                        if   focus == 0: cycle_algo(-1)
                        elif focus == 1: cycle_map(-1)
                        elif focus == 2: cycle_speed(-1)
                    elif ev.key in (pygame.K_RIGHT, pygame.K_e):
                        if   focus == 0: cycle_algo(1)
                        elif focus == 1: cycle_map(1)
                        elif focus == 2: cycle_speed(1)
                    elif ev.key == pygame.K_RETURN:
                        if focus == 1:
                            cycle_map(1)  # Enter trên Map = next map
                        else:
                            if start_solve(): scene = "solving"
                    elif ev.key == pygame.K_r:
                        if start_solve(): scene = "solving"

                # SOLVING
                elif scene == "solving":
                    if ev.key == pygame.K_c:
                        cancel_evt.set()

                # RUNNING
                elif scene == "running":
                    if ev.key == pygame.K_r:
                        if 0 <= map_index < len(maps):
                            sokoban = Sokoban(current_map_path()); sokoban.load_map()
                            move_idx = 0; step_accum_ms = 0.0; solved = False

                # FINISHED
                elif scene == "finished":
                    if ev.key == pygame.K_r:
                        sokoban = Sokoban(current_map_path()); sokoban.load_map()
                        move_idx = 0; step_accum_ms = 0.0; solved = False
                        scene = "running"
                    elif ev.key == pygame.K_RETURN:
                        cycle_map(1); load_preview(); scene = "menu"

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if scene == "menu":
                    if sel_algo.collidepoint(mx, my):  focus = 0
                    elif sel_map.collidepoint(mx, my): focus = 1
                    elif sel_speed.collidepoint(mx, my): focus = 2
                    elif btn_solve.collidepoint(mx, my):
                        focus = 3
                        if start_solve(): scene = "solving"
                    elif btn_back.collidepoint(mx, my):
                        focus = 4
                        load_preview()
                elif scene in ("running", "finished"):
                    if btn_back.collidepoint(mx, my): scene = "menu"
                    elif btn_repl.collidepoint(mx, my):
                        if 0 <= map_index < len(maps):
                            sokoban = Sokoban(current_map_path()); sokoban.load_map()
                            move_idx = 0; step_accum_ms = 0.0; solved = False
                            scene = "running"

        # Update animation
        if scene == "running" and sokoban is not None:
            if move_idx < len(moves):
                step_accum_ms += dt * 1000.0
                while move_idx < len(moves) and step_accum_ms >= anim_delay_ms:
                    apply_move_to_sokoban(sokoban, moves[move_idx])
                    move_idx += 1
                    step_accum_ms -= anim_delay_ms
            else:
                goals = {(g.get_x(), g.get_y()) for g in sokoban.get_storages()}
                solved = all((b.get_x(), b.get_y()) in goals for b in sokoban.get_boxes())
                scene = "finished"

        # ---- Draw ----
        screen.fill(COL_BG)

        # containers
        round_rect(screen, board_rect, COL_PANEL)
        inner = board_rect.inflate(-24, -24)
        round_rect(screen, inner, COL_INNER)
        draw_panel(side_rect, "Sokoban Solver")

        # board
        if scene in ("menu", "solving"):
            if preview: draw_board(screen, preview, inner)
        else:
            if sokoban: draw_board(screen, sokoban, inner)

        # selectors
        algo_val = algo_list[algo_index]
        map_val  = maps[map_index] if maps else "(no maps)"
        speed_name, speed_ms = SPEED_PRESETS[speed_idx]

        draw_selector(sel_algo, "Algorithm", algo_val, focused=(scene == "menu" and focus == 0))

        nice_name = beautify_map_name(map_val)
        if total_maps > 0 and 0 <= map_index < total_maps:
            nice_name = f"{nice_name}   ({map_index+1}/{total_maps})"
        draw_selector(sel_map, "Map", nice_name, focused=(scene == "menu" and focus == 1))

        draw_selector(sel_speed, "Speed", f"{speed_name}  ({speed_ms} ms/step)",
                      focused=(scene == "menu" and focus == 2))

        # Info
        info_lines = []
        info_lines.append((f"Map:  {map_val}", COL_TEXT))
        info_lines.append((f"Algo: {algo_val}", COL_TEXT))
        if scene in ("running", "finished"):
            info_lines.append((f"Step: {min(move_idx, len(moves))}/{len(moves)}", COL_TEXT))
            info_lines.append((f"Time (ms): {elapsed_ms:.2f}", COL_TEXT))
            if _have_psutil:
                info_lines.append((f"Mem RSS: {rss_after:.1f} MB (Δ {rss_delta:.1f} MB)", COL_TEXT))
            if _have_tracemalloc and peak_mb:
                info_lines.append((f"Peak (Python): {peak_mb:.1f} MB", COL_TEXT))
            info_lines.append((f"Speed: {speed_name} ({speed_ms} ms)", COL_MUTED))
            if scene == "finished":
                info_lines.append(("SOLVED!" if solved else "FAILED",
                                   COL_OK if solved else COL_BAD))
        draw_info(info_rect, info_lines)

        # Buttons
        if scene == "menu":
            draw_button(btn_solve, "Solve (Enter)", focused=(focus == 3))
            draw_button(btn_back,  "Back",          focused=(focus == 4))
        else:
            draw_button(btn_back,  "Back")
            draw_button(btn_repl,  "Replay (R)")

        # Overlays
        if scene == "solving":
            draw_spinner_overlay(t=t_spin)
        elif scene == "finished":
            draw_finished_overlay(solved)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
