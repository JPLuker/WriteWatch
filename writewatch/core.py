"""Content is read transiently. Only aggregate numbers leave the parser."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import sqlite3
import time
import uuid

from .formats import ScriptError, word_count


@dataclass
class Session:
    id: str
    started: str
    mode: str
    goal: int
    seconds: float = 0
    net: int = 0
    saves: int = 0
    status: str = "running"

    @classmethod
    def new(cls, mode: str, goal: int):
        if mode not in ("Writing", "Revision") or not 0 <= goal <= 100000:
            raise ValueError("Invalid session goal")
        return cls(uuid.uuid4().hex, datetime.now().astimezone().isoformat(), mode, goal)

    @property
    def progress(self):
        if self.goal == 0:
            return 0.0
        amount = max(0, self.net) if self.mode == "Writing" else self.seconds / 60
        return min(1.0, amount / self.goal)

    @property
    def goal_label(self):
        if not self.goal:
            return "No goal set"
        return f"{self.goal:,} net words" if self.mode == "Writing" else f"{self.goal} minutes"

    @property
    def goal_result(self):
        if not self.goal:
            return "No goal set"
        if self.progress >= 1:
            return "Goal reached"
        return f"{round(self.progress * 100)}% of goal"

    def summary(self):
        date = datetime.fromisoformat(self.started).strftime("%b %d, %Y")
        minutes, seconds = divmod(int(self.seconds), 60)
        heading = "Session complete" if self.status == "done" else "Interrupted session"
        lines = [f"WriteWatch · {date}", f"{self.mode} · {heading}",
                 f"Time: {minutes}m {seconds:02d}s · {self.net:+,} net words"]
        if self.goal:
            lines += [f"Goal: {self.goal_label}", f"Goal progress: {round(self.progress * 100)}%"]
        return "\n".join(lines + ["#WriteWatch"])


class Tracker:
    """Manual timer; paused edits are excluded on resume. No text snapshots."""
    def __init__(self, path: Path, mode: str, goal: int, clock=time.monotonic):
        self.path = path
        self.clock = clock
        self.previous, self.signature = self.read_snapshot()
        self.session = Session.new(mode, goal)
        self.last_tick = clock()

    def tick(self):
        now = self.clock()
        gap = max(0, now - self.last_tick)
        self.last_tick = now
        if self.session.status == "running":
            if gap > 30:
                self.session.status = "paused"  # suspension / long event-loop stall
            else:
                self.session.seconds += gap

    def file_signature(self):
        try:
            stat = self.path.stat()
            return (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        except OSError:
            raise ScriptError("The selected file is unavailable. Restore it or save it again, then retry.") from None

    def read_snapshot(self):
        before = self.file_signature()
        count = word_count(self.path)
        after = self.file_signature()
        if before != after:
            raise ScriptError("The document is still being saved. Retry when your editor finishes saving.")
        return count, after

    def observe(self, force=False):
        if self.session.status != "running":
            return
        if not force and self.file_signature() == self.signature:
            return
        count, signature = self.read_snapshot()
        delta = count - self.previous
        if delta:
            self.session.net += delta
            self.session.saves += 1
        self.previous = count
        self.signature = signature

    def pause(self):
        self.tick()
        self.observe(force=True)
        self.session.status = "paused"

    def resume(self):
        self.previous, self.signature = self.read_snapshot()
        self.last_tick = self.clock()
        self.session.status = "running"

    def finish(self):
        self.tick()
        self.observe(force=True)
        self.session.status = "done"
        return self.session


class Store:
    """Explicit schema is also the persistence privacy allowlist."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, started TEXT NOT NULL, mode TEXT NOT NULL,
            goal INTEGER NOT NULL, seconds REAL NOT NULL, net INTEGER NOT NULL,
            saves INTEGER NOT NULL, status TEXT NOT NULL)""")
        self.db.execute("UPDATE sessions SET status='interrupted' WHERE status IN ('running','paused')")
        self.db.commit()

    def save(self, session: Session):
        values = asdict(session)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO sessions VALUES (:id,:started,:mode,:goal,:seconds,:net,:saves,:status)", values)

    def history(self):
        return [Session(**dict(row)) for row in self.db.execute(
            "SELECT * FROM sessions WHERE status IN ('done','interrupted') ORDER BY started DESC")]

    def clear(self):
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE status IN ('done','interrupted')")
        self.db.execute("VACUUM")

    def close(self):
        self.db.close()
