"""Лабораторная работа 2, вариант 5.

Строка 1 таблицы : построение и эквализация гистограммы + линейное контрастирование
Столбец 5        : нелинейные фильтры на порядковых статистиках (медиана, min, max)

Управление изображением:
    колесо мыши            — зум (в точке курсора, все панели масштабируются синхронно)
    ЛКМ + перетаскивание   — сдвиг изображения
    двойной щелчок ЛКМ     — вернуть весь кадр
    панель под меню        — лупа (зум рамкой), «крестик» (сдвиг), домик (сброс)
"""
import os
import tkinter as tk
from enum import Enum
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(HERE, "test_images")  # можно и просто положить картинки рядом со скриптом
MAX_SIDE = 640  # большие кадры уменьшаются: фильтр с окном 15x15 на полном кадре слишком тяжёлый


# ───────────────────────── ТЕСТОВАЯ БАЗА ─────────────────────────
class ImageKind(Enum):
    """(имя файла, подпись в списке, операция, окно, p_low, p_high)."""
    NORMAL = ("normal.png", "Нормальное (эталон)", "Сравнение: линейное vs эквализация", 3, 0, 100)
    SALT_PEPPER = ("salt_pepper.png", "Шум «соль и перец»", "Фильтр порядковой статистики", 5, 0, 100)
    GAUSSIAN = ("gaussian_noise.png", "Гауссов шум", "Фильтр порядковой статистики", 3, 0, 100)
    BLURRED = ("blurred.png", "Размытое", "Сравнение всех фильтров", 3, 0, 100)
    DARK = ("low_contrast_dark.png", "Тёмное малоконтрастное", "Сравнение: линейное vs эквализация", 3, 1, 99)
    BRIGHT = ("low_contrast_bright.png", "Пересвеченное малоконтрастное", "Сравнение: линейное vs эквализация", 3, 1, 99)
    FOG = ("low_contrast_fog.png", "Серая дымка / туман", "Сравнение: линейное vs эквализация", 3, 1, 99)
    COLOR_LOW = ("color_low_contrast.png", "Цветное малоконтрастное", "Цвет: эквализация RGB vs HSV(V)", 3, 0, 100)
    FLAT = ("compress_best.png", "Плоские фигуры", "Сравнение всех фильтров", 5, 0, 100)
    BLOCK_NOISE = ("compress_worst.png", "Блочный цветной шум", "Сравнение всех фильтров", 3, 0, 100)

    filename = property(lambda self: self.value[0])
    label = property(lambda self: self.value[1])
    op = property(lambda self: self.value[2])
    size = property(lambda self: self.value[3])
    p_low = property(lambda self: self.value[4])
    p_high = property(lambda self: self.value[5])


OP_FILTER = "Фильтр порядковой статистики"
OP_FILTER_ALL = "Сравнение всех фильтров"
OP_LINEAR = "Линейное контрастирование"
OP_EQ = "Эквализация гистограммы"
OP_CMP = "Сравнение: линейное vs эквализация"
OP_COLOR = "Цвет: эквализация RGB vs HSV(V)"
OPERATIONS = [OP_FILTER, OP_FILTER_ALL, OP_LINEAR, OP_EQ, OP_CMP, OP_COLOR]

FILTERS = {
    "Медианный": "median",
    "Минимум (эрозия)": "min",
    "Максимум (дилатация)": "max",
}


def find_image(filename):
    for folder in (TEST_DIR, HERE):
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
    return None


# ───────────────────────── АЛГОРИТМЫ ─────────────────────────
def rank_filter_channel(ch, size, mode):
    """Фильтр порядковой статистики для одного канала (uint8, 2D).

    Для каждого пикселя берём окно size x size, строим вариационный ряд
    (значения по возрастанию) и берём: median — средний, min — первый, max — последний.
    """
    p = np.pad(ch, size // 2, mode="edge")  # края «продлеваем» ближайшими пикселями
    win = sliding_window_view(p, (size, size)).reshape(ch.shape[0], ch.shape[1], -1)
    n = win.shape[-1]
    match mode:
        case "median":
            return np.partition(win, n // 2, axis=-1)[..., n // 2]
        case "min":
            return win.min(axis=-1)
        case "max":
            return win.max(axis=-1)
    raise ValueError(mode)


def hist(ch):
    return np.bincount(ch.ravel(), minlength=256)


def equalize_channel(ch):
    """Эквализация: s = round((CDF(r) - CDF_min) / (N - CDF_min) * 255)."""
    cdf = hist(ch).cumsum()
    cdf_min = cdf[cdf > 0][0]
    n = ch.size
    if n == cdf_min:  # константное изображение
        return ch
    lut = np.round((cdf - cdf_min) / (n - cdf_min) * 255).clip(0, 255).astype(np.uint8)
    return lut[ch]


def linear_channel(ch, p_low=0.0, p_high=100.0):
    """Линейное растяжение: s = (r - lo) / (hi - lo) * 255 (lo, hi — процентили)."""
    lo, hi = np.percentile(ch, [p_low, p_high])
    if hi <= lo:
        return ch
    out = (ch.astype(np.float32) - lo) / (hi - lo) * 255
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def per_channel(im, fn):
    """Применить fn к каждому каналу отдельно (для RGB — к R, G, B)."""
    a = np.asarray(im)
    if a.ndim == 2:
        return Image.fromarray(fn(a))
    return Image.fromarray(np.stack([fn(a[..., c]) for c in range(3)], axis=-1))


def on_value(im, fn):
    """Применить fn только к яркости V в HSV (оттенок H и насыщенность S не трогаем)."""
    if im.mode == "L":
        return Image.fromarray(fn(np.asarray(im)))
    h, s, v = im.convert("HSV").split()
    v2 = Image.fromarray(fn(np.asarray(v)))
    return Image.merge("HSV", (h, s, v2)).convert("RGB")


def stats(im):
    g = np.asarray(im.convert("L"))
    return f"яркость: среднее={g.mean():6.1f}   σ (контраст)={g.std():6.1f}   диапазон={g.min()}…{g.max()}"


# ───────────────────────── ПРИЛОЖЕНИЕ ─────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("Лаба 2, вариант 5: гистограмма, контраст, фильтры порядковых статистик")
        self.orig = None   # загруженное изображение
        self.last = None   # последний результат (для сохранения)
        self.img_axes = []  # оси с картинками (у них общий масштаб)
        self.size_px = (1, 1)  # (ширина, высота) картинки
        self._drag = None

        top = ttk.Frame(root, padding=4)
        top.pack(fill="x")

        r0 = ttk.Frame(top)
        r0.pack(fill="x", pady=2)
        ttk.Label(r0, text="Тестовое изображение:").pack(side="left")
        self.cb_base = ttk.Combobox(r0, state="readonly", width=34, values=[k.label for k in ImageKind])
        self.cb_base.pack(side="left", padx=4)
        self.cb_base.bind("<<ComboboxSelected>>", self.on_pick_base)
        ttk.Button(r0, text="Открыть файл…", command=self.open_file).pack(side="left", padx=2)
        ttk.Button(r0, text="Сохранить результат…", command=self.save).pack(side="left", padx=2)

        r1 = ttk.Frame(top)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Операция:").pack(side="left")
        self.cb_op = ttk.Combobox(r1, state="readonly", width=34, values=OPERATIONS)
        self.cb_op.current(0)
        self.cb_op.pack(side="left", padx=4)
        ttk.Label(r1, text="Фильтр:").pack(side="left")
        self.cb_f = ttk.Combobox(r1, state="readonly", width=22, values=list(FILTERS))
        self.cb_f.current(0)
        self.cb_f.pack(side="left", padx=4)

        r2 = ttk.Frame(top)
        r2.pack(fill="x", pady=2)
        self.v_size = tk.IntVar(value=3)
        self.v_pl = tk.DoubleVar(value=0.0)
        self.v_ph = tk.DoubleVar(value=100.0)
        for text, var, a, b, inc in [("Окно (нечёт.):", self.v_size, 3, 15, 2),
                                     ("p_low %:", self.v_pl, 0, 49, 1),
                                     ("p_high %:", self.v_ph, 51, 100, 1)]:
            ttk.Label(r2, text=text).pack(side="left")
            ttk.Spinbox(r2, textvariable=var, from_=a, to=b, increment=inc, width=6).pack(side="left", padx=(2, 10))
        ttk.Button(r2, text="▶ Выполнить", command=self.run).pack(side="left", padx=6)

        self.fig = Figure(figsize=(12, 5.6), dpi=90)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.toolbar = NavigationToolbar2Tk(self.canvas, root, pack_toolbar=False)
        self.toolbar.pack(fill="x")
        ttk.Label(root, foreground="gray",
                  text="Зум: колесо мыши • сдвиг: ЛКМ + перетаскивание • двойной щелчок — весь кадр").pack(anchor="w", padx=6)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.txt = tk.Text(root, height=6, font=("Consolas", 9))
        self.txt.pack(fill="x")

        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)

    # ---- загрузка ----
    def load(self, path):
        im = Image.open(path).convert("RGB")
        if max(im.size) > MAX_SIDE:
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        a = np.asarray(im)
        if np.array_equal(a[..., 0], a[..., 1]) and np.array_equal(a[..., 1], a[..., 2]):
            im = im.convert("L")  # серое изображение
        self.orig = im
        self.show([("Исходное", im)])

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")])
        if p:
            self.load(p)

    def on_pick_base(self, _=None):
        kind = list(ImageKind)[self.cb_base.current()]
        path = find_image(kind.filename)
        if path is None:
            messagebox.showwarning("Нет файла", f"Файл {kind.filename} не найден.\n"
                                                f"Положите его в папку «test_images» рядом со скриптом.")
            return
        self.load(path)
        # сразу подставляем подходящую операцию и параметры
        self.cb_op.set(kind.op)
        self.v_size.set(kind.size)
        self.v_pl.set(kind.p_low)
        self.v_ph.set(kind.p_high)

    # ---- отрисовка ----
    def show(self, items):
        self.fig.clear()
        self.img_axes = []
        n = len(items)
        self.txt.delete("1.0", "end")
        self.size_px = items[0][1].size
        for i, (title, im) in enumerate(items):
            first = self.img_axes[0] if self.img_axes else None
            ax = self.fig.add_subplot(2, n, i + 1, sharex=first, sharey=first)  # общий зум для всех картинок
            ax.imshow(im, cmap="gray" if im.mode == "L" else None, vmin=0, vmax=255)
            ax.set_title(title, fontsize=9)
            ax.axis("off")
            self.img_axes.append(ax)

            ax2 = self.fig.add_subplot(2, n, n + i + 1)
            a = np.asarray(im)
            if a.ndim == 2:
                ax2.bar(range(256), hist(a), width=1.0, color="gray")
            else:
                for c, col in enumerate("rgb"):
                    ax2.plot(hist(a[..., c]), color=col, lw=0.8)
            ax2.set_xlim(0, 255)
            ax2.set_title("гистограмма", fontsize=8)
            ax2.tick_params(labelsize=7)
            self.txt.insert("end", f"{title}:\n   {stats(im)}\n")
        self.fig.tight_layout()
        self.canvas.draw()
        self.toolbar.update()  # сбросить историю масштабов тулбара под новые оси
        self.last = items[-1][1]

    # ---- зум и сдвиг ----
    def set_view(self, xmin, xmax, ymin, ymax):
        """Выставить область просмотра, не выходя за границы картинки."""
        w, h = self.size_px
        if xmax - xmin >= w or ymax - ymin >= h:
            xmin, xmax, ymin, ymax = -0.5, w - 0.5, -0.5, h - 0.5
        wd, ht = xmax - xmin, ymax - ymin
        xmin = min(max(xmin, -0.5), w - 0.5 - wd)
        ymin = min(max(ymin, -0.5), h - 0.5 - ht)
        xmax, ymax = xmin + wd, ymin + ht
        ax = self.img_axes[0]  # остальные оси подтянутся сами (sharex/sharey)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymax, ymin)
        self.canvas.draw_idle()

    def reset_view(self):
        if self.img_axes:
            w, h = self.size_px
            self.set_view(-0.5, w - 0.5, -0.5, h - 0.5)

    def on_scroll(self, e):
        if e.inaxes not in self.img_axes or e.xdata is None:
            return
        k = 0.8 if e.button == "up" else 1.25  # колесо вверх — приблизить
        x0, x1 = sorted(e.inaxes.get_xlim())
        y0, y1 = sorted(e.inaxes.get_ylim())
        self.set_view(e.xdata - (e.xdata - x0) * k, e.xdata + (x1 - e.xdata) * k,
                      e.ydata - (e.ydata - y0) * k, e.ydata + (y1 - e.ydata) * k)

    def on_press(self, e):
        if e.inaxes not in self.img_axes or e.button != 1 or self.toolbar.mode:
            return
        if e.dblclick:
            self.reset_view()
            return
        ax = e.inaxes
        self._drag = (ax.transData.inverted().transform((e.x, e.y)), sorted(ax.get_xlim()), sorted(ax.get_ylim()),
                      ax.transData.inverted())

    def on_motion(self, e):
        if self._drag is None or e.x is None:
            return
        start, (x0, x1), (y0, y1), inv = self._drag
        cur = inv.transform((e.x, e.y))
        dx, dy = start[0] - cur[0], start[1] - cur[1]
        self.set_view(x0 + dx, x1 + dx, y0 + dy, y1 + dy)

    def on_release(self, _):
        self._drag = None

    # ---- выполнение ----
    def run(self):
        if self.orig is None:
            messagebox.showwarning("Нет изображения", "Выберите изображение из списка или откройте файл.")
            return
        src = self.orig
        size = int(self.v_size.get())
        size = size if size % 2 == 1 else size + 1
        pl, ph = float(self.v_pl.get()), float(self.v_ph.get())
        op = self.cb_op.get()

        def flt(m):
            return per_channel(src, lambda ch: rank_filter_channel(ch, size, m))

        def lin():
            return on_value(src, lambda c: linear_channel(c, pl, ph))

        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            match op:
                case "Фильтр порядковой статистики":
                    items = [("Исходное", src), (f"{self.cb_f.get()} {size}x{size}", flt(FILTERS[self.cb_f.get()]))]
                case "Сравнение всех фильтров":
                    items = [("Исходное", src), (f"Медиана {size}x{size}", flt("median")),
                             (f"Минимум {size}x{size}", flt("min")), (f"Максимум {size}x{size}", flt("max"))]
                case "Линейное контрастирование":
                    items = [("Исходное", src), (f"Линейное [{pl:g}%…{ph:g}%]", lin())]
                case "Эквализация гистограммы":
                    items = [("Исходное", src),
                             ("Эквализация" + ("" if src.mode == "L" else " (V в HSV)"), on_value(src, equalize_channel))]
                case "Сравнение: линейное vs эквализация":
                    items = [("Исходное", src), (f"Линейное [{pl:g}%…{ph:g}%]", lin()),
                             ("Эквализация", on_value(src, equalize_channel))]
                case "Цвет: эквализация RGB vs HSV(V)":
                    if src.mode == "L":
                        messagebox.showinfo("Серое изображение", "Для сравнения RGB и HSV нужно цветное изображение.")
                        return
                    items = [("Исходное", src), ("Эквализация R,G,B раздельно", per_channel(src, equalize_channel)),
                             ("Эквализация только V (HSV)", on_value(src, equalize_channel))]
                case _:
                    return
            self.show(items)
        finally:
            self.root.config(cursor="")

    def save(self):
        if self.last is None:
            return
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if p:
            self.last.save(p)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()