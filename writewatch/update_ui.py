"""Optional background update controls, isolated from writing statistics."""
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QMessageBox
from . import __version__
from .updates import installation, UpdateWorker, install_update, RELEASES


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
        title = QLabel(f'WriteWatch {__version__}')
        title.setObjectName('title')
        layout.addWidget(title)
        explanation = QLabel('Updates check GitHub and download new releases in the background, including preview releases. '
                             'No writing files or session statistics are sent. Finish your session before restarting to update.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.automatic = QCheckBox('Automatically check and download updates')
        self.automatic.setChecked(self.settings.value('automatic', True, type=bool))
        self.automatic.toggled.connect(self.preference_changed)
        layout.addWidget(self.automatic)
        self.status = QLabel('Ready to check for updates.')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.check = QPushButton('Check for updates')
        self.check.clicked.connect(self.check_now)
        layout.addWidget(self.check)
        self.restart = QPushButton('Restart to Update')
        self.restart.setEnabled(False)
        self.restart.clicked.connect(self.apply)
        layout.addWidget(self.restart)
        releases = QPushButton('View releases / install manually')
        releases.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RELEASES)))
        layout.addWidget(releases)
        layout.addStretch()
        if not self.installation:
            self.status.setText('Automatic installation is available for the Windows app, Linux AppImage and installed macOS app. '
                                'For source or Linux tar builds, install manually. On macOS, move the app out of the disk image first.')
            self.check.setEnabled(False)
            self.automatic.setEnabled(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.automatic_check)
        self.timer.start(6 * 60 * 60 * 1000)
        QTimer.singleShot(5000, self.automatic_check)

    def preference_changed(self, enabled):
        self.settings.setValue('automatic', enabled)
        self.settings.sync()
        if not enabled and self.worker and self.worker.isRunning():
            self.worker.cancel.set()
            self.status.setText('Stopping automatic update check…')

    def automatic_check(self):
        if self.automatic.isChecked():
            self.check_now()

    def check_now(self):
        if not self.installation or self.pending or (self.worker and self.worker.isRunning()):
            return
        self.check.setEnabled(False)
        worker = UpdateWorker(self.installation, self.folder, self)
        self.worker = worker
        worker.status.connect(self.status.setText)
        worker.failed.connect(self.status.setText)
        worker.ready.connect(self.downloaded)
        worker.finished.connect(self.finished)
        worker.start()

    def finished(self):
        self.check.setEnabled(not self.pending)
        if self.worker.cancel.is_set():
            self.status.setText('Update check cancelled.')
        self.worker.deleteLater()
        self.worker = None

    def downloaded(self, path, asset):
        self.pending = (path, asset)
        self.status.setText(f"Version {asset['release_version']} downloaded and verified. Ready when you are.")
        self.restart.setEnabled(True)
        self.window.tabs.setTabText(self.window.tabs.indexOf(self), 'Update ready')

    def apply(self):
        if not self.pending:
            return
        if self.window.tracker:
            QMessageBox.information(self, 'Finish your session first', 'Use Done to save your session before restarting to update.')
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
            self.window.tabs.setCurrentWidget(self)
            return False
        return True
