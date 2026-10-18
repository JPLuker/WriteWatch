"""Optional background update controls, isolated from writing statistics."""
from pathlib import Path
import time

from PySide6.QtCore import QSettings, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QMessageBox, QProgressBar, QComboBox
from . import __version__
from .updates import installation, UpdateWorker, install_update, RELEASES, can_install, automatic_due, updates_disabled


class UpdatesPanel(QWidget):
    def __init__(self, window, folder):
        super().__init__(window)
        self.window = window
        self.folder = Path(folder) / 'updates'
        self.installation = installation()
        self.worker = None
        self.pending = None
        self.settings = QSettings(str(Path(folder) / 'updates.ini'), QSettings.Format.IniFormat)
        layout = QVBoxLayout(self)
        title = QLabel('Updates')
        title.setObjectName('section')
        layout.addWidget(title)
        self.automatic = QCheckBox('Automatically check and download updates')
        self.automatic.setChecked(self.settings.value('automatic', True, type=bool))
        self.automatic.toggled.connect(self.preference_changed)
        layout.addWidget(self.automatic)
        layout.addWidget(QLabel('Update channel'))
        self.channel = QComboBox()
        self.channel.addItems(['Stable', 'Testing'])
        self.channel.setAccessibleName('Update channel')
        self.channel.setCurrentText(self.settings.value('channel', 'Stable'))
        layout.addWidget(self.channel)
        hint = QLabel('Stable excludes testing releases. Choose Testing to receive development builds. Automatic checks run at most once a day.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.status = QLabel('')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.cancel_button = QPushButton('Cancel download')
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        self.check = QPushButton('Check for updates')
        self.check.clicked.connect(self.check_now)
        layout.addWidget(self.check)
        self.restart = QPushButton('Restart to update')
        self.restart.setEnabled(False)
        self.restart.clicked.connect(self.apply)
        layout.addWidget(self.restart)
        if self.installation and not can_install(self.installation):
            self.automatic.setText('Automatically check for updates')
            self.restart.hide()
            self.status.setText('Updates are installed through your system package installer. No automatic APT repository is configured.' if self.installation.kind == 'deb' else 'This copy checks for updates but requires manual installation. Open releases to download a new version.')
        releases = QPushButton('View releases')
        self.releases_button = releases
        releases.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RELEASES)))
        layout.addWidget(releases)
        layout.addStretch()
        if not self.installation:
            self.status.setText('Install updates manually for this copy.')
            self.status.setToolTip('This source build or unsupported package has no automatic update target. Download a supported package from Releases.')
            self.check.setEnabled(False)
            self.automatic.setEnabled(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.automatic_check)
        self.timer.start(60 * 60 * 1000)
        self.channel.currentTextChanged.connect(self.channel_changed)
        QTimer.singleShot(5000, self.automatic_check)

    def channel_changed(self, channel):
        self.settings.setValue('channel', channel)
        self.settings.sync()
        self.pending = None
        self.restart.setEnabled(False)
        self.restart.setObjectName('')
        self.restart.style().unpolish(self.restart)
        self.restart.style().polish(self.restart)
        self.check.setEnabled(bool(self.installation))
        self.releases_button.setText('View releases')
        self.window.menu_button.setText('')
        self.window.menu_button.setToolTip('Menu')
        self.window.menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.window.tabs.setTabText(self.window.tabs.indexOf(getattr(self.window, 'settings_tab', self)), 'Settings')
        self.status.setText(f'{channel} channel selected. Check for updates when ready.')

    def preference_changed(self, enabled):
        self.settings.setValue('automatic', enabled)
        self.settings.sync()
        if not enabled and self.worker and self.worker.isRunning():
            self.worker.cancel.set()
            self.status.setText('Stopping automatic update check…')

    def automatic_check(self):
        if not self.automatic.isChecked() or updates_disabled():
            return
        now = time.time()
        last = self.settings.value('last_check', 0)
        try:
            if float(last) > now:
                # Rebase after a clock rollback instead of checking repeatedly.
                self.settings.setValue('last_check', now)
                self.settings.sync()
                return
        except (TypeError, ValueError):
            pass
        if automatic_due(last, now):
            self.check_now()

    def check_now(self):
        if updates_disabled() or not self.installation or self.pending or (self.worker and self.worker.isRunning()):
            return
        self.check.setEnabled(False)
        self.channel.setEnabled(False)
        self.settings.setValue('last_check', time.time())
        self.settings.sync()
        worker = UpdateWorker(self.installation, self.folder, self, channel=self.channel.currentText())
        self.worker = worker
        worker.status.connect(self.report_status)
        worker.progress.connect(self.report_progress)
        self.cancel_button.show()
        worker.failed.connect(self.status.setText)
        worker.ready.connect(self.downloaded)
        worker.available.connect(self.update_available)
        worker.finished.connect(self.finished)
        worker.start()

    def cancel_download(self):
        if self.worker:
            self.worker.cancel.set()
            self.status.setText('Cancelling…')

    def report_status(self, text):
        self.status.setText(text)

    def report_progress(self, count, total):
        self.progress.show()
        self.progress.setValue(count * 100 // total)
        self.status.setText(f'{count / 1048576:.0f} / {total / 1048576:.0f} MB')

    def finished(self):
        self.cancel_button.hide()
        self.channel.setEnabled(True)
        self.progress.hide()
        self.check.setEnabled(not self.pending)
        if self.worker.cancel.is_set():
            self.status.setText('Update check cancelled.')
        self.worker.deleteLater()
        self.worker = None

    def update_available(self, asset):
        self.status.setText(f"Version {asset['release_version']} is available. Open releases, download the matching package and install it manually. Your history is kept.")
        self.releases_button.setText('Download update from releases')
        self.window.menu_button.setToolTip('Menu — update available')
        self.window.menu_button.setText('Update available')
        self.window.menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def downloaded(self, path, asset):
        self.pending = (path, asset)
        self.status.setText(f"Version {asset['release_version']} ready")
        self.restart.setObjectName('primary')
        self.restart.style().unpolish(self.restart)
        self.restart.style().polish(self.restart)
        self.restart.setEnabled(True)
        self.window.menu_button.setToolTip("Menu — update ready")
        self.window.menu_button.setText("Update ready")
        self.window.menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.window.tabs.setTabText(self.window.tabs.indexOf(getattr(self.window, 'settings_tab', self)), 'Update ready')

    def apply(self):
        if not self.pending:
            return
        if self.window.tracker:
            QMessageBox.information(self, 'Finish your session first', 'Finish your session before restarting to update.')
            return
        if self.worker and self.worker.isRunning():
            return
        try:
            install_update(self.installation, *self.pending)
        except Exception as error:
            QMessageBox.warning(self, 'Could not install update', str(error))
            return
        self.window.close()

    def allow_close(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel.set()
            self.status.setText('Stopping download. Close again in a moment.')
            self.window.tabs.setCurrentWidget(getattr(self.window, 'settings_tab', self))
            return False
        return True
