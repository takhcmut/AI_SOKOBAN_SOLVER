# -*- coding: utf-8 -*-
import threading, time, queue
from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple, Any

ProgressCB = Callable[[int, float], None]  # (expanded, elapsed_sec)

@dataclass
class SolverResult:
    ok: bool
    path: Optional[List[str]]
    expanded: int
    elapsed: float
    reason: str = ""

class AsyncSolver:
    """Chạy solver trong thread phụ để UI không bị 'Not Responding'."""
    def __init__(self):
        self._th = None
        self._running = False
        self._lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.progress_q: "queue.Queue[Tuple[int,float]]" = queue.Queue()
        self.result: Optional[SolverResult] = None
        self._expanded_snapshot = 0

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, solve_func: Callable[..., Any], state, algo: str, heuristic: str):
        if self.is_running():
            return False
        self.cancel_event.clear()
        self.result = None
        self._expanded_snapshot = 0

        def progress_cb(expanded: int, elapsed: float):
            self._expanded_snapshot = expanded
            try: self.progress_q.put_nowait((expanded, elapsed))
            except queue.Full: pass

        def worker():
            t0 = time.time()
            try:
                path = solve_func(state, algo, heuristic, self.cancel_event, progress_cb)
                elapsed = time.time() - t0
                ok = bool(path)
                self.result = SolverResult(
                    ok=ok, path=path if ok else None,
                    expanded=self._expanded_snapshot, elapsed=elapsed,
                    reason="" if ok else ("canceled" if self.cancel_event.is_set() else "no-solution"),
                )
            except Exception as e:
                elapsed = time.time() - t0
                self.result = SolverResult(False, None, self._expanded_snapshot, elapsed, f"error: {e}")
            finally:
                with self._lock:
                    self._running = False

        with self._lock:
            self._running = True
        self._th = threading.Thread(target=worker, daemon=True)
        self._th.start()
        return True

    def cancel(self):
        self.cancel_event.set()

    def poll_progress(self):
        try:
            return self.progress_q.get_nowait()
        except queue.Empty:
            return None
