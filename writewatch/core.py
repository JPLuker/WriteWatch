"""Content is read transiently. Only aggregate numbers leave the parser."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import re
import sqlite3
import time
import uuid
import zipfile

from defusedxml import ElementTree

MAX_BYTES = 16 * 1024 * 1024
WORDS = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)


class ScriptError(ValueError):
    pass


def word_count(path: Path) -> int:
    """Count body text only: no title page, notes, scene synopses or metadata."""
    try:
        if path.stat().st_size > MAX_BYTES:
            raise ScriptError("This file exceeds the 16 MB safety limit.")
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                info = archive.getinfo("document.xml")
                if info.file_size > MAX_BYTES:
                    raise ScriptError("The script exceeds the 16 MB safety limit.")
                data = archive.read(info)
        else:
            data = path.read_bytes()
        root = ElementTree.fromstring(data)
        # Normalize XML namespaces without retaining script content anywhere.
        for node in root.iter():
            node.tag = node.tag.split("}")[-1]
        if root.tag != "document" or root.find("paragraphs") is None:
            raise ScriptError("This is not a supported Fade In / OSF document.")
        count = 0
        for para in root.find("paragraphs").iter("para"):
            # Adjacent text runs may split a word; don't insert spaces between them.
            body = "".join("".join(node.itertext()) for node in para.findall("text"))
            count += len(WORDS.findall(body))
        return count
    except ScriptError:
        raise
    except Exception:
        # Never expose XML snippets, script text, or a private path in an error.
        raise ScriptError("Could not read the saved script. Save in Fade In, then retry.") from None


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
        if mode not in ("Writing", "Revision") or not 1 <= goal <= 100000:
            raise ValueError("Invalid session goal")
        return cls(uuid.uuid4().hex, datetime.now().astimezone().isoformat(), mode, goal)

    @property
    def progress(self):
        amount = max(0, self.net) if self.mode == "Writing" else self.seconds / 60
        return min(1.0, amount / self.goal)

    def summary(self):
        date = datetime.fromisoformat(self.started).strftime("%b %d, %Y")
        minutes, seconds = divmod(int(self.seconds), 60)
        goal = f"{self.goal:,} net words" if self.mode == "Writing" else f"{self.goal} minutes"
        heading = "Session complete" if self.status == "done" else "Interrupted session"
        return (f"WriteWatch · {date}\n{self.mode} · {heading}\n"
                f"Goal progress: {round(self.progress * 100)}%\n"
                f"Time: {minutes}m {seconds:02d}s · {self.net:+,} net words\n"
                f"Goal: {goal}\n#WriteWatch")


class Tracker:
    """Manual timer; paused edits are excluded on resume. No text snapshots."""
    def __init__(self, path: Path, mode: str, goal: int, clock=time.monotonic):
        self.path = path
        self.clock = clock
        self.previous = word_count(path)
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

    def observe(self):
        if self.session.status != "running":
            return
        count = word_count(self.path)
        delta = count - self.previous
        if delta:
            self.session.net += delta
            self.session.saves += 1
        self.previous = count

    def pause(self):
        self.tick()
        self.observe()
        self.session.status = "paused"

    def resume(self):
        self.previous = word_count(self.path)
        self.last_tick = self.clock()
        self.session.status = "running"

    def finish(self):
        self.tick()
        self.observe()
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
