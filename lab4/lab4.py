#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лабораторная работа 4. Вариант 5.
Часть 1: алгоритм Лианга-Барски (параметрическое задание отрезков).
Часть 2: алгоритм отсечения выпуклого многоугольника (Сазерленд-Ходжмен).

Установка:   pip install PySide6
Запуск:      python lab4_variant5.py

Возможности:
  * мышью можно перетаскивать концы отрезков, вершины, углы и тело окна — результат пересчитывается сразу;
  * колесо — масштаб, правая/средняя кнопка (или перетаскивание пустого места) — сдвиг;
  * журнал справа — пошаговая трассировка Лианга-Барски для выбранного отрезка (p, q, t0, t1);
  * для многоугольника — ползунок по этапам отсечения (по одной границе окна);
  * светлая/тёмная тема, открытие/сохранение файлов в формате из задания.

Формат файла (часть 1):            Формат файла (часть 2):
    n                                  n
    X1 Y1 X2 Y2  (n строк)             X Y  (n строк — вершины)
    Xmin Ymin Xmax Ymax                Xmin Ymin Xmax Ymax
"""
import math
import random
import sys

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QGroupBox, QDoubleSpinBox,
    QPlainTextEdit, QFileDialog, QMessageBox, QSlider, QCheckBox, QToolBar, QHeaderView,
    QAbstractItemView, QFormLayout, QSizePolicy,
)

# =============================================================================
#  АЛГОРИТМЫ  (каждый может вести журнал log — список строк)
# =============================================================================
def fmt(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pt(x, y):
    return "(%s; %s)" % (fmt(x), fmt(y))


def liang_barsky(seg, w, log=None):
    """Лианг-Барски: P(t) = P1 + t·(P2 − P1), t ∈ [0, 1]; для каждой границы p·t ≤ q."""
    L = log.append if log is not None else (lambda s: None)
    x1, y1, x2, y2 = seg
    xmin, ymin, xmax, ymax = w
    dx, dy = x2 - x1, y2 - y1
    L("dx = %s,  dy = %s" % (fmt(dx), fmt(dy)))
    L("t0 = 0,  t1 = 1\n")
    t0, t1 = 0.0, 1.0
    for name, p, q in (("левая   ", -dx, x1 - xmin), ("правая  ", dx, xmax - x1),
                       ("нижняя  ", -dy, y1 - ymin), ("верхняя ", dy, ymax - y1)):
        if p == 0:
            if q < 0:
                L("%s p = 0, q = %s < 0  →  параллелен границе и снаружи: ОТБРОШЕН" % (name, fmt(q)))
                return None
            L("%s p = 0, q = %s ≥ 0  →  параллелен границе, внутри полосы" % (name, fmt(q)))
            continue
        r = q / p
        if p < 0:
            L("%s p = %s < 0 (вход),  r = q/p = %s" % (name, fmt(p), fmt(r)))
            if r > t1:
                L("          r > t1  →  ОТБРОШЕН")
                return None
            t0 = max(t0, r)
        else:
            L("%s p = %s > 0 (выход), r = q/p = %s" % (name, fmt(p), fmt(r)))
            if r < t0:
                L("          r < t0  →  ОТБРОШЕН")
                return None
            t1 = min(t1, r)
        L("          t0 = %s,  t1 = %s" % (fmt(t0), fmt(t1)))
    res = (x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy)
    L("\nВидимая часть: P(t0)=%s,  P(t1)=%s" % (pt(res[0], res[1]), pt(res[2], res[3])))
    return res


def _dedupe(poly):
    res = []
    for p in poly:
        if not res or math.hypot(p[0] - res[-1][0], p[1] - res[-1][1]) > 1e-9:
            res.append(p)
    if len(res) > 1 and math.hypot(res[0][0] - res[-1][0], res[0][1] - res[-1][1]) <= 1e-9:
        res.pop()
    return res


def clip_polygon_stages(poly, w):
    """Сазерленд-Ходжмен: список этапов [(название, многоугольник)], этап 0 — исходный."""
    xmin, ymin, xmax, ymax = w

    def ix(a, b, xc):
        t = (xc - a[0]) / (b[0] - a[0])
        return (xc, a[1] + t * (b[1] - a[1]))

    def iy(a, b, yc):
        t = (yc - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), yc)

    edges = [
        ("левая граница x ≥ xmin", lambda p: p[0] >= xmin, lambda a, b: ix(a, b, xmin)),
        ("правая граница x ≤ xmax", lambda p: p[0] <= xmax, lambda a, b: ix(a, b, xmax)),
        ("нижняя граница y ≥ ymin", lambda p: p[1] >= ymin, lambda a, b: iy(a, b, ymin)),
        ("верхняя граница y ≤ ymax", lambda p: p[1] <= ymax, lambda a, b: iy(a, b, ymax)),
    ]
    cur = [tuple(p) for p in poly]
    stages = [("исходный многоугольник", cur)]
    for name, inside, inter in edges:
        inp, out = cur, []
        if inp:
            prev = inp[-1]
            for c in inp:
                if inside(c):
                    if not inside(prev):
                        out.append(inter(prev, c))
                    out.append(c)
                elif inside(prev):
                    out.append(inter(prev, c))
                prev = c
        cur = _dedupe(out)
        stages.append((name, cur))
    return stages


def is_convex(poly):
    n = len(poly)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        a, b, c = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-12:
            continue
        s = 1 if cr > 0 else -1
        if sign and s != sign:
            return False
        sign = s
    return sign != 0


# =============================================================================
#  МОДЕЛЬ ДАННЫХ И ФАЙЛЫ
# =============================================================================
class Model(QObject):
    changed = Signal()

    def __init__(self, segs=None, poly=None, win=(-4, -3, 4, 3)):
        super().__init__()
        self.segs = [list(map(float, s)) for s in (segs or [])]
        self.poly = [list(map(float, p)) for p in (poly or [])]
        self.win = list(map(float, win))


def parse_text(text, kind):
    t = text.replace(",", ".").split()
    n = int(t[0])
    nums = [float(v) for v in t[1:]]
    per = 4 if kind == "seg" else 2
    if len(nums) != per * n + 4:
        raise ValueError("Ожидалось %d чисел после n, найдено %d" % (per * n + 4, len(nums)))
    items = [nums[per * i:per * i + per] for i in range(n)]
    x0, y0, x1, y1 = nums[per * n:]
    return items, [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


def dump_text(items, win):
    lines = [str(len(items))]
    lines += [" ".join(fmt(v) for v in it) for it in items]
    lines.append(" ".join(fmt(v) for v in win))
    return "\n".join(lines) + "\n"


# =============================================================================
#  ТЕМЫ
# =============================================================================
THEMES = {
    "dark": dict(bg="#11151e", grid="#1f2635", minor="#171d2a", axes="#8c97ad", label="#9aa5bb",
                 win="#4c8dff", src="#ff6b73", vis="#3ddc84", accent="#ffc857", panel="#171c28",
                 panel2="#10141c", input="#0f131b", border="#2a3347", btn="#222b3d", sel="#2b3a5c",
                 fg="#e3e8f2", muted="#8b96ab"),
    "light": dict(bg="#fbfcfe", grid="#dfe5ef", minor="#eef1f7", axes="#3a4356", label="#556079",
                  win="#2c63f2", src="#e0424a", vis="#16a34a", accent="#f0a500", panel="#f3f5fa",
                  panel2="#e6eaf2", input="#ffffff", border="#cdd5e3", btn="#ffffff", sel="#cfe0ff",
                  fg="#1b2233", muted="#667089"),
}


def build_qss(t):
    return f"""
    QMainWindow, QWidget {{ background:{t['panel']}; color:{t['fg']}; font-size:13px; }}
    QTabWidget::pane {{ border:0; }}
    QTabBar::tab {{ background:{t['panel2']}; padding:10px 20px; margin-right:2px; color:{t['muted']};
                   border-top-left-radius:8px; border-top-right-radius:8px; }}
    QTabBar::tab:selected {{ background:{t['panel']}; color:{t['fg']}; border-bottom:3px solid {t['accent']}; }}
    QGroupBox {{ border:1px solid {t['border']}; border-radius:8px; margin-top:12px; padding:10px 8px 6px 8px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding:0 4px; color:{t['muted']}; }}
    QPushButton {{ background:{t['btn']}; border:1px solid {t['border']}; border-radius:6px; padding:6px 12px; }}
    QPushButton:hover {{ border-color:{t['accent']}; }}
    QPushButton#primary {{ background:{t['accent']}; color:#16181f; font-weight:600; border:0; }}
    QTableWidget, QPlainTextEdit, QDoubleSpinBox {{ background:{t['input']}; border:1px solid {t['border']};
                   border-radius:6px; }}
    QTableWidget {{ gridline-color:{t['border']}; selection-background-color:{t['sel']}; selection-color:{t['fg']}; }}
    QHeaderView::section {{ background:{t['panel2']}; border:0; padding:5px; color:{t['muted']}; }}
    QLabel#hint {{ color:{t['muted']}; }}
    QLabel#title {{ font-size:17px; font-weight:700; }}
    QToolBar {{ background:{t['panel2']}; border:0; spacing:6px; padding:4px; }}
    QStatusBar {{ background:{t['panel2']}; color:{t['muted']}; }}
    QSlider::groove:horizontal {{ height:4px; background:{t['border']}; border-radius:2px; }}
    QSlider::handle:horizontal {{ background:{t['accent']}; width:16px; margin:-6px 0; border-radius:8px; }}
    QSplitter::handle {{ background:{t['border']}; }}
    """


# =============================================================================
#  ХОЛСТ
# =============================================================================
def nice_step(span, target=10):
    raw = max(span, 1e-9) / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class Canvas(QWidget):
    hovered = Signal(float, float)
    segmentSelected = Signal(int)

    def __init__(self, model, kind, theme):
        super().__init__()
        self.model, self.kind, self.t = model, kind, theme
        self.s, self.ox, self.oy = 40.0, 0.0, 0.0
        self.pending_fit = True
        self.results, self.stages, self.stage = [], [], 4
        self.selected = -1
        self.snap = False
        self.drag = None
        self.last = None
        self.setMouseTracking(True)
        self.setMinimumSize(420, 360)

    # ---- преобразования
    def w2s(self, x, y):
        return QPointF(self.ox + self.s * x, self.oy - self.s * y)

    def s2w(self, px, py):
        return (px - self.ox) / self.s, (self.oy - py) / self.s

    def fit(self):
        m = self.model
        xs, ys = [0.0, m.win[0], m.win[2]], [0.0, m.win[1], m.win[3]]
        if self.kind == "seg":
            for s in m.segs:
                xs += [s[0], s[2]]
                ys += [s[1], s[3]]
        else:
            xs += [p[0] for p in m.poly]
            ys += [p[1] for p in m.poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        bw, bh = (x1 - x0) or 1, (y1 - y0) or 1
        W, H = max(self.width(), 100), max(self.height(), 100)
        mg = 36
        self.s = min((W - 2 * mg) / bw, (H - 2 * mg) / bh)
        self.ox = W / 2 - self.s * (x0 + x1) / 2
        self.oy = H / 2 + self.s * (y0 + y1) / 2
        self.pending_fit = False
        self.update()

    # ---- рисование
    def paintEvent(self, _):
        if self.pending_fit and self.width() > 100:
            self.fit()
        t = self.t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(t["bg"]))
        self.draw_grid(p)
        if self.kind == "seg":
            self.draw_window(p)
            self.draw_segments(p)
        else:
            self.draw_polygon(p)
            self.draw_window(p)
        self.draw_legend(p)
        p.end()

    def draw_grid(self, p):
        t, W, H = self.t, self.width(), self.height()
        xa, ya = self.s2w(0, H)[0], self.s2w(0, H)[1]
        x_lo, y_lo = self.s2w(0, H)
        x_hi, y_hi = self.s2w(W, 0)
        step = nice_step(max(x_hi - x_lo, y_hi - y_lo))
        minor = step / 5
        if minor * self.s >= 9:
            p.setPen(QPen(QColor(t["minor"]), 1))
            k = math.ceil(x_lo / minor)
            while k * minor <= x_hi:
                sx = self.w2s(k * minor, 0).x()
                p.drawLine(QPointF(sx, 0), QPointF(sx, H))
                k += 1
            k = math.ceil(y_lo / minor)
            while k * minor <= y_hi:
                sy = self.w2s(0, k * minor).y()
                p.drawLine(QPointF(0, sy), QPointF(W, sy))
                k += 1
        # оси прижимаем к краям, если начало координат ушло за экран
        axis_y = min(max(self.oy, 18), H - 18)
        axis_x = min(max(self.ox, 34), W - 34)
        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        k = math.ceil(x_lo / step)
        while k * step <= x_hi:
            sx = self.w2s(k * step, 0).x()
            p.setPen(QPen(QColor(t["grid"]), 1))
            p.drawLine(QPointF(sx, 0), QPointF(sx, H))
            if k != 0:
                p.setPen(QColor(t["label"]))
                p.drawText(QRectF(sx - 30, axis_y + 3, 60, 14), Qt.AlignCenter, fmt(k * step))
            k += 1
        k = math.ceil(y_lo / step)
        while k * step <= y_hi:
            sy = self.w2s(0, k * step).y()
            p.setPen(QPen(QColor(t["grid"]), 1))
            p.drawLine(QPointF(0, sy), QPointF(W, sy))
            if k != 0:
                p.setPen(QColor(t["label"]))
                p.drawText(QRectF(axis_x - 38, sy - 7, 32, 14), Qt.AlignRight | Qt.AlignVCenter, fmt(k * step))
            k += 1
        p.setPen(QColor(t["label"]))
        p.drawText(QRectF(axis_x - 38, axis_y + 3, 32, 14), Qt.AlignRight, "0")
        # оси со стрелками
        pen = QPen(QColor(t["axes"]), 2)
        p.setPen(pen)
        p.setBrush(QColor(t["axes"]))
        p.drawLine(QPointF(0, axis_y), QPointF(W - 6, axis_y))
        p.drawLine(QPointF(axis_x, H), QPointF(axis_x, 6))
        p.drawPolygon(QPolygonF([QPointF(W - 2, axis_y), QPointF(W - 12, axis_y - 4), QPointF(W - 12, axis_y + 4)]))
        p.drawPolygon(QPolygonF([QPointF(axis_x, 2), QPointF(axis_x - 4, 12), QPointF(axis_x + 4, 12)]))
        f = QFont()
        f.setPointSize(11)
        f.setItalic(True)
        p.setFont(f)
        p.drawText(QPointF(W - 20, axis_y - 10), "x")
        p.drawText(QPointF(axis_x + 10, 20), "y")
        p.setBrush(Qt.NoBrush)

    def draw_window(self, p):
        t = self.t
        x0, y0, x1, y1 = self.model.win
        a, b = self.w2s(x0, y1), self.w2s(x1, y0)
        r = QRectF(a, b)
        fill = QColor(t["win"])
        fill.setAlpha(28)
        p.setBrush(fill)
        p.setPen(QPen(QColor(t["win"]), 2.5))
        p.drawRect(r)
        # подсветка границы, обрабатываемой на текущем этапе многоугольника
        if self.kind == "poly" and 1 <= self.stage <= 4:
            pen = QPen(QColor(t["accent"]), 5)
            p.setPen(pen)
            ln = {1: (r.topLeft(), r.bottomLeft()), 2: (r.topRight(), r.bottomRight()),
                  3: (r.bottomLeft(), r.bottomRight()), 4: (r.topLeft(), r.topRight())}[self.stage]
            p.drawLine(*ln)
        p.setBrush(QColor(t["bg"]))
        p.setPen(QPen(QColor(t["win"]), 2))
        for c in (r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()):
            p.drawRect(QRectF(c.x() - 4, c.y() - 4, 8, 8))
        p.setBrush(Qt.NoBrush)

    def draw_segments(self, p):
        t = self.t
        f = QFont()
        f.setPointSize(9)
        f.setBold(True)
        p.setFont(f)
        for i, s in enumerate(self.model.segs):
            a, b = self.w2s(s[0], s[1]), self.w2s(s[2], s[3])
            if i == self.selected:
                glow = QColor(t["accent"])
                glow.setAlpha(110)
                p.setPen(QPen(glow, 11, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(a, b)
            pen = QPen(QColor(t["src"]), 1.6, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(a, b)
        for i, r in enumerate(self.results):
            if r is None:
                continue
            p.setPen(QPen(QColor(t["vis"]), 4.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(self.w2s(r[0], r[1]), self.w2s(r[2], r[3]))
            s = self.model.segs[i]
            p.setBrush(QColor(t["bg"]))
            p.setPen(QPen(QColor(t["vis"]), 2))
            for (rx, ry), (sx, sy) in (((r[0], r[1]), (s[0], s[1])), ((r[2], r[3]), (s[2], s[3]))):
                if abs(rx - sx) > 1e-7 or abs(ry - sy) > 1e-7:      # новая точка (пересечение)
                    q = self.w2s(rx, ry)
                    p.drawEllipse(q, 4.5, 4.5)
            p.setBrush(Qt.NoBrush)
        for i, s in enumerate(self.model.segs):
            a, b = self.w2s(s[0], s[1]), self.w2s(s[2], s[3])
            p.setBrush(QColor(t["src"]))
            p.setPen(QPen(QColor(t["bg"]), 1.5))
            p.drawEllipse(a, 5, 5)
            p.drawEllipse(b, 5, 5)
            p.setBrush(Qt.NoBrush)
            mid = QPointF((a.x() + b.x()) / 2 + 6, (a.y() + b.y()) / 2 - 6)
            p.setPen(QColor(t["accent"] if i == self.selected else t["label"]))
            p.drawText(mid, str(i + 1))

    def draw_polygon(self, p):
        t = self.t
        poly = self.model.poly
        if len(poly) >= 2:
            qp = QPolygonF([self.w2s(x, y) for x, y in poly])
            p.setPen(QPen(QColor(t["src"]), 1.8, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawPolygon(qp)
        if self.stages and 0 <= self.stage < len(self.stages):
            cur = self.stages[self.stage][1]
            if len(cur) >= 3:
                col = QColor(t["vis"])
                fill = QColor(col)
                fill.setAlpha(80)
                p.setBrush(fill)
                p.setPen(QPen(col, 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPolygon(QPolygonF([self.w2s(x, y) for x, y in cur]))
                p.setBrush(QColor(t["bg"]))
                p.setPen(QPen(col, 2))
                for x, y in cur:
                    p.drawEllipse(self.w2s(x, y), 4, 4)
        f = QFont()
        f.setPointSize(9)
        f.setBold(True)
        p.setFont(f)
        for i, (x, y) in enumerate(poly):
            q = self.w2s(x, y)
            p.setBrush(QColor(t["src"]))
            p.setPen(QPen(QColor(t["bg"]), 1.5))
            p.drawEllipse(q, 5.5, 5.5)
            p.setPen(QColor(t["label"]))
            p.drawText(QPointF(q.x() + 8, q.y() - 8), "V%d" % (i + 1))
        p.setBrush(Qt.NoBrush)

    def draw_legend(self, p):
        t = self.t
        items = [(t["win"], "отсекающее окно", Qt.SolidLine, 3),
                 (t["src"], "исходные данные", Qt.DashLine, 2),
                 (t["vis"], "видимая часть", Qt.SolidLine, 4)]
        w, h = 168, 12 + 20 * len(items)
        bg = QColor(t["bg"])
        bg.setAlpha(215)
        p.setPen(QPen(QColor(t["border"]), 1))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(10, 10, w, h), 8, 8)
        f = QFont()
        f.setPointSize(9)
        p.setFont(f)
        y = 28
        for col, text, style, wd in items:
            p.setPen(QPen(QColor(col), wd, style))
            p.drawLine(QPointF(20, y), QPointF(46, y))
            p.setPen(QColor(t["fg"]))
            p.drawText(QPointF(54, y + 4), text)
            y += 20

    # ---- мышь
    def handles(self):
        m, h = self.model, []
        if self.kind == "seg":
            for i, s in enumerate(m.segs):
                h.append((("p", i, 0), s[0], s[1]))
                h.append((("p", i, 1), s[2], s[3]))
        else:
            for i, v in enumerate(m.poly):
                h.append((("v", i), v[0], v[1]))
        x0, y0, x1, y1 = m.win
        for c, (x, y) in enumerate(((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
            h.append((("w", c), x, y))
        return h

    def hit_handle(self, pos):
        for key, x, y in self.handles():
            q = self.w2s(x, y)
            if math.hypot(q.x() - pos.x(), q.y() - pos.y()) <= 10:
                return key
        return None

    def hit_segment(self, pos):
        if self.kind != "seg":
            return -1
        best, bi = 7.0, -1
        for i, s in enumerate(self.model.segs):
            a, b = self.w2s(s[0], s[1]), self.w2s(s[2], s[3])
            dx, dy = b.x() - a.x(), b.y() - a.y()
            L2 = dx * dx + dy * dy
            u = 0 if L2 == 0 else max(0, min(1, ((pos.x() - a.x()) * dx + (pos.y() - a.y()) * dy) / L2))
            d = math.hypot(a.x() + u * dx - pos.x(), a.y() + u * dy - pos.y())
            if d < best:
                best, bi = d, i
        return bi

    def in_window(self, pos):
        x, y = self.s2w(pos.x(), pos.y())
        x0, y0, x1, y1 = self.model.win
        return x0 <= x <= x1 and y0 <= y <= y1

    def mousePressEvent(self, e):
        pos = e.position()
        self.last = pos
        if e.button() != Qt.LeftButton:
            self.drag = ("pan",)
            return
        key = self.hit_handle(pos)
        if key:
            self.drag = ("h", key)
            return
        i = self.hit_segment(pos)
        if i >= 0:
            self.selected = i
            self.segmentSelected.emit(i)
            self.drag = ("seg", i)
            self.update()
        elif self.in_window(pos):
            self.drag = ("win",)
        else:
            self.drag = ("pan",)

    def mouseMoveEvent(self, e):
        pos = e.position()
        wx, wy = self.s2w(pos.x(), pos.y())
        self.hovered.emit(wx, wy)
        m = self.model
        if self.drag is None:
            if self.hit_handle(pos):
                self.setCursor(Qt.PointingHandCursor)
            elif self.hit_segment(pos) >= 0:
                self.setCursor(Qt.PointingHandCursor)
            elif self.in_window(pos):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return
        kind = self.drag[0]
        if kind == "pan":
            self.ox += pos.x() - self.last.x()
            self.oy += pos.y() - self.last.y()
            self.update()
        elif kind == "h":
            self.move_handle(self.drag[1], wx, wy)
        else:
            lx, ly = self.s2w(self.last.x(), self.last.y())
            dx, dy = wx - lx, wy - ly
            if kind == "seg":
                s = m.segs[self.drag[1]]
                s[0] += dx; s[1] += dy; s[2] += dx; s[3] += dy
            else:
                m.win[0] += dx; m.win[2] += dx; m.win[1] += dy; m.win[3] += dy
            m.changed.emit()
        self.last = pos

    def move_handle(self, key, wx, wy):
        m = self.model
        if self.snap:
            wx, wy = round(wx * 2) / 2, round(wy * 2) / 2
        else:
            wx, wy = round(wx, 3), round(wy, 3)
        k = key[0]
        if k == "p":
            m.segs[key[1]][2 * key[2]] = wx
            m.segs[key[1]][2 * key[2] + 1] = wy
        elif k == "v":
            m.poly[key[1]][0], m.poly[key[1]][1] = wx, wy
        else:
            c = key[1]
            x0, y0, x1, y1 = m.win
            if c in (0, 3):
                x0 = min(wx, x1 - 0.05)
            else:
                x1 = max(wx, x0 + 0.05)
            if c in (0, 1):
                y0 = min(wy, y1 - 0.05)
            else:
                y1 = max(wy, y0 + 0.05)
            m.win[:] = [x0, y0, x1, y1]
        m.changed.emit()

    def mouseReleaseEvent(self, e):
        self.drag = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        pos = e.position()
        wx, wy = self.s2w(pos.x(), pos.y())
        self.s *= f
        self.ox = pos.x() - self.s * wx
        self.oy = pos.y() + self.s * wy
        self.update()


# =============================================================================
#  ВКЛАДКИ
# =============================================================================
def make_btn(text, slot, primary=False):
    b = QPushButton(text)
    if primary:
        b.setObjectName("primary")
    b.clicked.connect(slot)
    return b


def spin():
    s = QDoubleSpinBox()
    s.setRange(-10000, 10000)
    s.setDecimals(3)
    s.setSingleStep(0.5)
    s.setKeyboardTracking(False)
    return s


class BaseTab(QWidget):
    COLS = []

    def __init__(self, model, kind, theme, title, description):
        super().__init__()
        self.model, self.kind = model, kind
        self.busy = False
        self.canvas = Canvas(model, kind, theme)

        panel = QWidget()
        panel.setMinimumWidth(460)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 12, 12, 12)
        t = QLabel(title)
        t.setObjectName("title")
        t.setWordWrap(True)
        lay.addWidget(t)
        d = QLabel(description)
        d.setObjectName("hint")
        d.setWordWrap(True)
        lay.addWidget(d)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        if len(self.COLS) > 3:
            for c in range(1, 5):
                hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
            hh.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_select)
        lay.addWidget(self.table, 3)

        row = QHBoxLayout()
        self.build_buttons(row)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(make_btn("Открыть…", self.open_file))
        row2.addWidget(make_btn("Сохранить…", self.save_file))
        row2.addWidget(make_btn("Вписать", self.canvas.fit))
        lay.addLayout(row2)

        g = QGroupBox("Отсекающее окно")
        form = QFormLayout(g)
        self.sp = [spin() for _ in range(4)]
        grid = QHBoxLayout()
        for name, s in zip(("Xmin", "Ymin", "Xmax", "Ymax"), self.sp):
            col = QVBoxLayout()
            lb = QLabel(name)
            lb.setObjectName("hint")
            col.addWidget(lb)
            col.addWidget(s)
            grid.addLayout(col)
            s.valueChanged.connect(self.on_window_spin)
        form.addRow(grid)
        snap = QCheckBox("Привязка к сетке 0.5 при перетаскивании")
        snap.toggled.connect(lambda v: setattr(self.canvas, "snap", v))
        form.addRow(snap)
        lay.addWidget(g)

        self.extra(lay)
        lg = QLabel("Журнал алгоритма")
        lg.setObjectName("hint")
        lay.addWidget(lg)
        self.trace = QPlainTextEdit()
        self.trace.setReadOnly(True)
        f = QFont("Menlo, Consolas, DejaVu Sans Mono, monospace")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(10)
        self.trace.setFont(f)
        lay.addWidget(self.trace, 4)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.canvas)
        split.addWidget(panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([800, 520])
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(split)
        model.changed.connect(self.refresh)
        self.canvas.segmentSelected.connect(self.select_row)
        self.refresh()

    # --- заглушки
    def extra(self, lay):
        pass

    def build_buttons(self, row):
        pass

    # --- общее
    def set_theme(self, theme):
        self.canvas.t = theme
        self.canvas.update()

    def on_window_spin(self):
        if self.busy:
            return
        v = [s.value() for s in self.sp]
        self.model.win[:] = [min(v[0], v[2]), min(v[1], v[3]), max(v[0], v[2]), max(v[1], v[3])]
        self.model.changed.emit()

    def select_row(self, i):
        self.table.selectRow(i)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                items, win = parse_text(f.read(), self.kind)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка во входных данных", str(e))
            return
        self.set_items(items)
        self.model.win[:] = win
        self.model.changed.emit()
        self.canvas.fit()

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", "data.txt", "Текстовые файлы (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(dump_text(self.get_items(), self.model.win))

    def on_item_changed(self, item):
        if self.busy:
            return
        try:
            v = float(item.text().replace(",", "."))
        except ValueError:
            self.refresh()
            return
        self.get_items()[item.row()][item.column() - self.COL0] = v
        self.model.changed.emit()

    COL0 = 1

    def sync_common(self):
        self.busy = True
        for s, v in zip(self.sp, self.model.win):
            s.setValue(v)
        self.busy = False

    def fill_table(self, rows, result_texts=None):
        self.busy = True
        sel = self.table.currentRow()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            it = QTableWidgetItem(str(i + 1))
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, it)
            for j, v in enumerate(r):
                it = QTableWidgetItem(fmt(v))
                it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j + 1, it)
            if result_texts:
                it = QTableWidgetItem(result_texts[i][0])
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                it.setForeground(QColor(self.canvas.t["vis"] if result_texts[i][1] else self.canvas.t["src"]))
                self.table.setItem(i, len(r) + 1, it)
        if 0 <= sel < len(rows):
            self.table.selectRow(sel)
        self.busy = False


class SegTab(BaseTab):
    COLS = ["№", "X1", "Y1", "X2", "Y2", "Результат"]

    def __init__(self, model, theme, title, description, algo):
        self.algo = algo
        super().__init__(model, "seg", theme, title, description)

    def build_buttons(self, row):
        row.addWidget(make_btn("+ Отрезок", self.add))
        row.addWidget(make_btn("− Удалить", self.remove))
        row.addWidget(make_btn("Случайные", self.randomize, True))

    def get_items(self):
        return self.model.segs

    def set_items(self, items):
        self.model.segs[:] = items

    def add(self):
        self.model.segs.append([-2.0, -1.0, 2.0, 1.0])
        self.model.changed.emit()

    def remove(self):
        i = self.table.currentRow()
        if 0 <= i < len(self.model.segs):
            del self.model.segs[i]
            self.canvas.selected = -1
            self.model.changed.emit()

    def randomize(self):
        x0, y0, x1, y1 = self.model.win
        cx, cy, sx, sy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0), (y1 - y0)
        self.model.segs[:] = [[round(cx + random.uniform(-1.2, 1.2) * sx, 2), round(cy + random.uniform(-1.2, 1.2) * sy, 2),
                               round(cx + random.uniform(-1.2, 1.2) * sx, 2), round(cy + random.uniform(-1.2, 1.2) * sy, 2)]
                              for _ in range(8)]
        self.model.changed.emit()

    def refresh(self):
        m = self.model
        self.canvas.results = [self.algo(s, m.win) for s in m.segs]
        texts = []
        for r in self.canvas.results:
            if r is None:
                texts.append(("отброшен", False))
            else:
                texts.append(("%s–%s" % (pt(r[0], r[1]), pt(r[2], r[3])), True))
        self.sync_common()
        self.fill_table(m.segs, texts)
        self.table.resizeColumnToContents(0)
        self.canvas.update()
        self.show_trace()

    def on_select(self):
        if self.busy:
            return
        self.canvas.selected = self.table.currentRow()
        self.canvas.update()
        self.show_trace()

    def show_trace(self):
        i = self.table.currentRow()
        if 0 <= i < len(self.model.segs):
            log = []
            self.algo(self.model.segs[i], self.model.win, log)
            self.trace.setPlainText("Отрезок №%d\n\n" % (i + 1) + "\n".join(log).strip("\n"))
        else:
            self.trace.setPlainText("Выберите отрезок в таблице или кликните по нему на графике — "
                                    "здесь появится пошаговая трассировка алгоритма.")


class PolyTab(BaseTab):
    COLS = ["№", "X", "Y"]

    def __init__(self, model, theme):
        super().__init__(
            model, "poly", theme, "Часть 2 · Отсечение выпуклого многоугольника",
            "Алгоритм Сазерленда-Ходжмена: многоугольник последовательно отсекается полуплоскостью "
            "каждой границы окна (левой, правой, нижней, верхней). Для каждой пары соседних вершин "
            "возможны 4 случая: обе внутри, выход, вход, обе снаружи. Тяните вершины мышью.")

    def extra(self, lay):
        g = QGroupBox("Этапы отсечения")
        v = QVBoxLayout(g)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 4)
        self.slider.setValue(4)
        self.slider.valueChanged.connect(self.on_stage)
        self.stage_lbl = QLabel()
        self.stage_lbl.setWordWrap(True)
        self.convex_lbl = QLabel()
        v.addWidget(self.slider)
        v.addWidget(self.stage_lbl)
        v.addWidget(self.convex_lbl)
        lay.addWidget(g)

    def build_buttons(self, row):
        row.addWidget(make_btn("+ Вершина", self.add))
        row.addWidget(make_btn("− Удалить", self.remove))
        row.addWidget(make_btn("Случайный", self.randomize, True))

    def get_items(self):
        return self.model.poly

    def set_items(self, items):
        self.model.poly[:] = items

    def add(self):
        p = self.model.poly
        if len(p) >= 2:
            a, b = p[-1], p[0]
            p.append([(a[0] + b[0]) / 2 + 0.5, (a[1] + b[1]) / 2 + 0.5])
        else:
            p.append([0.0, 0.0])
        self.model.changed.emit()

    def remove(self):
        i = self.table.currentRow()
        if 0 <= i < len(self.model.poly) and len(self.model.poly) > 3:
            del self.model.poly[i]
            self.model.changed.emit()

    def randomize(self):
        n = random.randint(5, 8)
        x0, y0, x1, y1 = self.model.win
        cx, cy = (x0 + x1) / 2 + random.uniform(-1, 1), (y0 + y1) / 2 + random.uniform(-1, 1)
        r = max(x1 - x0, y1 - y0) * random.uniform(0.6, 0.9)
        angs = sorted(random.uniform(0, 2 * math.pi) for _ in range(n))
        self.model.poly[:] = [[round(cx + r * math.cos(a), 2), round(cy + r * 0.8 * math.sin(a), 2)] for a in angs]
        self.model.changed.emit()

    def refresh(self):
        m = self.model
        self.canvas.stages = clip_polygon_stages(m.poly, m.win)
        self.canvas.stage = self.slider.value() if hasattr(self, "slider") else 4
        self.sync_common()
        self.fill_table(m.poly)
        ok = is_convex(m.poly)
        self.convex_lbl.setText("Исходный многоугольник выпуклый ✓" if ok else
                                "⚠ Многоугольник невыпуклый — алгоритм рассчитан на выпуклые")
        self.convex_lbl.setStyleSheet("color:%s" % self.canvas.t["vis" if ok else "src"])
        self.canvas.update()
        self.on_stage()

    def on_stage(self):
        k = self.slider.value()
        self.canvas.stage = k
        st = self.canvas.stages
        if not st:
            return
        self.stage_lbl.setText("Этап %d из 4: %s  (вершин: %d)" % (k, st[k][0], len(st[k][1])))
        lines = []
        for i, (name, poly) in enumerate(st):
            mark = "►" if i == k else " "
            lines.append("%s Этап %d — %s" % (mark, i, name))
            lines.append("     " + (", ".join(pt(x, y) for x, y in poly) if poly else "(пусто — многоугольник невидим)"))
        self.trace.setPlainText("\n".join(lines))
        self.canvas.update()

    def on_select(self):
        pass


# =============================================================================
#  ГЛАВНОЕ ОКНО
# =============================================================================
SEG_DEFAULT = [[-6, -2, 3, 5], [1, 1, 4, 3], [-8, 6, -5, 8], [-3, -7, 7, 7], [0, -6, 0, 6], [-7, 3, 9, 3]]
POLY_DEFAULT = [[-5, -1], [0, -6], [5, -2], [4, 5], [-2, 6]]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа 4 · вариант 5 — алгоритмы отсечения")
        self.resize(1400, 820)
        self.theme_name = "dark"
        th = THEMES["dark"]

        self.seg_model = Model(segs=SEG_DEFAULT)
        self.poly_model = Model(poly=POLY_DEFAULT, win=(-3, -3, 3, 3))

        self.tabs = QTabWidget()
        self.all = [
            SegTab(self.seg_model, th, "Часть 1 · Лианг-Барски",
                   "Параметрический отрезок P(t) = P1 + t(P2 − P1). Для каждой границы p·t ≤ q: при p<0 "
                   "t0 = max(t0, q/p), при p>0 t1 = min(t1, q/p). Если t0 > t1 — отрезок невидим.",
                   liang_barsky),
            PolyTab(self.poly_model, th),
        ]
        names = ["Часть 1 · Лианг-Барски", "Часть 2 · Многоугольник"]
        for tab, n in zip(self.all, names):
            self.tabs.addTab(tab, n)
            tab.canvas.hovered.connect(self.on_hover)
        self.setCentralWidget(self.tabs)

        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        act = QAction("☾ / ☀  Сменить тему", self)
        act.triggered.connect(self.toggle_theme)
        tb.addAction(act)
        hint = QLabel("  ЛКМ: тянуть точки/углы/окно · колесо: масштаб · ПКМ или пустое место: сдвиг")
        hint.setObjectName("hint")
        tb.addWidget(hint)
        self.status = self.statusBar()
        self.apply_theme()

    def on_hover(self, x, y):
        self.status.showMessage("x = %.2f   y = %.2f" % (x, y))

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.apply_theme()

    def apply_theme(self):
        th = THEMES[self.theme_name]
        QApplication.instance().setStyleSheet(build_qss(th))
        for tab in self.all:
            tab.set_theme(th)
            tab.refresh()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()