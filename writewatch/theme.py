"""Aurora Glass native Qt adaptation. DESIGN.md is the token source.
Opaque surface fallback: Qt Widgets has no portable backdrop-blur material.
Static ambient light and no animations also satisfy reduced-motion preferences.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QPalette, QFontDatabase, QPen, QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QApplication, QTabBar

LIGHT = dict(canvas='#F4F5FA', surface='#FFFFFF', surface2='#EEF0F7', surface3='#E4E7F1',
             text='#14172B', secondary='#474D6B', tertiary='#62688A', accent='#6B5CF0',
             soft='#ECE9FF', onaccent='#FFFFFF', danger='#D93B3B')
DARK = dict(canvas='#0B0D16', surface='#151826', surface2='#1D2133', surface3='#262B40',
            text='#F2F3F8', secondary='#B8BCD0', tertiary='#9095AE', accent='#9C8EFF',
            soft='#262B40', onaccent='#0B0D16', danger='#FF6B6B')
SPACE = (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96)
RADIUS = dict(xs=6, sm=10, md=14, lg=20, xl=28, window=36)


def colors():
    return DARK if QApplication.instance().property('auroraDark') else LIGHT


def stylesheet(dark=True):
    t = DARK if dark else LIGHT
    check = (Path(__file__).parent / ("check-dark.svg" if dark else "check-light.svg")).as_posix()
    up = (Path(__file__).parent / ("up-dark.svg" if dark else "up-light.svg")).as_posix()
    down = (Path(__file__).parent / ("down-dark.svg" if dark else "down-light.svg")).as_posix()
    # TOKEN-GAP: Qt QSS has no pill/percentage radius; 20px is half a 40px control.
    return f'''
QWidget {{ color: {t['text']}; font-size: 15px; background: transparent; }}
QMainWindow, QDialog, QMessageBox {{ background: {t['canvas']}; }}
QLabel#brand, QLabel#section {{ font-size: 20px; font-weight: 600; }}
QLabel#title {{ font-size: 32px; font-weight: 600; }}
QLabel#muted {{ color: {t['secondary']}; }}
QLabel#eyebrow {{ color: {t['secondary']}; font-size: 14px; font-weight: 500; }}
QLabel#number {{ font-size: 32px; font-weight: 600; }}
QLabel#timer {{ font-size: 48px; font-weight: 600; }}
QFrame#segments {{ background: {t['surface2']}; border-radius: 20px; }}
QRadioButton#segment {{ background: transparent; color: {t['secondary']}; border: 2px solid transparent; border-radius: 14px; padding: 12px 16px; font-size: 14px; }}
QRadioButton#segment::indicator {{ width: 0; height: 0; border: 0; background: transparent; image: none; }}
QRadioButton#segment:checked {{ background: {t['surface']}; color: {t['accent']}; }}
QRadioButton#segment:hover {{ background: {t['surface3']}; }}
QRadioButton#segment:focus {{ border-color: {t['accent']}; }}
QRadioButton#segment:disabled {{ color: {t['tertiary']}; }}
QFrame#panel {{ background: {t['surface']}; border: none; border-radius: 28px; }}
QPushButton {{ background: {t['surface2']}; border: 2px solid transparent; border-radius: 20px; padding: 8px 16px; min-height: 20px; font-size: 14px; font-weight: 500; }}
QPushButton:hover {{ background: {t['surface3']}; }}
QPushButton:pressed {{ background: {t['soft']}; }}
QPushButton#primary {{ background: {t['accent']}; color: {t['onaccent']}; }}
QPushButton#primary:hover {{ background: {t['accent']}; border-color: {t['text']}; }}
QPushButton#destructive {{ background: transparent; color: {t['danger']}; }}
QPushButton:disabled, QPushButton#primary:disabled {{ background: {t['surface2']}; color: {t['tertiary']}; }}
QComboBox, QSpinBox {{ background: {t['surface']}; border: 2px solid {t['tertiary']}; border-radius: 10px; padding: 8px 12px; min-height: 20px; }}
QComboBox::drop-down {{ width: 24px; border: 0; }}
QComboBox::down-arrow {{ image: url("{down}"); width: 16px; height: 16px; }}
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 24px; height: 20px; border: 0; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; height: 20px; border: 0; }}
QSpinBox::up-arrow {{ image: url("{up}"); width: 16px; height: 16px; }}
QSpinBox::down-arrow {{ image: url("{down}"); width: 16px; height: 16px; }}
QComboBox:disabled, QSpinBox:disabled {{ color: {t['tertiary']}; border-color: {t['surface3']}; }}
QComboBox QAbstractItemView, QMenu {{ background: {t['surface']}; color: {t['text']}; selection-background-color: {t['soft']}; selection-color: {t['text']}; }}
QPlainTextEdit {{ background: {t['surface']}; border: 2px solid {t['tertiary']}; border-radius: 14px; padding: 16px; selection-background-color: {t['soft']}; selection-color: {t['text']}; }}
QPushButton:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTableWidget:focus {{ border: 2px solid {t['accent']}; }}
QTabWidget::pane {{ border: 0; }}
QTabWidget::tab-bar {{ alignment: center; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ color: {t['secondary']}; padding: 12px 12px; margin: 4px; border: 2px solid transparent; border-radius: 20px; font-size: 14px; font-weight: 500; }}
QTabBar::tab:selected {{ color: {t['accent']}; background: {t['soft']}; }}
QTabBar::tab:hover {{ background: {t['surface2']}; }}
QTabBar::tab:focus {{ border: 2px solid {t['accent']}; }}
QProgressBar {{ border: 0; background: {t['surface2']}; border-radius: 4px; min-height: 8px; max-height: 8px; }}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 4px; }}
QTableWidget {{ background: {t['surface']}; border: 2px solid transparent; border-radius: 20px; selection-background-color: {t['soft']}; selection-color: {t['text']}; alternate-background-color: {t['surface']}; }}
QTableWidget::item {{ padding: 8px; border: 0; }}
QTableWidget::item:hover {{ background: {t['surface2']}; }}
QHeaderView::section {{ background: {t['surface']}; border: 0; padding: 12px; color: {t['secondary']}; font-size: 13px; }}
QCheckBox {{ spacing: 8px; padding: 4px; border: 2px solid transparent; }}
QCheckBox:focus {{ border-color: {t['accent']}; border-radius: 6px; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border: 2px solid {t['tertiary']}; border-radius: 6px; background: {t['surface']}; }}
QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; image: url("{check}"); }}
QToolButton {{ background: {t['surface']}; border: 2px solid transparent; border-radius: 14px; padding: 12px 16px; color: {t['text']}; }}
QToolButton:hover {{ background: {t['surface2']}; }}
QToolButton:focus {{ border-color: {t['accent']}; }}
QToolButton:checked {{ background: {t['surface2']}; }}
QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['tertiary']}; padding: 8px; }}
QScrollArea {{ border: 0; }}
QScrollBar:vertical {{ background: {t['surface2']}; width: 12px; border-radius: 6px; }}
QScrollBar::handle:vertical {{ background: {t['tertiary']}; min-height: 32px; border-radius: 6px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
'''


def apply_theme(choice='System', ambient=True):
    app = QApplication.instance()
    dark = choice == 'Dark' or (choice == 'System' and app.styleHints().colorScheme() == Qt.ColorScheme.Dark)
    app.setProperty('auroraDark', dark)
    app.setProperty('auroraAmbient', ambient)
    t = DARK if dark else LIGHT
    palette = QPalette()
    for role, value in [(QPalette.ColorRole.Window,t['canvas']), (QPalette.ColorRole.Base,t['surface']),
                        (QPalette.ColorRole.Text,t['text']), (QPalette.ColorRole.WindowText,t['text']),
                        (QPalette.ColorRole.Button,t['surface2']), (QPalette.ColorRole.ButtonText,t['text']),
                        (QPalette.ColorRole.Highlight,t['soft']), (QPalette.ColorRole.HighlightedText,t['text'])]:
        palette.setColor(role, QColor(value))
    app.setPalette(palette)
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.setStyleSheet(stylesheet(dark))
    for widget in app.topLevelWidgets():
        widget.update()


class AmbientCanvas(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        t = colors()
        p.fillRect(self.rect(), QColor(t['canvas']))
        if QApplication.instance().property('auroraAmbient'):
            opacity = .45 if t is DARK else .30
            for x, y, color, size in [(0, 0, '#4F7BFF', .55), (1, .1, '#8B5CF6', .5), (.85, 1, '#2DD4BF', .45)]:
                glow = QRadialGradient(self.width()*x, self.height()*y, self.width()*size)
                start = QColor(color); start.setAlphaF(opacity)
                end = QColor(color); end.setAlpha(0)
                glow.setColorAt(0, start); glow.setColorAt(1, end)
                p.fillRect(self.rect(), glow)
        p.end()


class FloatingTabs(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors()['surface']))
        painter.drawRoundedRect(QRectF(self.rect()), RADIUS['xl'], RADIUS['xl'])
        painter.end()
        super().paintEvent(event)


def nav_icon(kind):
    # One outline family, 20px, rounded 1.75px strokes.
    pix = QPixmap(24, 24); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(colors()['secondary']), 1.75, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if kind in (0, 1):
        p.drawEllipse(QRectF(4, 4, 16, 16)); p.drawLine(12, 7, 12, 12); p.drawLine(12, 12, 16, 14)
        if kind == 1: p.drawLine(3, 3, 3, 8); p.drawLine(3, 8, 7, 8)
    elif kind == 2:
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 2, 2)
        for y in (8, 12, 16): p.drawLine(9, y, 15, y)
    elif kind == 3:
        p.drawRoundedRect(QRectF(5, 10, 14, 11), 2, 2); p.drawArc(QRectF(8, 2, 8, 14), 0, 180*16)
        p.drawLine(12, 14, 12, 17)
    elif kind == 5:
        for y in (6, 12, 18):
            p.drawLine(4, y, 20, y)
    else:
        for y, x in [(6, 9), (12, 15), (18, 9)]:
            p.drawLine(4, y, 20, y); p.setBrush(QColor(colors()['surface']));p.drawEllipse(QRectF(x-2, y-2, 4, 4))
    p.end(); return QIcon(pix)
