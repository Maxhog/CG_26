#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лабораторная работа 3 — Базовые растровые алгоритмы (PyQt6).
Пошаговый, ЦДА, Брезенхем (отрезок), Брезенхем (окружность).
Запуск:  pip install PyQt6  &&  python lab3.py
"""
import math
import sys
from time import perf_counter

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QPolygonF, QBrush
from PyQt6.QtWidgets import (
    QApplication, QFrame, QMainWindow, QWidget, QVBoxLayout, QFormLayout, QGroupBox, QComboBox,
    QSpinBox, QPushButton, QLabel, QCheckBox, QSlider, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QPlainTextEdit, QHeaderView, QAbstractItemView)


def rnd(v):
    """Округление «половина вверх» (round() в Python — банковское)."""
    return math.floor(v + 0.5)


# ===================== АЛГОРИТМЫ =====================

def step_by_step(x1, y1, x2, y2, log=None):
    """Пошаговый: y = k*x + b; шаг по более длинной оси."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        if log is not None:
            log.append((0, x1, y1, "—"))
        return [(x1, y1)], ["№", "x", "y", "—"], "Вырожденный отрезок: одна точка."
    steep = abs(dy) > abs(dx)
    a1, b1, a2 = (y1, x1, y2) if steep else (x1, y1, x2)
    da, db = (dy, dx) if steep else (dx, dy)
    A, B = ("y", "x") if steep else ("x", "y")
    k = db / da
    b = b1 - k * a1
    st = 1 if da > 0 else -1
    pts = []
    for i, a in enumerate(range(a1, a2 + st, st)):
        bf = k * a + b
        bb = rnd(bf)
        pts.append((bb, a) if steep else (a, bb))
        if log is not None:
            log.append((i, a, f"{bf:.4f}", bb))
    info = (f"Δx = {dx}, Δy = {dy}" + ("  (|Δy| > |Δx| — шагаем по y)" if steep else "") +
            f"\nk = Δ{B}/Δ{A} = {k:.6f}\nb = {B}1 − k·{A}1 = {b:.6f}\n"
            f"Шаг по {A} от {a1} до {a2}; {B} = round(k·{A} + b)")
    return pts, ["№", A, f"{B} = k·{A} + b", f"{B} (округл.)"], info


def dda(x1, y1, x2, y2, log=None):
    """ЦДА: L = max(|Δx|,|Δy|), приращения Δx/L, Δy/L накапливаются в float."""
    dx, dy = x2 - x1, y2 - y1
    L = max(abs(dx), abs(dy))
    sx, sy = (dx / L, dy / L) if L else (0.0, 0.0)
    x, y = float(x1), float(y1)
    pts = []
    for i in range(L + 1):
        p = (rnd(x), rnd(y))
        pts.append(p)
        if log is not None:
            log.append((i, f"{x:.4f}", f"{y:.4f}", p[0], p[1]))
        x += sx
        y += sy
    info = (f"Δx = {dx}, Δy = {dy}\nL = max(|Δx|,|Δy|) = {L}\nsx = Δx/L = {sx:.6f}\nsy = Δy/L = {sy:.6f}\n"
            f"Точка = (round(x), round(y)), затем x += sx, y += sy")
    return pts, ["№", "x", "y", "X = round(x)", "Y = round(y)"], info


def bresenham(x1, y1, x2, y2, log=None):
    """Брезенхем (отрезок): целые числа, все октанты. err = dx + dy, e2 = 2·err."""
    dx, dy = abs(x2 - x1), -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    info = (f"dx = |Δx| = {dx}, dy = −|Δy| = {dy}, sx = {sx}, sy = {sy}\nerr₀ = dx + dy = {err}\n"
            f"e2 = 2·err;  если e2 ≥ dy: err += dy, x += sx;  если e2 ≤ dx: err += dx, y += sy")
    pts, x, y, i = [], x1, y1, 0
    while True:
        pts.append((x, y))
        e2 = 2 * err
        if log is not None:
            st = ("шаг по x " if e2 >= dy else "") + ("шаг по y" if e2 <= dx else "")
            log.append((i, x, y, err, e2, st.strip()))
        if x == x2 and y == y2:
            break
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
        i += 1
    return pts, ["№", "x", "y", "err", "e2 = 2·err", "следующий шаг"], info


def bresenham_circle(cx, cy, r, log=None):
    """Брезенхем (окружность): 1 октант (x ≤ y) + симметрия. d₀ = 3 − 2R."""
    r = max(0, r)
    x, y, d = 0, r, 3 - 2 * r
    pts, seen, i = [], set(), 0
    while x <= y:
        for px, py in ((x, y), (y, x), (-x, y), (-y, x), (x, -y), (y, -x), (-x, -y), (-y, -x)):
            p = (cx + px, cy + py)
            if p not in seen:
                seen.add(p)
                pts.append(p)
        if log is not None:
            log.append((i, x, y, d, f"({cx + x}, {cy + y})",
                        "d < 0: (x+1, y), d += 4x+6" if d < 0 else "d ≥ 0: (x+1, y−1), d += 4(x−y)+10"))
        if d < 0:
            d += 4 * x + 6
        else:
            d += 4 * (x - y) + 10
            y -= 1
        x += 1
        i += 1
    info = (f"Центр ({cx}, {cy}), R = {r}\nСтарт: x = 0, y = R = {r}, d₀ = 3 − 2R = {3 - 2 * r}\n"
            f"d < 0: d += 4x + 6;  d ≥ 0: d += 4(x − y) + 10, y −= 1;  затем x += 1\n"
            f"Считается 1-й октант (x ≤ y), остальные 7 — симметрией (±x,±y), (±y,±x)")
    return pts, ["№", "x", "y", "d", "точка октанта", "решение"], info


ALGOS = {
    "Пошаговый алгоритм": (step_by_step, "line", QColor(46, 110, 230)),
    "ЦДА": (dda, "line", QColor(40, 160, 70)),
    "Брезенхем (отрезок)": (bresenham, "line", QColor(255, 127, 14)),
    "Брезенхем (окружность)": (bresenham_circle, "circle", QColor(148, 80, 190)),
}

# ===================== ХОЛСТ =====================

class Canvas(QWidget):
    scaleChanged = pyqtSignal(float)
    hovered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.scale, self.off = 30.0, QPointF(0, 0)
        self.layers, self.ideal = [], None
        self.show_ideal = self.show_grid = self.show_nums = True
        self._drag = None

    def sx(self, x): return self.width() / 2 + self.off.x() + x * self.scale
    def sy(self, y): return self.height() / 2 + self.off.y() - y * self.scale

    def to_world(self, px, py):
        return ((px - self.width() / 2 - self.off.x()) / self.scale,
                -(py - self.height() / 2 - self.off.y()) / self.scale)

    def set_data(self, layers, ideal):
        self.layers, self.ideal = layers, ideal
        self.update()

    def fit(self):
        pts = [p for l in self.layers for p in l[1]]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            w, h = max(max(xs) - min(xs) + 5, 8), max(max(ys) - min(ys) + 5, 8)
            s = max(4.0, min(90.0, self.width() / w, self.height() / h))
            self.scale = s
            self.off = QPointF(-(max(xs) + min(xs)) / 2 * s, (max(ys) + min(ys)) / 2 * s)
            self.scaleChanged.emit(s)
        self.update()

    def zoom_to(self, ns, anchor=None):
        ns = max(4.0, min(120.0, float(ns)))
        anchor = anchor or QPointF(self.width() / 2, self.height() / 2)
        wx, wy = self.to_world(anchor.x(), anchor.y())
        self.scale = ns
        self.off = QPointF(anchor.x() - self.width() / 2 - wx * ns, anchor.y() - self.height() / 2 + wy * ns)
        self.scaleChanged.emit(ns)
        self.update()

    def wheelEvent(self, e):
        self.zoom_to(self.scale * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15), e.position())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position()

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.off += pos - self._drag
            self._drag = pos
            self.update()
        wx, wy = self.to_world(pos.x(), pos.y())
        self.hovered.emit(f"Клетка: ({rnd(wx)}, {rnd(wy)})    точка плоскости: ({wx:.2f}; {wy:.2f})")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, s = self.width(), self.height(), self.scale
        p.fillRect(self.rect(), QColor(255, 255, 255))
        xmin, xmax = math.floor(self.to_world(0, 0)[0]) - 1, math.ceil(self.to_world(w, 0)[0]) + 1
        ymax, ymin = math.ceil(self.to_world(0, 0)[1]) + 1, math.floor(self.to_world(0, h)[1]) - 1

        if self.show_grid and s >= 6:
            p.setPen(QPen(QColor(210, 210, 210), 1))
            for k in range(xmin, xmax + 1):
                p.drawLine(QPointF(self.sx(k + .5), 0), QPointF(self.sx(k + .5), h))
            for k in range(ymin, ymax + 1):
                p.drawLine(QPointF(0, self.sy(k + .5)), QPointF(w, self.sy(k + .5)))

        p.setPen(Qt.PenStyle.NoPen)
        n = len(self.layers)
        # клетка -> цвета всех фигур, проходящих через неё (цвета не перекрываются, а делят клетку на полосы)
        cells = {}
        for _, pts, col in self.layers:
            for x, y in pts:
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    cells.setdefault((x, y), []).append(col)
        for (x, y), cols in cells.items():
            k = len(cols)
            for i, col in enumerate(cols):
                p.setBrush(QBrush(col))
                p.drawRect(QRectF(self.sx(x) - s / 2 + i * s / k, self.sy(y) - s / 2, s / k, s))

        if self.show_nums and n == 1 and s >= 30 and len(self.layers[0][1]) <= 400:
            f = QFont(p.font())
            f.setPointSizeF(max(6.0, min(11.0, s / 4)))
            p.setFont(f)
            p.setPen(QColor(255, 255, 255))
            for i, (x, y) in enumerate(self.layers[0][1]):
                p.drawText(QRectF(self.sx(x) - s / 2, self.sy(y) - s / 2, s, s), Qt.AlignmentFlag.AlignCenter, str(i))
            p.setFont(QFont())

        if self.show_ideal and self.ideal:
            p.setPen(QPen(QColor(225, 40, 40), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if self.ideal[0] == "line":
                _, a, b, c, d = self.ideal
                p.drawLine(QPointF(self.sx(a), self.sy(b)), QPointF(self.sx(c), self.sy(d)))
            else:
                _, a, b, r = self.ideal
                p.drawEllipse(QPointF(self.sx(a), self.sy(b)), r * s, r * s)

        ax, ay = self.sx(0), self.sy(0)
        p.setPen(QPen(QColor(0, 0, 0), 1.6))
        p.drawLine(QPointF(0, ay), QPointF(w, ay))
        p.drawLine(QPointF(ax, 0), QPointF(ax, h))
        p.setBrush(QColor(0, 0, 0))
        ayc, axc = min(max(ay, 8), h - 8), min(max(ax, 8), w - 8)
        p.drawPolygon(QPolygonF([QPointF(w - 2, ayc), QPointF(w - 12, ayc - 4), QPointF(w - 12, ayc + 4)]))
        p.drawPolygon(QPolygonF([QPointF(axc, 2), QPointF(axc - 4, 12), QPointF(axc + 4, 12)]))

        fm = p.fontMetrics()
        step = next((st for st in (1, 2, 5, 10, 20, 50, 100, 200, 500) if st * s >= 34), 500)
        p.setPen(QColor(0, 0, 0))
        ly = min(max(ay + 15, 14), h - 4)
        for k in range(xmin, xmax + 1):
            if k % step == 0:
                X = self.sx(k)
                p.drawLine(QPointF(X, ay - 3), QPointF(X, ay + 3))
                if k:
                    p.drawText(QPointF(X - fm.horizontalAdvance(str(k)) / 2, ly), str(k))
        for k in range(ymin, ymax + 1):
            if k % step == 0:
                Y = self.sy(k)
                p.drawLine(QPointF(ax - 3, Y), QPointF(ax + 3, Y))
                if k:
                    tw = fm.horizontalAdvance(str(k))
                    p.drawText(QPointF(min(max(ax - 7 - tw, 2), w - tw - 2), Y + 4), str(k))
        p.drawText(QPointF(min(max(ax - 14, 2), w - 14), ly), "0")
        bf = QFont(p.font())
        bf.setBold(True)
        p.setFont(bf)
        p.drawText(QPointF(w - 16, max(ayc - 8, 12)), "x")
        p.drawText(QPointF(min(axc + 10, w - 12), 14), "y")

        p.end()


# ===================== ГЛАВНОЕ ОКНО =====================

class MainWindow(QMainWindow):
    BENCH_SIZES = [10, 100, 1000, 10000]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа 3 — Базовые растровые алгоритмы")
        self.resize(1350, 880)
        
        # Хранилище для нескольких фигур
        self.drawn_objects = []

        self.canvas = Canvas()
        self.lbl_time = QLabel("Время: —")
        self.lbl_coord = QLabel("Клетка: —")
        for lb, wd in ((self.lbl_time, 260), (self.lbl_coord, 420)):
            lb.setMinimumWidth(wd)
            lb.setFrameShape(QFrame.Shape.StyledPanel)
            lb.setContentsMargins(6, 2, 6, 2)
            self.statusBar().addWidget(lb)
        self.canvas.hovered.connect(self.lbl_coord.setText)
        self.canvas.scaleChanged.connect(self.sync_slider)

        self.combo = QComboBox()
        self.combo.addItems(ALGOS.keys())
        self.combo.currentTextChanged.connect(self.on_algo_changed)

        def spin(v, lo=-500, hi=500):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(v)
            return s

        self.x1, self.y1, self.x2, self.y2, self.rr = spin(0), spin(0), spin(4), spin(1), spin(8, 0, 500)
        self.lbls = [QLabel(t) for t in ("Начало X1:", "Начало Y1:", "Конец X2:", "Конец Y2:", "Радиус R:")]
        form = QFormLayout()
        for lab, w in zip(self.lbls, (self.x1, self.y1, self.x2, self.y2, self.rr)):
            form.addRow(lab, w)
        
        g_alg = QGroupBox("Алгоритм")
        la = QVBoxLayout(g_alg)
        la.addWidget(self.combo)

        g_par = QGroupBox("Параметры (целые координаты)")
        g_par.setLayout(form)

        # Кнопки управления добавлением и очисткой
        btn_add = QPushButton("Добавить на холст")
        btn_add.setStyleSheet("font-weight:bold; padding:6px; background-color: #e6f2ff;")
        btn_add.clicked.connect(self.add_shape)

        btn_clear = QPushButton("Очистить всё")
        btn_clear.setStyleSheet("padding:4px;")
        btn_clear.clicked.connect(self.clear_shapes)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(4, 120)
        self.slider.setValue(30)
        self.slider.valueChanged.connect(lambda v: self.canvas.zoom_to(v))
        
        self.scale_lbl = QLabel()
        self.scale_lbl.setWordWrap(True)
        
        g_view = QGroupBox("Вид")
        lv = QVBoxLayout(g_view)
        lv.addWidget(self.scale_lbl)
        lv.addWidget(self.slider)
        for text, attr in (("Идеальная линия/окружность", "show_ideal"), ("Линии сетки", "show_grid"),
                           ("Номера пикселей (крупный масштаб)", "show_nums")):
            c = QCheckBox(text)
            c.setChecked(True)
            c.toggled.connect(lambda v, a=attr: (setattr(self.canvas, a, v), self.canvas.update()))
            lv.addWidget(c)

        left = QWidget()
        ll = QVBoxLayout(left)
        for w in (g_alg, g_par, btn_add, btn_clear, g_view):
            ll.addWidget(w)
        ll.addStretch(1)
        left.setFixedWidth(370)

        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(190)
        self.info.setFont(QFont("Consolas", 10))
        
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        tab1 = QWidget()
        t1 = QVBoxLayout(tab1)
        t1.addWidget(self.info)
        t1.addWidget(self.table)

        self.bench_table = QTableWidget()
        self.bench_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        btn_bench = QPushButton("Измерить время всех алгоритмов")
        btn_bench.clicked.connect(self.run_benchmark)
        
        tab2 = QWidget()
        t2 = QVBoxLayout(tab2)
        for w in (btn_bench, self.bench_table):
            t2.addWidget(w)
            
        tabs = QTabWidget()
        tabs.addTab(tab1, "Сопроводительные вычисления")
        tabs.addTab(tab2, "Временные характеристики")

        vs = QSplitter(Qt.Orientation.Vertical)
        vs.addWidget(self.canvas)
        vs.addWidget(tabs)
        vs.setStretchFactor(0, 3)
        vs.setStretchFactor(1, 2)
        
        main = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(left)
        main.addWidget(vs)
        main.setStretchFactor(1, 1)
        self.setCentralWidget(main)
        
        self.on_algo_changed(self.combo.currentText())
        # Строим первую фигуру по умолчанию при запуске
        self.add_shape()

    def sync_slider(self, s):
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(s)))
        self.slider.blockSignals(False)
        self.scale_lbl.setText(f"Масштаб: {s:.0f} px/клетка")

    def on_algo_changed(self, name):
        circle = ALGOS[name][1] == "circle"
        self.lbls[0].setText("Центр X:" if circle else "Начало X1:")
        self.lbls[1].setText("Центр Y:" if circle else "Начало Y1:")
        for w in (self.lbls[2], self.x2, self.lbls[3], self.y2):
            w.setEnabled(not circle)
        for w in (self.lbls[4], self.rr):
            w.setEnabled(circle)

    def add_shape(self):
        """Добавляет новую фигуру в список отображения и вычисляет её параметры."""
        name = self.combo.currentText()
        func, kind, col = ALGOS[name]
        
        if kind == "line":
            args = (self.x1.value(), self.y1.value(), self.x2.value(), self.y2.value())
            ideal = ("line",) + args
        else:
            args = (self.x1.value(), self.y1.value(), self.rr.value())
            ideal = ("circle",) + args

        log = []
        pts, hdr, info = func(*args, log=log)
        
        # Замер времени выполнения
        reps = 300
        t0 = perf_counter()
        for _ in range(reps):
            func(*args)
        us = (perf_counter() - t0) / reps * 1e6
        self.lbl_time.setText(f"Время: {us:.2f} мкс")

        # Сохраняем объект в общую коллекцию
        layer_name = f"{name} #{len(self.drawn_objects) + 1}"
        self.drawn_objects.append({
            "layer": (layer_name, pts, col),
            "ideal": ideal,
            "info": info,
            "hdr": hdr,
            "log": log
        })

        self.update_canvas_display()

    def clear_shapes(self):
        """Очищает все нарисованные фигуры с холста."""
        self.drawn_objects.clear()
        self.canvas.set_data([], None)
        self.info.clear()
        self.table.clear()
        self.lbl_time.setText("Время: —")

    def update_canvas_display(self):
        """Передает все накопленные слои на холст и обновляет таблицу шагов для последней фигуры."""
        if not self.drawn_objects:
            return

        layers = [obj["layer"] for obj in self.drawn_objects]
        last_obj = self.drawn_objects[-1]

        # Передаем все слои на холст, а идеальную линию — от последнего объекта
        self.canvas.set_data(layers, last_obj["ideal"])

        # Выводим аналитику и таблицу для последнего добавленного алгоритма
        self.info.setPlainText(last_obj["info"])
        self.table.clear()
        self.table.setColumnCount(len(last_obj["hdr"]))
        self.table.setHorizontalHeaderLabels(last_obj["hdr"])
        self.table.setRowCount(min(len(last_obj["log"]), 5000))
        for r, row in enumerate(last_obj["log"][:5000]):
            for c, v in enumerate(row):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, it)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def run_benchmark(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            names = list(ALGOS)
            self.bench_table.clear()
            self.bench_table.setRowCount(len(names))
            self.bench_table.setColumnCount(len(self.BENCH_SIZES))
            self.bench_table.setHorizontalHeaderLabels([f"n = {n}" for n in self.BENCH_SIZES])
            self.bench_table.setVerticalHeaderLabels(names)
            for r, name in enumerate(names):
                func, kind, _ = ALGOS[name]
                for c, n in enumerate(self.BENCH_SIZES):
                    args = (0, 0, n, int(n * 0.6)) if kind == "line" else (0, 0, n)
                    reps = max(5, 100000 // n)
                    t0 = perf_counter()
                    for _ in range(reps):
                        func(*args)
                    txt = f"{(perf_counter() - t0) / reps * 1e6:.1f} мкс"
                    it = QTableWidgetItem(txt)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.bench_table.setItem(r, c, it)
                    QApplication.processEvents()
            self.bench_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        finally:
            QApplication.restoreOverrideCursor()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())