from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

from PySide6.QtCore import Qt, QTimer, QStandardPaths, QLockFile, QSettings, QUrl
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QComboBox, QSpinBox, QFrame, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QPlainTextEdit, QAbstractItemView, QScrollArea, QCheckBox, QToolButton, QMenu, QToolBox, QDoubleSpinBox,
)
from . import __version__
from .core import ScriptError, Session, Store, Tracker
from .formats import file_filter, format_name
from .controls import SegmentedChoice, GoalChoice

from .theme import AmbientCanvas, apply_theme, stylesheet, DARK, FloatingTabs, nav_icon
STYLE = stylesheet(True)



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
    pix.fill(QColor(DARK["canvas"]))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(DARK["accent"]))
    p.drawRoundedRect(12, 12, 104, 104, 26, 26)
    p.setPen(QColor(DARK["onaccent"]))
    p.setFont(QFont(QApplication.font().family(), 49, QFont.Weight.DemiBold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    p.end()
    return QIcon(pix)


def card(session: Session) -> QPixmap:
    """Render only explicit public metrics. No filename or content input exists."""
    pix = QPixmap(1200, 720)
    pix.fill(QColor(DARK["canvas"]))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(DARK["accent"]))
    p.setFont(QFont(QApplication.font().family(), 20, QFont.Weight.DemiBold))
    p.drawText(64, 75, "WriteWatch")
    p.setPen(QColor(DARK["text"]))
    p.setFont(QFont(QApplication.font().family(), 38, QFont.Weight.DemiBold))
    p.drawText(64, 165, "Session complete" if session.status == "done" else "Session interrupted")
    p.setFont(QFont(QApplication.font().family(), 18))
    date = datetime.fromisoformat(session.started).strftime("%B %d, %Y")
    status = "Complete" if session.status == "done" else "Interrupted"
    p.drawText(64, 215, f"{session.mode} session  /  {date}  /  {status}")
    p.setPen(QColor(DARK["text"]))
    p.setFont(QFont(QApplication.font().family(), 39, QFont.Weight.DemiBold))
    minutes, seconds = divmod(int(session.seconds), 60)
    p.drawText(64, 465, f"{minutes}m {seconds:02d}s")
    p.drawText(640, 465, f"{session.page_count:,.1f}" if session.unit in ("pages", "estimated_pages") else f"{session.net:+,}")
    p.setFont(QFont(QApplication.font().family(), 17))
    p.setPen(QColor(DARK["secondary"]))
    p.drawText(64, 510, "Session time")
    p.drawText(640, 510, {"pages": "Pages (self-reported)", "estimated_pages": "Estimated pages"}.get(session.unit, "Net words"))
    goal_text = f"{session.goal_result}  /  {session.goal_label}" if session.goal else "No goal set"
    if session.mode == "Revision" and session.revision_metrics:
        p.drawText(64, 560, f"{session.added:,} words added  /  {session.removed:,} words removed")
    p.drawText(64, 610, goal_text)
    p.setFont(QFont(QApplication.font().family(), 13))
    p.end()
    return pix


class ShareDialog(QDialog):
    def __init__(self, session, parent=None, review=False):
        super().__init__(parent)
        self.setWindowTitle("Your session · WriteWatch")
        self.resize(620, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(label("Session review" if review else "Session complete", "title"))
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
                         session.goal_result if session.goal else "No goal set"):
                item = label(text)
                item.setWordWrap(True)
                details.addWidget(item)
            details_toggle = QCheckBox("Session details")
            details_toggle.toggled.connect(panel.setVisible)
            panel.hide()
            layout.addWidget(details_toggle)
            layout.addWidget(panel)
        self.text = QPlainTextEdit(session.summary())
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(180)
        layout.addWidget(self.text)
        row = QHBoxLayout()
        self.copy = button("Copy", self.copy_summary, True)
        row.addWidget(self.copy)
        row.addWidget(button("Save image…", lambda: self.save_image(session)))
        row.addWidget(button("Close", self.accept))
        layout.addLayout(row)

    def copy_summary(self):
        QApplication.clipboard().setText(self.text.toPlainText())
        self.copy.setText("Copied")

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
        self.recent_settings = QSettings(str(store.path.parent / "recents.ini"), QSettings.Format.IniFormat)
        self.recent_settings.setValue("format_version", 1)
        self.path = None
        self.tracker = None
        self.setWindowTitle("WriteWatch")
        self.setWindowIcon(icon())
        self.resize(1000, 850)
        self.setMinimumSize(720, 540)
        base = AmbientCanvas()
        self.setCentralWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("WriteWatch", "brand"))
        top.addStretch()
        self.menu_button = QToolButton()
        self.menu_button.setIcon(nav_icon(5))
        self.menu_button.setAccessibleName("Navigation menu")
        self.menu_button.setToolTip("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.navigation = QMenu(self.menu_button)
        self.menu_button.setMenu(self.navigation)
        top.addWidget(self.menu_button)
        layout.addLayout(top)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs)
        self.build_session()
        self.build_history()
        self.build_formats()
        self.build_privacy()
        self.about_pages = [self.tabs.widget(2), self.tabs.widget(3)]
        self.tabs.removeTab(3)
        self.tabs.removeTab(2)
        self.build_settings(update_folder)
        for index, title in enumerate(("Session", "History", "Settings")):
            action = self.navigation.addAction(title)
            action.triggered.connect(lambda checked=False, i=index: self.tabs.setCurrentIndex(i))
        for index in range(self.tabs.count()):
            self.tabs.setTabIcon(index, nav_icon(index))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(2000)
        self.refresh_history()
        self.update_view()

    def add_scroll_tab(self, page, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        if title in ('Session', 'Settings', 'Privacy'):
            page.setMaximumWidth(720)
            scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.tabs.addTab(scroll, title)

    def build_settings(self, folder):
        # FOCAL: available update action. Appearance stays neutral.
        self.preferences = QSettings(str(Path(folder) / "appearance.ini"), QSettings.Format.IniFormat) if folder else None
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 24, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(label("Appearance", "section"))
        row = QHBoxLayout()
        row.addWidget(label("Theme"))
        self.theme_choice = QComboBox()
        self.theme_choice.addItems(["System", "Light", "Dark"])
        self.theme_choice.setAccessibleName("Theme")
        self.theme_choice.setCurrentText(self.preferences.value("theme", "System") if self.preferences else "System")
        row.addWidget(self.theme_choice)
        row.addStretch()
        layout.addLayout(row)
        self.ambient_choice = QCheckBox("Ambient background")
        self.ambient_choice.setChecked(self.preferences.value("ambient", True, type=bool) if self.preferences else True)
        layout.addWidget(self.ambient_choice)
        self.theme_choice.currentTextChanged.connect(self.change_appearance)
        self.ambient_choice.toggled.connect(self.change_appearance)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.change_appearance)
        self.updates = None
        from .updates import updates_disabled
        if folder is not None and not updates_disabled():
            from .update_ui import UpdatesPanel
            self.updates = UpdatesPanel(self, folder)
            layout.addWidget(self.updates)
        layout.addWidget(label("Files", "section"))
        self.remember_files = QCheckBox("Remember recent files")
        self.remember_files.setChecked(self.recent_settings.value("remember", True, type=bool))
        self.remember_files.toggled.connect(self.set_remember_files)
        layout.addWidget(self.remember_files)
        layout.addWidget(button("Clear recent files", self.clear_recents))
        layout.addWidget(label("Data & storage", "section"))
        layout.addWidget(button("Export everything…", self.export_data))
        layout.addWidget(button("Import backup…", self.import_data))
        layout.addWidget(button("Open data folder", self.open_data_folder))
        layout.addWidget(button("Clear update downloads and logs", self.clear_update_cache))
        delete_data = button("Delete all app data…", self.delete_all_data)
        delete_data.setObjectName("destructive")
        layout.addWidget(delete_data)
        layout.addStretch()
        layout.addWidget(button("About WriteWatch", self.show_about))
        self.add_scroll_tab(page, "Settings")
        self.settings_tab = self.tabs.widget(self.tabs.count() - 1)
        if folder is not None:
            self.change_appearance()

    def data_ready(self):
        if self.tracker:
            QMessageBox.information(self, "Finish your session first", "Finish your session before managing app data.")
            return False
        if self.updates and self.updates.worker and self.updates.worker.isRunning():
            QMessageBox.information(self, "Update in progress", "Wait for the update check or cancel it before managing app data.")
            return False
        return True

    def export_preferences(self):
        updates = QSettings(str(self.store.path.parent / "updates.ini"), QSettings.Format.IniFormat)
        return dict(theme=self.theme_choice.currentText(), ambient=self.ambient_choice.isChecked(),
                    remember=self.remember_files.isChecked(), recents=self.recent_files(),
                    automatic_updates=updates.value("automatic", True, type=bool),
                    update_channel=updates.value("channel", "Stable"))

    def export_data(self):
        if not self.data_ready():
            return
        from .data import backup_payload, write_backup
        destination = str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)) / "WriteWatch-backup.json")
        path, _ = QFileDialog.getSaveFileName(self, "Export history, settings and recent-file paths", destination, "JSON backup (*.json)")
        if not path:
            return
        if not path.lower().endswith('.json'):
            path += '.json'
        try:
            write_backup(path, backup_payload(self.store, self.export_preferences()))
        except (OSError, ValueError, TypeError):
            QMessageBox.warning(self, "Export failed", "Could not save the backup. Check the destination and free space.")
            return
        QMessageBox.information(self, "Backup saved", "History, settings and recent-file paths were exported. Document contents are not included.")

    def import_data(self):
        if not self.data_ready():
            return
        from .data import read_backup, merge_sessions
        path, _ = QFileDialog.getOpenFileName(self, "Import WriteWatch backup", "", "JSON backup (*.json)")
        if not path:
            return
        try:
            payload = read_backup(path)
        except (OSError, ValueError):
            QMessageBox.warning(self, "Invalid backup", "This backup could not be read or validated. Existing data is unchanged.")
            return
        choice = QMessageBox.question(self, "Import backup?", f"Import {len(payload['sessions'])} sessions and replace settings and recent files? Existing session IDs will be kept.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            added = merge_sessions(self.store, payload)
        except Exception:
            QMessageBox.warning(self, "Import failed", "History could not be imported. Existing data is unchanged.")
            return
        prefs = payload['settings']
        self.theme_choice.setCurrentText(prefs['theme'])
        self.ambient_choice.setChecked(prefs['ambient'])
        self.remember_files.setChecked(prefs['remember'])
        self.recent_settings.setValue("files", prefs['recents'] if prefs['remember'] else [])
        settings = QSettings(str(self.store.path.parent / "updates.ini"), QSettings.Format.IniFormat)
        settings.setValue("automatic", prefs['automatic_updates'])
        settings.setValue("channel", prefs.get("update_channel", "Stable"))
        if self.updates:
            self.updates.automatic.setChecked(prefs['automatic_updates'])
            self.updates.channel.setCurrentText(prefs.get('update_channel', 'Stable'))
        self.change_appearance()
        saved = True
        for item in (self.preferences, self.recent_settings, settings):
            if item is not None:
                item.sync()
                saved = saved and item.status() == QSettings.Status.NoError
        self.refresh_history()
        if saved:
            QMessageBox.information(self, "Backup imported", f"Imported {added} new sessions. Existing sessions were kept.")
        else:
            QMessageBox.warning(self, "Settings could not be saved", "History was imported, but some settings could not be saved. Check folder permissions and free space.")

    def open_data_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path.parent)))

    def clear_update_cache(self):
        if not self.data_ready():
            return
        from .data import clear_cache
        try:
            clear_cache(self.store.path.parent)
        except OSError:
            QMessageBox.warning(self, "Could not clear downloads", "Some update files could not be removed. Check folder permissions.")
            return
        if self.updates:
            self.updates.pending = None
            self.updates.restart.setEnabled(False)
            self.updates.restart.setObjectName("")
            self.updates.restart.style().unpolish(self.updates.restart)
            self.updates.restart.style().polish(self.updates.restart)
            self.updates.check.setEnabled(bool(self.updates.installation))
            self.updates.status.setText("Update downloads and logs cleared.")
            self.tabs.setTabText(self.tabs.indexOf(self.settings_tab), "Settings")
            self.menu_button.setText("")
            self.menu_button.setToolTip("Menu")
            self.menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        QMessageBox.information(self, "Downloads cleared", "Update downloads and logs were removed. Your history and settings were kept.")

    def copy_diagnostics(self):
        import platform
        text = (f"WriteWatch {__version__}\nOS: {platform.system()} {platform.release()}\n"
                f"Architecture: {platform.machine()}\nHistory schema: 2\n"
                f"Data folder: {self.store.path.parent}\nUpdate log: {self.store.path.parent / 'updates' / 'last-update.log'}")
        QApplication.clipboard().setText(text)

    def delete_all_data(self):
        if not self.data_ready():
            return
        choice = QMessageBox.question(self, "Delete all app data?", "Permanently delete history, settings, recent files, migration backups, update downloads and logs, then quit? Documents and exported backups are kept. This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if choice != QMessageBox.StandardButton.Yes:
            return
        from .data import delete_owned_data
        self.timer.stop()
        if self.updates:
            self.updates.timer.stop()
            self.updates.automatic.setChecked(False)
        for item in (self.preferences, self.recent_settings, self.updates.settings if self.updates else None):
            if item is not None:
                item.clear()
                item.sync()
        self.store.close()
        try:
            delete_owned_data(self.store.path.parent)
        except OSError:
            QMessageBox.warning(self, "Some app data remains", "Some files could not be deleted. WriteWatch will quit. Remove remaining app files from the data folder manually.")
        self.close()
        QApplication.instance().quit()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About WriteWatch")
        dialog.resize(640, 540)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(label(f"WriteWatch {__version__}", "section"))
        layout.addWidget(label("Made by Joseph Luker", "muted"))
        sections = QToolBox()
        for page, title in zip(self.about_pages, ("Formats", "Privacy")):
            sections.addItem(page, title)
        layout.addWidget(sections)
        layout.addWidget(button("Copy diagnostic info", self.copy_diagnostics))
        layout.addWidget(button("Close", dialog.accept))
        dialog.exec()
        for page in self.about_pages:
            page.setParent(self)
            page.hide()
        dialog.deleteLater()

    def change_appearance(self, *_):
        choice, ambient = self.theme_choice.currentText(), self.ambient_choice.isChecked()
        if self.preferences:
            self.preferences.setValue("theme", choice)
            self.preferences.setValue("ambient", ambient)
        apply_theme(choice, ambient)
        self.centralWidget().update()
        self.menu_button.setIcon(nav_icon(5))
        for index in range(self.tabs.count()):
            self.tabs.setTabIcon(index, nav_icon(index))

    def build_session(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        # FOCAL: Open file before a session; timer during an active session.
        self.setup_panel = QFrame()
        self.setup_panel.setObjectName("panel")
        setup = QVBoxLayout(self.setup_panel)
        setup.setContentsMargins(24, 24, 24, 24)
        setup.setSpacing(16)
        setup.addWidget(label("New session", "title"))
        setup.addWidget(label("Writing file", "eyebrow"))
        row = QHBoxLayout()
        self.choose = button("Open file…", self.pick, True)
        row.addWidget(self.choose)
        self.file_status = label("No document selected", "muted")
        self.file_status.setWordWrap(True)
        row.addWidget(self.file_status, 1)
        setup.addLayout(row)
        self.mode = SegmentedChoice(["Writing", "Revision"])
        self.mode.setAccessibleName("Session type")
        self.mode.currentTextChanged.connect(self.mode_changed)
        layout.addWidget(self.mode)
        self.goal_dialog = QDialog(self)
        self.goal_dialog.setWindowTitle("Goal settings")
        self.goal_dialog.resize(440, 240)
        goal_settings = QVBoxLayout(self.goal_dialog)
        goal_settings.setContentsMargins(24, 24, 24, 24)
        goal_settings.setSpacing(16)
        goal_settings.addWidget(label("Session goal", "section"))
        self.goal = QSpinBox()
        self.goal.setRange(1, 100000)
        self.goal.setValue(500)
        self.goal.setSuffix(" net words")
        self.goal.setAccessibleName("Session goal")
        self.goal.setMaximumWidth(200)
        self.skip_goal = GoalChoice()
        self.skip_goal.toggled.connect(lambda _: self.update_view())
        goal_settings.addWidget(self.skip_goal)
        self.goal_unit = SegmentedChoice(["Words", "Pages", "Minutes"])
        self.goal_unit.setAccessibleName("Goal unit")
        goal_settings.addWidget(self.goal_unit)
        self.page_method = SegmentedChoice(["Enter pages", "Estimate"])
        self.page_method.setAccessibleName("Page measurement")
        goal_settings.addWidget(self.page_method)
        self.page_rate = QSpinBox()
        self.page_rate.setRange(1, 2000)
        self.page_rate.setValue(250)
        self.page_rate.setSuffix(" words per page")
        self.page_rate.setAccessibleName("Words per estimated page")
        goal_settings.addWidget(self.page_rate)
        self.page_hint = label("Estimates use word count, not editor pagination.", "muted")
        self.page_hint.setWordWrap(True)
        goal_settings.addWidget(self.page_hint)
        self.goal_row = QWidget()
        goal_layout = QHBoxLayout(self.goal_row)
        goal_layout.setContentsMargins(0, 0, 0, 0)
        goal_layout.addWidget(label("Target", "muted"))
        goal_layout.addWidget(self.goal)
        goal_layout.addStretch()
        goal_settings.addWidget(self.goal_row)
        dialog_actions = QHBoxLayout()
        dialog_actions.addStretch()
        dialog_actions.addWidget(button("Cancel", self.goal_dialog.reject))
        dialog_actions.addWidget(button("Save goal", self.goal_dialog.accept, True))
        goal_settings.addLayout(dialog_actions)
        setup.addSpacing(8)
        actions = QHBoxLayout()
        self.goal_settings_button = button("Goal settings", self.edit_goal)
        # Goal settings has one home, below the session panel.
        actions.addStretch()
        self.start = button("Start session", self.begin, True)
        self.start.hide()  # Kept as an internal entry point; selecting a file starts tracking.
        setup.addLayout(actions)
        layout.addWidget(self.setup_panel)
        panel = QFrame()
        self.active_panel = panel
        panel.setObjectName("panel")
        body = QVBoxLayout(panel)
        body.setContentsMargins(24, 24, 24, 24)
        self.state_label = label("Ready", "eyebrow")
        body.addWidget(self.state_label)
        self.time_label = label("00:00", "timer")
        body.addWidget(self.time_label)
        row = QHBoxLayout()
        self.words = label("+0", "number")
        self.percent = label("0%", "number")
        self.goal_caption = label("Goal", "muted")
        self.words_caption = label("Net words", "muted")
        for number, title in [(self.words, "Net words"), (self.percent, "Goal")]:
            col = QVBoxLayout()
            col.addWidget(number)
            col.addWidget(self.goal_caption if number is self.percent else self.words_caption)
            row.addLayout(col)
        body.addLayout(row)
        body.addSpacing(16)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        body.addWidget(self.progress)
        self.pages_row = QWidget()
        pages_layout = QHBoxLayout(self.pages_row)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.addWidget(label("Pages completed"))
        self.pages_done = QDoubleSpinBox()
        self.pages_done.setRange(0, 100000)
        self.pages_done.setDecimals(1)
        self.pages_done.setSingleStep(0.5)
        self.pages_done.setAccessibleName("Pages completed, self-reported")
        self.pages_done.valueChanged.connect(self.record_pages)
        pages_layout.addWidget(self.pages_done)
        body.addWidget(self.pages_row)
        self.revision_counts = label("", "muted")
        self.revision_counts.setWordWrap(True)
        self.revision_counts.setToolTip("Cumulative word additions and removals between observed saves. Moving words and punctuation-only edits are not counted.")
        body.addWidget(self.revision_counts)
        layout.addWidget(panel)
        self.message = label("Save in your editor to update progress.", "muted")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.pause_button = button("Pause", self.pause_resume)
        self.done = button("Finish session", self.finish)
        row.addWidget(self.goal_settings_button)
        row.addStretch()
        row.addWidget(self.pause_button)
        row.addWidget(self.done)
        layout.addLayout(row)
        layout.addStretch()
        self.goal_unit.currentTextChanged.connect(self.goal_unit_changed)
        self.page_method.currentTextChanged.connect(lambda _: self.update_view())
        self.add_scroll_tab(page, "Session")

    def selected_goal_unit(self):
        if self.goal_unit.currentText() == "Pages":
            return "estimated_pages" if self.page_method.currentText() == "Estimate" else "pages"
        return self.goal_unit.currentText().lower()

    def goal_unit_changed(self, unit):
        self.goal.setMaximum(1440 if unit == "Minutes" else 100000)
        self.goal.setSuffix({"Words": " net words", "Pages": " pages", "Minutes": " minutes"}[unit])
        self.goal.setValue({"Words": 500, "Pages": 5, "Minutes": 30}[unit])
        self.update_view()

    def apply_goal(self):
        if self.tracker:
            session = self.tracker.session
            session.goal = 0 if self.skip_goal.isChecked() else self.goal.value()
            session.goal_unit = self.selected_goal_unit()
            session.words_per_page = self.page_rate.value()
            self.persist()

    def record_pages(self, value):
        if self.tracker:
            self.tracker.session.pages = value
            self.persist()
            self.update_view()

    def edit_goal(self):
        previous = (self.skip_goal.isChecked(), self.goal.value(), self.goal_unit.currentText(),
                    self.page_method.currentText(), self.page_rate.value())
        if self.goal_dialog.exec() != QDialog.DialogCode.Accepted:
            self.skip_goal.setChecked(previous[0])
            self.goal_unit.setCurrentText(previous[2])
            self.goal.setValue(previous[1])
            self.page_method.setCurrentText(previous[3])
            self.page_rate.setValue(previous[4])
        else:
            self.apply_goal()
        self.update_view()

    def build_history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
         # FOCAL: session history; goal details live in the review dialog.
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
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        self.table.setColumnHidden(4, True)
        self.table.setColumnHidden(5, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.share_selected)
        layout.addWidget(self.table)
        self.empty = label("No sessions yet", "muted")
        layout.addWidget(self.empty)
        row = QHBoxLayout()
        self.review_button = button("Review session", self.share_selected, True)
        row.addWidget(self.review_button)
        row.addStretch()
        delete = button("Delete history…", self.clear_history)
        delete.setObjectName("destructive")
        row.addWidget(delete)
        layout.addLayout(row)
        self.tabs.addTab(page, "History")

    def help_section(self, layout, title, detail):
        heading = QToolButton()
        heading.setText(title)
        heading.setCheckable(True)
        heading.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        heading.setArrowType(Qt.ArrowType.RightArrow)
        text = label(detail, "muted")
        text.setWordWrap(True)
        text.hide()
        def expand(checked):
            text.setVisible(checked)
            heading.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        heading.toggled.connect(expand)
        layout.addWidget(heading)
        layout.addWidget(text)

    def build_formats(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 20, 12, 12)
        layout.setSpacing(16)
        layout.addWidget(label("Supported formats", "title"))
        for title, detail in [
            ("Screenplays", "Fade In (.fadein, .osf), Final Draft (.fdx), and Fountain (.fountain). WriterDuet, WriterSolo and other screenplay apps can supply a local FDX or Fountain export."),
            ("Documents", "Word, LibreOffice, OpenOffice, ONLYOFFICE and WPS through .docx, .odt, .fodt or .rtf. AbiWord through .abw and .zabw. Track the format your editor actually saves."),
            ("Notes & prose", "Obsidian, Typora, MarkText, Zettlr, iA Writer and other Markdown editors through .md, .markdown or .mdown. Plain-text editors through .txt or .text. UTF-8 and BOM-marked UTF-16 are supported."),
            ("Exports & publishing", "HTML (.html, .htm, .xhtml), EPUB (.epub) and selectable-text PDF (.pdf). EPUB editors can be watched directly. PDFs include extracted headers, footers and page numbers; scanned PDFs need OCR elsewhere."),
            ("Cloud apps and project formats", "Google Docs, Notion, Scrivener, Ulysses, Pages and browser-based editors need an export to a supported local format. WriteWatch cannot see cloud-only edits, .gdoc shortcuts or proprietary project contents. Re-export to the same selected path to update progress."),
            ("What gets counted", "DOCX body text (including tables and inserted revisions), excluding deleted revisions and separate comments/headers/footers. ODT excludes annotations, tracked-change history and footnotes. Markdown excludes front matter, comments and link destinations; code text counts. Fountain excludes title metadata, notes, boneyards, section headings and synopses. EPUB counts linear text chapters. RTF counts extracted text. HTML strips markup, scripts and styles but does not interpret CSS visibility."),
        ]:
            self.help_section(layout, title, detail)
        layout.addStretch()
        scroll.setWidget(page)
        self.tabs.addTab(scroll, "Formats")

    def build_privacy(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(label("Privacy", "section"))
        for title, text in [
            ("Private by design", "No accounts, analytics, uploads, keyboard recording or automatic posts. The selected document is opened read-only on this computer."),
            ("Optional updates", "Automatic updates contact GitHub for release metadata and app downloads. GitHub receives normal connection information such as your IP address. No document or session data is sent. Turn automatic checks off in Updates."),
            ("Numbers, not drafts", "History stores session statistics, goal units and page measurements, never document text or file paths. Recent file paths are stored separately on this device; turn them off or clear them in Settings."),
            ("Revision metrics", "Added and removed words compare word occurrences between observed saves. Equal-length replacements count; word moves and punctuation-only edits do not. Repeated edits and saved undos count again. Paused edits are excluded. These totals describe changes, not editing quality."),
            ("An honest measure", "Net words compare saved word counts. Equal-length rewrites do not increase the number. Counting rules vary by format; see Formats & apps. Counts can differ from your editor. Cloud-only documents need a refreshed local export."),
            ("You control the clock", "Opening a file starts session time; Pause and Finish control it. It does not detect typing or focus. Edits saved while paused are excluded when you resume. A long system suspension pauses the timer. Save before pausing or finishing."),
            ("Share on your terms", "Copy sends only the displayed summary to your system clipboard. Save image exports the metrics shown on the card. Your clipboard manager or clipboard sync may retain copied summaries."),
        ]:
            self.help_section(layout, title, text)
        layout.addStretch()
        self.add_scroll_tab(page, "Privacy")

    def mode_changed(self, mode):
        if self.tracker:
            self.tracker.session.mode = mode
            self.persist()
        else:
            self.goal_unit.setCurrentText("Minutes" if mode == "Revision" else "Words")
        self.update_view()

    def clear_recents(self):
        self.recent_settings.remove("files")
        self.recent_settings.sync()

    def set_remember_files(self, enabled):
        self.recent_settings.setValue("remember", enabled)
        if not enabled:
            self.clear_recents()

    def recent_files(self):
        files = self.recent_settings.value("files", [])
        if isinstance(files, str):
            files = [files]
        return [str(p) for p in files][:10] if isinstance(files, list) else []

    def open_path(self, path):
        if self.tracker:
            return
        self.path = Path(path)
        self.begin()
        if self.tracker:
            self.file_status.setText(format_name(self.path) + " selected")
            if self.recent_settings.value("remember", True, type=bool):
                selected = str(self.path.absolute())
                self.recent_settings.setValue("files", [selected] + [p for p in self.recent_files() if p != selected][:9])
                self.recent_settings.sync()

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open writing file", "", file_filter())
        if path:
            self.open_path(path)

    def pick(self):
        files = self.recent_files()
        if not files:
            self.browse()
            return
        menu = QMenu(self)
        for path in files:
            action = menu.addAction(Path(path).name.replace("&", "&&"))
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, p=path: self.open_path(p))
        menu.addSeparator()
        menu.addAction("Browse…", self.browse)
        menu.addAction("Clear recent files", self.clear_recents)
        menu.exec(self.choose.mapToGlobal(self.choose.rect().bottomLeft()))
        menu.deleteLater()

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
        if not self.path or self.tracker:
            return
        try:
            self.tracker = Tracker(self.path, self.mode.currentText(), 0 if self.skip_goal.isChecked() else self.goal.value())
            self.tracker.session.goal_unit = self.selected_goal_unit()
            self.tracker.session.words_per_page = self.page_rate.value()
            self.pages_done.blockSignals(True)
            self.pages_done.setValue(0)
            self.pages_done.blockSignals(False)
            if self.persist():
                self.message.setText("Save in your editor to update progress.")
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
                self.message.setText("Save in your editor before finishing.")
            else:
                self.message.setText("Edits saved while paused are excluded.")
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
        except ScriptError:
            choice = QMessageBox.question(
                self, "Final save unavailable",
                "Could not read the final save. Finish using the last recorded counts?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if choice != QMessageBox.StandardButton.Yes:
                return
            session = self.tracker.session
            session.status = "done"
            if not self.persist():
                self.update_view()
                return
        self.tracker.discard_snapshot()
        self.tracker = None
        self.refresh_history()
        self.update_view()
        self.message.setText("Session saved")
        ShareDialog(session, self).exec()

    def update_view(self):
        active = self.tracker is not None
        self.setup_panel.setVisible(not active)
        self.active_panel.setVisible(active)
        self.goal_row.setVisible(not self.skip_goal.isChecked())
        self.goal_unit.setVisible(not self.skip_goal.isChecked())
        page_goal = not self.skip_goal.isChecked() and self.goal_unit.currentText() == "Pages"
        estimate = page_goal and self.page_method.currentText() == "Estimate"
        self.page_method.setVisible(page_goal)
        self.page_rate.setVisible(estimate)
        self.page_hint.setVisible(estimate)
        target = f"{self.goal.value():,} {self.goal_unit.currentText().lower()}"
        self.goal_settings_button.setText("Goal settings" if active or self.skip_goal.isChecked() else f"Goal settings · {target}")
        self.goal_settings_button.setToolTip("No goal" if self.skip_goal.isChecked() else target)
        for widget in (self.choose,):
            widget.setEnabled(not active)
        self.goal.setEnabled(not self.skip_goal.isChecked())
        self.start.setEnabled(not active and self.path is not None)
        self.start.setVisible(False)
        self.done.setVisible(active)
        self.done.setObjectName("primary")
        self.done.style().unpolish(self.done)
        self.done.style().polish(self.done)
        self.pause_button.setVisible(active)
        self.pause_button.setEnabled(active)
        self.done.setEnabled(active)
        session = self.tracker.session if active else None
        self.pages_row.setVisible(active and session.unit == "pages")
        self.revision_counts.setVisible(active and session.mode == "Revision")
        if active:
            self.revision_counts.setText(f"{session.added:,} words added · {session.removed:,} words removed")
        paused = active and session.status == "paused"
        self.pause_button.setText("Resume" if paused else "Pause")
        self.state_label.setText("Paused" if paused else "Running" if active else "Ready")
        seconds = int(session.seconds) if active else 0
        minutes, seconds = divmod(seconds, 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        estimated = active and session.unit == "estimated_pages"
        self.words.setText(f"{session.page_count:,.1f}" if estimated else f"{session.net if active else 0:+,}")
        self.words_caption.setText("Estimated pages" if estimated else "Net words")
        percent = round(session.progress * 100) if active else 0
        has_goal = bool(session.goal) if active else not self.skip_goal.isChecked()
        self.percent.setText(f"{percent}%" if has_goal else "—")
        self.percent.setToolTip("No goal set" if not has_goal else "Progress toward this session's goal")
        self.goal_caption.setText(f"Goal · {session.goal_label}" if active and has_goal else "Goal")
        self.percent.setVisible(has_goal)
        self.goal_caption.setVisible(has_goal)
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
                item = QTableWidgetItem(value)
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
        self.empty.setText("No matching sessions" if all_sessions else "No sessions yet")
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
    except ValueError as error:
        QMessageBox.critical(None, "History unavailable", str(error))
        return 1
    except Exception:
        QMessageBox.critical(None, "History unavailable", "WriteWatch could not open local history. Check disk space and folder permissions.")
        return 1
    window = Window(store, update_folder=folder)
    window.show()
    result = app.exec()
    store.close()
    lock.unlock()
    return result
