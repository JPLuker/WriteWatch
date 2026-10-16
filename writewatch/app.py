from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

from PySide6.QtCore import Qt, QTimer, QStandardPaths, QLockFile
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QComboBox, QSpinBox, QFrame, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QPlainTextEdit, QAbstractItemView, QScrollArea, QCheckBox,
)
from . import __version__
from .core import ScriptError, Session, Store, Tracker
from .formats import file_filter, format_name

STYLE = """
QWidget { background: #10191b; color: #e7eeeb; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 14px; }
QMainWindow, QDialog { background: #10191b; }
QLabel#brand { font-size: 25px; font-weight: 700; color: #b5e3bf; }
QLabel#title { font-size: 32px; font-weight: 700; }
QLabel#muted { color: #a7bbb6; }
QLabel#eyebrow { color: #b5e3bf; font-size: 12px; font-weight: 700; }
QLabel#number { font-size: 38px; font-weight: 600; }
QLabel#timer { font-size: 64px; font-weight: 600; }
QFrame#panel { background: #192629; border: 1px solid #304043; border-radius: 16px; }
QFrame#panel QLabel { background: transparent; }
QPushButton { background: #26383a; border: 1px solid #435a59; border-radius: 8px; padding: 11px 18px; font-weight: 600; }
QPushButton:hover { background: #354b4c; }
QPushButton:pressed { background: #405c58; }
QPushButton#primary { background: #b5e3bf; color: #13291d; border: 0; }
QPushButton#primary:hover { background: #d0f0d7; }
QPushButton#primary:disabled, QPushButton:disabled { background: #202d2e; color: #657b76; border-color: #304043; }
QComboBox, QSpinBox, QPlainTextEdit { background: #192629; border: 1px solid #435a59; border-radius: 7px; padding: 9px; }
QComboBox QAbstractItemView { background: #26383a; selection-background-color: #405c58; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #10191b; color: #a7bbb6; padding: 13px 22px; margin-right: 8px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #b5e3bf; border-bottom: 2px solid #b5e3bf; }
QProgressBar { border: 0; background: #304043; border-radius: 5px; min-height: 10px; max-height: 10px; }
QProgressBar::chunk { background: #b5e3bf; border-radius: 5px; }
QTableWidget { background: #192629; border: 1px solid #304043; gridline-color: #304043; selection-background-color: #36574b; }
QHeaderView::section { background: #26383a; border: 0; padding: 11px; color: #b5c9c2; }
QCheckBox { spacing: 10px; }
QToolTip { background: #26383a; color: #e7eeeb; border: 1px solid #435a59; }
"""


def label(text, name=None):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(text)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        item.setObjectName("primary")
    item.clicked.connect(callback)
    return item


def icon():
    pix = QPixmap(128, 128)
    pix.fill(QColor("#10191b"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#b5e3bf"))
    p.drawRoundedRect(12, 12, 104, 104, 26, 26)
    p.setPen(QColor("#13291d"))
    p.setFont(QFont("DejaVu Sans", 49, QFont.Weight.Bold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    p.end()
    return QIcon(pix)


def card(session: Session) -> QPixmap:
    """Render only explicit public metrics. No filename or content input exists."""
    pix = QPixmap(1200, 720)
    pix.fill(QColor("#10191b"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#b5e3bf"))
    p.setFont(QFont("DejaVu Sans", 20, QFont.Weight.Bold))
    p.drawText(64, 75, "WRITEWATCH")
    p.setPen(QColor("#e7eeeb"))
    p.setFont(QFont("DejaVu Sans", 38, QFont.Weight.Bold))
    p.drawText(64, 165, "A little more of the story.")
    p.setFont(QFont("DejaVu Sans", 18))
    date = datetime.fromisoformat(session.started).strftime("%B %d, %Y")
    status = "Complete" if session.status == "done" else "Interrupted"
    p.drawText(64, 215, f"{session.mode} session  /  {date}  /  {status}")
    p.setPen(QColor("#e7eeeb"))
    p.setFont(QFont("DejaVu Sans", 39, QFont.Weight.Bold))
    minutes, seconds = divmod(int(session.seconds), 60)
    p.drawText(64, 465, f"{minutes}m {seconds:02d}s")
    p.drawText(640, 465, f"{session.net:+,}")
    p.setFont(QFont("DejaVu Sans", 17))
    p.setPen(QColor("#a7bbb6"))
    p.drawText(64, 510, "SESSION TIME")
    p.drawText(640, 510, "NET WORDS")
    goal_text = f"{session.goal_result}  /  {session.goal_label}" if session.goal else "A session for the sake of writing."
    p.drawText(64, 610, goal_text)
    p.setFont(QFont("DejaVu Sans", 13))
    p.drawText(64, 665, "Progress worth sharing. Story kept private.")
    p.end()
    return pix


class ShareDialog(QDialog):
    def __init__(self, session, parent=None, review=False):
        super().__init__(parent)
        self.setWindowTitle("Your session · WriteWatch")
        self.resize(620, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(label("Session review" if review else "That's a session.", "title"))
        if review:
            date = datetime.fromisoformat(session.started).astimezone().strftime("%A, %B %d, %Y · %I:%M %p")
            layout.addWidget(label(date, "muted"))
            panel = QFrame()
            panel.setObjectName("panel")
            details = QVBoxLayout(panel)
            details.setContentsMargins(20, 16, 20, 16)
            minutes, seconds = divmod(int(session.seconds), 60)
            state = "Completed" if session.status == "done" else "Interrupted — last saved checkpoint"
            for text in (f"{session.mode} · {state}", f"Session time: {minutes}m {seconds:02d}s",
                         f"Net words: {session.net:+,}", f"Goal: {session.goal_label}",
                         session.goal_result if session.goal else "You chose to write without a target."):
                item = label(text)
                item.setWordWrap(True)
                details.addWidget(item)
            layout.addWidget(panel)
            layout.addWidget(label("SHAREABLE SUMMARY", "eyebrow"))
        layout.addWidget(label("Copy your progress. Keep your story yours.", "muted"))
        self.text = QPlainTextEdit(session.summary())
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(180)
        layout.addWidget(self.text)
        row = QHBoxLayout()
        self.copy = button("Copy for writers group", self.copy_summary, True)
        row.addWidget(self.copy)
        row.addWidget(button("Save image…", lambda: self.save_image(session)))
        row.addWidget(button("Close", self.accept))
        layout.addLayout(row)

    def copy_summary(self):
        QApplication.clipboard().setText(self.text.toPlainText())
        self.copy.setText("Copied ✓")

    def save_image(self, session):
        path, _ = QFileDialog.getSaveFileName(self, "Save share card", "WriteWatch-session.png", "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            if not card(session).save(path, "PNG"):
                QMessageBox.warning(self, "Image not saved", "Choose a writable folder and try again.")


class Window(QMainWindow):
    def __init__(self, store, update_folder=None):
        super().__init__()
        self.store = store
        self.path = None
        self.tracker = None
        self.setWindowTitle(f"WriteWatch {__version__}")
        self.setWindowIcon(icon())
        self.resize(1000, 850)
        self.setMinimumSize(800, 700)
        base = QWidget()
        self.setCentralWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(32, 22, 32, 20)
        layout.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("WriteWatch", "brand"))
        top.addStretch()
        top.addWidget(label("YOUR WORDS STAY ON YOUR COMPUTER", "eyebrow"))
        layout.addLayout(top)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.build_session()
        self.build_history()
        self.build_formats()
        self.build_privacy()
        self.updates = None
        if update_folder is not None:
            from .update_ui import UpdatesPanel
            self.updates = UpdatesPanel(self, update_folder)
            self.tabs.addTab(self.updates, "Updates")
        layout.addWidget(label(f"Made by Joseph Luker   ·   v{__version__}", "muted"))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(2000)
        self.refresh_history()
        self.update_view()

    def build_session(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(label("Make time for your story.", "title"))
        description = label("Start a session, write in your favorite editor, then share your progress.", "muted")
        description.setWordWrap(True)
        layout.addWidget(description)
        row = QHBoxLayout()
        self.choose = button("Choose writing file…", self.pick)
        row.addWidget(self.choose)
        self.file_status = label("No document selected", "muted")
        row.addWidget(self.file_status, 1)
        layout.addLayout(row)
        options = QHBoxLayout()
        options.addWidget(label("Session"))
        self.mode = QComboBox()
        self.mode.addItems(["Writing", "Revision"])
        self.mode.setAccessibleName("Session type")
        self.mode.currentTextChanged.connect(self.mode_changed)
        options.addWidget(self.mode)
        options.addSpacing(18)
        options.addWidget(label("Goal"))
        self.goal = QSpinBox()
        self.goal.setRange(1, 100000)
        self.goal.setValue(500)
        self.goal.setSuffix(" net words")
        self.goal.setAccessibleName("Session goal")
        options.addWidget(self.goal)
        self.skip_goal = QCheckBox("Skip goal")
        self.skip_goal.setToolTip("Track time and words without a target for this session.")
        self.skip_goal.toggled.connect(lambda _: self.update_view())
        options.addWidget(self.skip_goal)
        options.addStretch()
        layout.addLayout(options)
        panel = QFrame()
        panel.setObjectName("panel")
        body = QVBoxLayout(panel)
        body.setContentsMargins(28, 22, 28, 24)
        self.state_label = label("READY WHEN YOU ARE", "eyebrow")
        body.addWidget(self.state_label)
        self.time_label = label("00:00", "timer")
        body.addWidget(self.time_label)
        row = QHBoxLayout()
        self.words = label("+0", "number")
        self.percent = label("0%", "number")
        for number, title in [(self.words, "NET WORDS"), (self.percent, "SESSION GOAL")]:
            col = QVBoxLayout()
            col.addWidget(number)
            col.addWidget(label(title, "muted"))
            row.addLayout(col)
        body.addLayout(row)
        body.addSpacing(14)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        body.addWidget(self.progress)
        layout.addWidget(panel)
        self.message = label("Save your document before starting. Progress updates whenever your editor saves this file.", "muted")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.start = button("Start session", self.begin, True)
        self.pause_button = button("Pause", self.pause_resume)
        self.done = button("Done — share progress", self.finish)
        row.addWidget(self.start)
        row.addWidget(self.pause_button)
        row.addWidget(self.done)
        layout.addLayout(row)
        note = label("Session time is a manual timer. Pause for breaks. Net words can be negative when editing.", "muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.tabs.addTab(page, "Session")

    def build_history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(label("Every session adds up.", "title"))
        self.totals = label("", "muted")
        layout.addWidget(self.totals)
        filters = QHBoxLayout()
        self.history_period = QComboBox()
        self.history_period.addItems(["All time", "Last 7 days", "Last 30 days"])
        self.history_period.setAccessibleName("History date range")
        self.history_mode = QComboBox()
        self.history_mode.addItems(["All sessions", "Writing", "Revision"])
        self.history_mode.setAccessibleName("History session type")
        for control in (self.history_period, self.history_mode):
            control.currentTextChanged.connect(self.refresh_history)
            filters.addWidget(control)
        filters.addStretch()
        layout.addLayout(filters)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Started", "Session", "Time", "Net words", "Goal", "Result"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.share_selected)
        layout.addWidget(self.table)
        self.empty = label("Your finished sessions will appear here. Start with a few minutes.", "muted")
        layout.addWidget(self.empty)
        row = QHBoxLayout()
        self.review_button = button("Review session", self.share_selected, True)
        row.addWidget(self.review_button)
        row.addStretch()
        row.addWidget(button("Delete history…", self.clear_history))
        layout.addLayout(row)
        self.tabs.addTab(page, "History")

    def build_formats(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 20, 12, 12)
        layout.setSpacing(16)
        layout.addWidget(label("One workflow. Many editors.", "title"))
        for title, detail in [
            ("Screenplays", "Fade In (.fadein, .osf), Final Draft (.fdx), and Fountain (.fountain). WriterDuet, WriterSolo and other screenplay apps can supply a local FDX or Fountain export."),
            ("Documents", "Word, LibreOffice, OpenOffice, ONLYOFFICE and WPS through .docx, .odt, .fodt or .rtf. AbiWord through .abw and .zabw. Track the format your editor actually saves."),
            ("Notes & prose", "Obsidian, Typora, MarkText, Zettlr, iA Writer and other Markdown editors through .md, .markdown or .mdown. Plain-text editors through .txt or .text. UTF-8 and BOM-marked UTF-16 are supported."),
            ("Exports & publishing", "HTML (.html, .htm, .xhtml), EPUB (.epub) and selectable-text PDF (.pdf). EPUB editors can be watched directly. PDFs include extracted headers, footers and page numbers; scanned PDFs need OCR elsewhere."),
            ("Cloud apps and project formats", "Google Docs, Notion, Scrivener, Ulysses, Pages and browser-based editors need an export to a supported local format. WriteWatch cannot see cloud-only edits, .gdoc shortcuts or proprietary project contents. Re-export to the same selected path to update progress."),
            ("What gets counted", "DOCX body text (including tables and inserted revisions), excluding deleted revisions and separate comments/headers/footers. ODT excludes annotations, tracked-change history and footnotes. Markdown excludes front matter, comments and link destinations; code text counts. Fountain excludes title metadata, notes, boneyards, section headings and synopses. EPUB counts linear text chapters. RTF counts extracted text. HTML strips markup, scripts and styles but does not interpret CSS visibility."),
        ]:
            layout.addWidget(label(title, "eyebrow"))
            text = label(detail, "muted")
            text.setWordWrap(True)
            layout.addWidget(text)
        layout.addStretch()
        scroll.setWidget(page)
        self.tabs.addTab(scroll, "Formats & apps")

    def build_privacy(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(label("Your story stays with you.", "title"))
        for title, text in [
            ("Private by design", "No accounts, analytics, uploads, keyboard recording or automatic posts. The selected document is opened read-only on this computer."),
            ("Optional updates", "Automatic updates contact GitHub for release metadata and app downloads. GitHub receives normal connection information such as your IP address. No document or session data is sent. Turn automatic checks off in Updates."),
            ("Numbers, not drafts", "History stores session date, type, goal, duration, net word change, count-changing observations and completion status. It does not store document text, titles, filenames or paths."),
            ("An honest measure", "Net words compare saved word counts. Equal-length rewrites do not increase the number. Counting rules vary by format; see Formats & apps. Counts can differ from your editor. Cloud-only documents need a refreshed local export."),
            ("You control the clock", "Start / Pause / Done controls session time. It does not detect typing or focus. Edits saved while paused are excluded when you resume. A long system suspension pauses the timer. Save before pausing or finishing."),
            ("Share on your terms", "Copy sends only the displayed summary to your system clipboard. Save image exports the metrics shown on the card. Your clipboard manager or clipboard sync may retain copied summaries."),
        ]:
            layout.addWidget(label(title, "eyebrow"))
            detail = label(text, "muted")
            detail.setWordWrap(True)
            layout.addWidget(detail)
        layout.addStretch()
        self.tabs.addTab(page, "Privacy & how it works")

    def mode_changed(self, mode):
        self.goal.setMaximum(1440 if mode == "Revision" else 100000)
        self.goal.setSuffix(" minutes" if mode == "Revision" else " net words")
        self.goal.setValue(30 if mode == "Revision" else 500)

    def pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a saved writing file", "", file_filter())
        if path:
            self.path = Path(path)
            self.file_status.setText(format_name(self.path) + " selected · filename kept private")
            self.update_view()

    def persist(self):
        if not self.tracker:
            return True
        try:
            self.store.save(self.tracker.session)
            return True
        except Exception:
            self.tracker.session.status = "paused"
            self.message.setText("History could not be saved. Session paused. Free disk space, then retry.")
            return False

    def begin(self):
        if not self.path:
            return
        try:
            self.tracker = Tracker(self.path, self.mode.currentText(), 0 if self.skip_goal.isChecked() else self.goal.value())
            if self.persist():
                self.message.setText("Session running. Save in your editor to update your progress.")
        except ScriptError as error:
            QMessageBox.warning(self, "Document unavailable", str(error))
        self.update_view()

    def poll(self):
        if not self.tracker:
            return
        self.tracker.tick()
        try:
            self.tracker.observe()
            if self.tracker.session.status == "running":
                self.message.setText("Reading saved progress every 2 seconds · save in your editor before finishing.")
            else:
                self.message.setText("Paused. Resume when ready; changes saved during this pause are excluded.")
        except ScriptError as error:
            self.message.setText(str(error) + " Timer continues; last good count retained.")
        self.persist()
        self.update_view()

    def pause_resume(self):
        if not self.tracker:
            return
        try:
            if self.tracker.session.status == "paused":
                self.tracker.resume()
            else:
                self.tracker.pause()
            self.persist()
        except ScriptError as error:
            QMessageBox.warning(self, "Save and retry", str(error))
        self.update_view()

    def finish(self):
        if not self.tracker:
            return
        try:
            session = self.tracker.finish()
            if not self.persist():
                self.update_view()
                return
        except ScriptError as error:
            QMessageBox.warning(self, "Save and retry", str(error) + " Your session remains open.")
            return
        self.tracker = None
        self.refresh_history()
        self.update_view()
        self.message.setText("Session saved. Ready for the next one.")
        ShareDialog(session, self).exec()

    def update_view(self):
        active = self.tracker is not None
        for widget in (self.choose, self.mode, self.skip_goal):
            widget.setEnabled(not active)
        self.goal.setEnabled(not active and not self.skip_goal.isChecked())
        self.start.setEnabled(not active and self.path is not None)
        self.pause_button.setEnabled(active)
        self.done.setEnabled(active)
        session = self.tracker.session if active else None
        paused = active and session.status == "paused"
        self.pause_button.setText("Resume" if paused else "Pause")
        self.state_label.setText("PAUSED" if paused else "SESSION IN PROGRESS" if active else "READY WHEN YOU ARE")
        seconds = int(session.seconds) if active else 0
        minutes, seconds = divmod(seconds, 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        self.words.setText(f"{session.net if active else 0:+,}")
        percent = round(session.progress * 100) if active else 0
        has_goal = bool(session.goal) if active else not self.skip_goal.isChecked()
        self.percent.setText(f"{percent}%" if has_goal else "—")
        self.percent.setToolTip("No goal set" if not has_goal else "Progress toward this session's goal")
        self.progress.setVisible(has_goal)
        self.progress.setValue(percent)

    def refresh_history(self, *_):
        all_sessions = self.store.history()
        today = datetime.now().date()
        period = self.history_period.currentText()
        days_back = 7 if period == "Last 7 days" else 30 if period == "Last 30 days" else None
        mode = self.history_mode.currentText()
        self.history = [s for s in all_sessions
                        if (mode == "All sessions" or s.mode == mode)
                        and (days_back is None or today - timedelta(days=days_back - 1)
                             <= datetime.fromisoformat(s.started).astimezone().date() <= today)]
        self.table.setRowCount(len(self.history))
        for row, session in enumerate(self.history):
            date = datetime.fromisoformat(session.started).astimezone().strftime("%Y-%m-%d %H:%M")
            minutes, seconds = divmod(int(session.seconds), 60)
            values = [date, session.mode + (" (interrupted)" if session.status == "interrupted" else ""),
                      f"{minutes}m {seconds:02d}s", f"{session.net:+,}", session.goal_label, session.goal_result]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.empty.setText("No sessions match these filters." if all_sessions else "Your finished sessions will appear here. Start with a few minutes.")
        self.empty.setVisible(not self.history)
        self.review_button.setEnabled(bool(self.history))
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week = [s for s in all_sessions if week_start <= datetime.fromisoformat(s.started).astimezone().date() <= today]
        days = {datetime.fromisoformat(s.started).astimezone().date() for s in all_sessions if s.status == "done"}
        day = today if today in days else today - timedelta(days=1)
        streak = 0
        while day in days:
            streak += 1
            day -= timedelta(days=1)
        self.totals.setText(f"This week: {len(week)} sessions · {int(sum(s.seconds for s in week) / 60)} minutes · "
                            f"{sum(s.net for s in week):+,} net words     |     {streak}-day streak")
        if self.history:
            self.table.selectRow(0)

    def share_selected(self, *_):
        row = self.table.currentRow()
        if 0 <= row < len(self.history):
            ShareDialog(self.history[row], self, review=True).exec()

    def clear_history(self):
        if QMessageBox.question(self, "Delete history?", "Delete all completed and interrupted session statistics? This cannot be undone.") == QMessageBox.StandardButton.Yes:
            try:
                self.store.clear()
                self.refresh_history()
            except Exception:
                QMessageBox.warning(self, "History unavailable", "Could not update history. Check available disk space.")

    def closeEvent(self, event):
        if self.updates and not self.updates.allow_close():
            event.ignore()
            return
        if self.tracker:
            response = QMessageBox.question(self, "Session in progress", "Close and keep this as an interrupted session? Choose No to return and use Done to finish.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if response != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.tracker.tick()
            try:
                self.tracker.observe()
            except ScriptError:
                pass
            self.tracker.session.status = "interrupted"
            if not self.persist():
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WriteWatch")
    app.setOrganizationName("WriteWatch")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(icon())
    folder = Path(os.environ.get("WRITEWATCH_DATA_DIR") or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    folder.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(folder / "writewatch.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, "WriteWatch is open", "WriteWatch is already running for this user.")
        return 0
    try:
        store = Store(folder / "history.sqlite3")
    except Exception:
        QMessageBox.critical(None, "History unavailable", "WriteWatch could not open local history. Check disk space and folder permissions.")
        return 1
    window = Window(store, update_folder=None if os.environ.get("WRITEWATCH_DISABLE_UPDATES") == "1" else folder)
    window.show()
    result = app.exec()
    store.close()
    lock.unlock()
    return result
