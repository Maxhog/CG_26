import math
import tkinter as tk
from tkinter import colorchooser


def jround(x):
    """Округление как Math.round в Java (половина вверх), а не банковское."""
    return int(math.floor(x + 0.5))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ======================= Модели =======================

class RGBModel:
    """r, g, b — целые 0..255."""

    def __init__(self, r, g, b):
        self.r = clamp(int(r), 0, 255)
        self.g = clamp(int(g), 0, 255)
        self.b = clamp(int(b), 0, 255)

    def to_cmyk(self):
        """-> (c, m, y, k), все 0..1."""
        rn, gn, bn = self.r / 255.0, self.g / 255.0, self.b / 255.0
        k = min(1 - rn, 1 - gn, 1 - bn)
        if k >= 1.0:                      # чистый чёрный
            return 0.0, 0.0, 0.0, 1.0
        c = (1 - rn - k) / (1 - k)
        m = (1 - gn - k) / (1 - k)
        y = (1 - bn - k) / (1 - k)
        return c, m, y, k

    def to_hls(self):
        """-> (h 0..360, s 0..1, l 0..1)."""
        rn, gn, bn = self.r / 255.0, self.g / 255.0, self.b / 255.0
        mx, mn = max(rn, gn, bn), min(rn, gn, bn)
        l = (mx + mn) / 2.0
        if mx == mn:
            return 0.0, 0.0, l
        d = mx - mn
        s = d / (mx + mn) if l < 0.5 else d / (2.0 - mx - mn)
        if mx == rn:
            h = (gn - bn) / d + (6 if gn < bn else 0)
        elif mx == gn:
            h = (bn - rn) / d + 2
        else:
            h = (rn - gn) / d + 4
        return h * 60.0, s, l


class CMYKModel:
    """c, m, y, k — 0..1."""

    def __init__(self, c, m, y, k):
        self.c = clamp(c, 0.0, 1.0)
        self.m = clamp(m, 0.0, 1.0)
        self.y = clamp(y, 0.0, 1.0)
        self.k = clamp(k, 0.0, 1.0)

    def to_rgb(self):
        r = jround(255 * (1 - self.c) * (1 - self.k))
        g = jround(255 * (1 - self.m) * (1 - self.k))
        b = jround(255 * (1 - self.y) * (1 - self.k))
        return clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255)

    def to_hls(self):
        return RGBModel(*self.to_rgb()).to_hls()


class HLSModel:
    """h — 0..360, s и l — 0..1."""

    def __init__(self, h, s, l):
        self.h = ((h % 360) + 360) % 360
        self.s = clamp(s, 0.0, 1.0)
        self.l = clamp(l, 0.0, 1.0)

    def to_rgb(self):
        l, s = self.l, self.s
        m2 = l * (1 + s) if l <= 0.5 else (l + s - l * s)
        m1 = 2 * l - m2
        r = jround(255 * self._value(self.h + 120, m1, m2))
        g = jround(255 * self._value(self.h, m1, m2))
        b = jround(255 * self._value(self.h - 120, m1, m2))
        return clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255)

    def to_cmyk(self):
        return RGBModel(*self.to_rgb()).to_cmyk()

    @staticmethod
    def _value(h, m1, m2):
        h = ((h % 360) + 360) % 360
        if h < 60:
            return m1 + (m2 - m1) * h / 60.0
        if h < 180:
            return m2
        if h < 240:
            return m1 + (m2 - m1) * (240 - h) / 60.0
        return m1


# ======================= Приложение =======================

SRC_NONE, SRC_RGB, SRC_CMYK, SRC_HLS = "none", "rgb", "cmyk", "hls"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Цветовые модели: RGB / CMYK / HLS")
        self.geometry("820x660")

        self.updating = False        # флаг против рекурсивных вызовов
        self.last_h = 0.0            # последние известные H и S — нужны, когда
        self.last_s = 1.0            # из RGB их восстановить нельзя
        self._last = {}              # последнее известное значение каждого ползунка

        # Каждая группа: списки StringVar (поля) и Scale (ползунки)
        self.rgb_f, self.rgb_s = self._make_panel(
            "RGB (0..255)",
            [("R:", 255), ("G:", 255), ("B:", 255)],
            lambda ff, i: self._on_rgb(ff, i))
        self.cmyk_f, self.cmyk_s = self._make_panel(
            "CMYK (0..100 %)",
            [("C:", 100), ("M:", 100), ("Y:", 100), ("K:", 100)],
            lambda ff, i: self._on_cmyk(ff, i))
        self.hls_f, self.hls_s = self._make_panel(
            "HLS (H:0..360, S и L:0..100 %)",
            [("H:", 360), ("S:", 100), ("L:", 100)],
            lambda ff, i: self._on_hls(ff, i))

        # Предпросмотр и кнопка палитры
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=10)

        self.preview = tk.Frame(bottom, height=100, bd=2, relief="solid")
        self.preview.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(bottom, text="Выбрать цвет из палитры",
                  command=self._pick_color).pack(side="right")

        self._from_rgb(255, 0, 0, SRC_NONE, False)   # начальный цвет — красный

    # ---------- Построение панелей ----------

    def _make_panel(self, title, rows, handler):
        frame = tk.LabelFrame(self, text=title, padx=5, pady=5)
        frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        frame.columnconfigure(2, weight=1)

        fields, sliders = [], []
        for i, (label, mx) in enumerate(rows):
            tk.Label(frame, text=label).grid(row=i, column=0, padx=5, pady=2)

            var = tk.StringVar()
            var.trace_add("write", lambda *_, i=i: (not self.updating) and handler(True, i))
            tk.Entry(frame, textvariable=var, width=7).grid(row=i, column=1, padx=5)

            sc = tk.Scale(frame, from_=0, to=mx, orient="horizontal", showvalue=False)
            sc.configure(command=lambda v, sc=sc, i=i: self._slider_cmd(sc, v, handler, i))
            sc.grid(row=i, column=2, sticky="ew", padx=5)
            self._last[sc] = 0

            fields.append(var)
            sliders.append(sc)
        return fields, sliders

    # ---------- Ползунки ----------

    def _slider_cmd(self, sc, val, handler, idx):
        """Реагируем только на ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ. Tk вызывает command и после
        программного sc.set(), причём позже (когда флаг updating уже снят) —
        поэтому сравниваем с последним значением, которое выставили мы сами."""
        v = int(float(val))
        if self._last.get(sc) == v:
            return
        self._last[sc] = v
        if not self.updating:
            handler(False, idx)

    def _set_scale(self, sc, v):
        self._last[sc] = v      # запоминаем ДО set: отложенный command будет проигнорирован
        sc.set(v)

    # ---------- Обработчики ввода ----------

    @staticmethod
    def _num(var):
        return float(var.get().strip().replace(",", "."))

    def _read(self, fields, sliders, scales, from_field, idx):
        """Значения группы. Если двигают ползунок idx, то он берётся с ползунка,
        а остальные компоненты — точные значения из полей (а не округлённые ползунки)."""
        vals = []
        for i, (var, sc, k) in enumerate(zip(fields, sliders, scales)):
            if from_field or i != idx:
                try:
                    vals.append(self._num(var) / k)
                    continue
                except ValueError:
                    if from_field:
                        raise
            vals.append(sc.get() / k)
        return vals

    def _on_rgb(self, from_field, idx):
        try:
            if from_field:
                r, g, b = (jround(self._num(v)) for v in self.rgb_f)
            else:
                r, g, b = (s.get() for s in self.rgb_s)
            self._from_rgb(r, g, b, SRC_RGB, from_field)
        except ValueError:
            pass   # пользователь ещё печатает

    def _on_cmyk(self, from_field, idx):
        try:
            c, m, y, k = self._read(self.cmyk_f, self.cmyk_s, (100,) * 4, from_field, idx)
            cm = CMYKModel(c, m, y, k)
            rgb = cm.to_rgb()
            hls = self._fix_hls(RGBModel(*rgb).to_hls())
            self._apply(rgb, (cm.c, cm.m, cm.y, cm.k), hls, SRC_CMYK, from_field)
        except ValueError:
            pass

    def _on_hls(self, from_field, idx):
        try:
            h, s, l = self._read(self.hls_f, self.hls_s, (1, 100, 100), from_field, idx)
            hm = HLSModel(h, s, l)
            rgb = hm.to_rgb()
            cmyk = RGBModel(*rgb).to_cmyk()
            # Используем введённые пользователем H,S,L, а не восстановленные из RGB
            self._apply(rgb, cmyk, (hm.h, hm.s, hm.l), SRC_HLS, from_field)
        except ValueError:
            pass

    def _pick_color(self):
        _, hex_color = colorchooser.askcolor(color=self._hex(self.preview["bg"]),
                                             title="Выбор цвета", parent=self)
        if hex_color:
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
            self._from_rgb(r, g, b, SRC_NONE, False)

    @staticmethod
    def _hex(color):
        return color if color.startswith("#") else "#ff0000"

    # ---------- Обновление ----------

    def _from_rgb(self, r, g, b, src, from_field):
        rgb = RGBModel(r, g, b)   # внутри делает clamp
        self._apply((rgb.r, rgb.g, rgb.b), rgb.to_cmyk(),
                    self._fix_hls(rgb.to_hls()), src, from_field)

    def _fix_hls(self, hls):
        """Если H или S из RGB восстановить нельзя (серый/чёрный/белый) — берём прошлые."""
        h, s, l = hls
        if l < 1e-9 or l > 1 - 1e-9:
            h, s = self.last_h, self.last_s
        elif s < 1e-9:
            h = self.last_h
        return h, s, l

    def _apply(self, rgb, cmyk, hls, src, from_field):
        """Обновляет все элементы, КРОМЕ той части группы-источника, которую
        пользователь сейчас редактирует (иначе поле/ползунок «убегает»)."""
        if self.updating:
            return
        self.updating = True
        try:
            self.last_h, self.last_s = hls[0], hls[1]

            def fill(group, fields, sliders, text_vals, slider_vals):
                upd_fields = not (src == group and from_field)
                upd_sliders = not (src == group and not from_field)
                if upd_fields:
                    for var, t in zip(fields, text_vals):
                        var.set(t)
                if upd_sliders:
                    for sc, v in zip(sliders, slider_vals):
                        self._set_scale(sc, v)

            fill(SRC_RGB, self.rgb_f, self.rgb_s,
                 [str(v) for v in rgb], list(rgb))

            fill(SRC_CMYK, self.cmyk_f, self.cmyk_s,
                 [self._fmt(v * 100) for v in cmyk],
                 [jround(v * 100) for v in cmyk])

            fill(SRC_HLS, self.hls_f, self.hls_s,
                 [self._fmt(hls[0]), self._fmt(hls[1] * 100), self._fmt(hls[2] * 100)],
                 [jround(hls[0]), jround(hls[1] * 100), jround(hls[2] * 100)])

            self.preview.configure(bg="#%02x%02x%02x" % tuple(rgb))
        finally:
            self.updating = False

    @staticmethod
    def _fmt(v):
        return f"{v:.1f}"


if __name__ == "__main__":
    App().mainloop()