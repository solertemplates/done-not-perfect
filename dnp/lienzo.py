"""Primitivas de dibujo con antialiasing por sobremuestreo.

Se dibuja a ESCALA veces el tamaño final y luego se reduce; así las líneas
finas del decorado quedan suaves. Todas las coordenadas que reciben estas
funciones están en píxeles del vídeo final (1080x1920), relativas al panel.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ESCALA = 2

# Fondos permitidos: siempre MUY oscuros para que los personajes blancos resalten.
FONDOS = {
    "negro": (0x0E, 0x0F, 0x12),  # #0E0F12
    "azul_noche": (0x0D, 0x14, 0x24),  # #0D1424
    "marron_cafe": (0x1A, 0x13, 0x0E),  # #1A130E
    "gris_pizarra": (0x15, 0x18, 0x1C),  # #15181C
    "morado_oscuro": (0x17, 0x12, 0x22),  # #171222
}
FONDO = FONDOS["negro"]  # fondo por defecto (episodio 1)
_fondo_actual = [FONDO]


def fondo():
    """Color de fondo del episodio que se está dibujando."""
    return _fondo_actual[0]


def usar_fondo(color) -> None:
    _fondo_actual[0] = tuple(color)


BLANCO = (245, 245, 240)
VERDE = (64, 214, 128)  # logro / ahorro
ROJO = (236, 78, 78)  # fracaso / deuda
AMARILLO = (244, 196, 64)  # riesgo
AZUL = (80, 160, 255)  # IA
LUZ_LAMPARA = (0xFF, 0xC8, 0x73)  # ámbar cálido de ambiente (no es el amarillo de riesgo)
TINTA = (14, 15, 18)  # rasgos de la cara: iguales en todos los episodios


def mezcla(c1, c2, t: float):
    """Mezcla c1 hacia c2 (t=0 -> c1, t=1 -> c2)."""
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def tenue(alfa: float, color=BLANCO):
    """Color 'semitransparente' sobre el fondo (sin coste de alfa real)."""
    return mezcla(fondo(), color, alfa)


def rotar(p, centro, grados: float):
    a = math.radians(grados)
    x, y = p[0] - centro[0], p[1] - centro[1]
    return (centro[0] + x * math.cos(a) - y * math.sin(a), centro[1] + x * math.sin(a) + y * math.cos(a))


class Lienzo:
    def __init__(self, img: Image.Image, ox: float = 0, oy: float = 0, escala: int = ESCALA):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.ox, self.oy, self.s = ox, oy, escala

    def P(self, p):
        return ((p[0] + self.ox) * self.s, (p[1] + self.oy) * self.s)

    def linea(self, pts, ancho: float, color=BLANCO, puntas: bool = True):
        q = [self.P(p) for p in pts]
        w = max(1, int(round(ancho * self.s)))
        if len(q) >= 2:
            self.d.line(q, fill=color, width=w, joint="curve")
        if puntas and w > 2:
            r = w / 2
            for x, y in (q[0], q[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def circulo(self, c, r: float, relleno=None, borde=None, ancho: float = 0):
        x, y = self.P(c)
        rr = r * self.s
        self.d.ellipse(
            (x - rr, y - rr, x + rr, y + rr),
            fill=relleno,
            outline=borde,
            width=max(1, int(round(ancho * self.s))) if borde else 0,
        )

    def elipse(self, c, rx: float, ry: float, relleno=None, borde=None, ancho: float = 0):
        x, y = self.P(c)
        self.d.ellipse(
            (x - rx * self.s, y - ry * self.s, x + rx * self.s, y + ry * self.s),
            fill=relleno,
            outline=borde,
            width=max(1, int(round(ancho * self.s))) if borde else 0,
        )

    def poligono(self, pts, relleno=None, borde=None, ancho: float = 0):
        q = [self.P(p) for p in pts]
        if relleno is not None:
            self.d.polygon(q, fill=relleno)
        if borde is not None and ancho > 0:
            self.linea(list(pts) + [pts[0]], ancho, borde, puntas=False)

    def arco(self, c, r: float, desde: float, hasta: float, ancho: float, color=BLANCO, pasos: int = 24):
        pts = [
            (c[0] + r * math.cos(math.radians(desde + (hasta - desde) * i / pasos)),
             c[1] + r * math.sin(math.radians(desde + (hasta - desde) * i / pasos)))
            for i in range(pasos + 1)
        ]
        self.linea(pts, ancho, color)

    def boceto(self, p0, p1, ancho: float = 2.2, color=BLANCO, semilla: int = 0, amp: float = 1.6, doble: bool = True):
        """Línea con temblor de lápiz. La semilla fija el trazo: no 'hierve' entre fotogramas."""
        rnd = random.Random(semilla)
        largo = math.dist(p0, p1)
        n = max(2, int(largo / 60) + 2)
        nx, ny = (-(p1[1] - p0[1]) / (largo or 1), (p1[0] - p0[0]) / (largo or 1))
        def trazo(a):
            pts = []
            for i in range(n + 1):
                t = i / n
                off = rnd.uniform(-a, a) if 0 < i < n else rnd.uniform(-a, a) * 0.4
                pts.append((p0[0] + (p1[0] - p0[0]) * t + nx * off, p0[1] + (p1[1] - p0[1]) * t + ny * off))
            return pts
        self.linea(trazo(amp), ancho, color)
        if doble:
            ext = rnd.uniform(0.02, 0.06)
            a0 = (p0[0] - (p1[0] - p0[0]) * ext, p0[1] - (p1[1] - p0[1]) * ext)
            sub = trazo(amp * 1.4)
            sub[0] = a0
            self.linea(sub, ancho * 0.6, mezcla(color, fondo(), 0.55))

    def boceto_poli(self, pts, ancho: float = 2.2, color=BLANCO, semilla: int = 0, cerrado: bool = False, amp=1.6):
        pares = list(zip(pts, pts[1:] + ([pts[0]] if cerrado else [])))
        for i, (a, b) in enumerate(pares):
            self.boceto(a, b, ancho, color, semilla * 101 + i, amp)


# --- Texto ---------------------------------------------------------------------

_FUENTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


@lru_cache(maxsize=64)
def fuente(tamano_px: int) -> ImageFont.FreeTypeFont:
    for ruta in _FUENTES:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano_px)
    return ImageFont.load_default(size=tamano_px)


def texto(img: Image.Image, cadena_colores, centro, tamano: float, alfa: float = 1.0, escala: int = ESCALA,
          ancla: str = "mm"):
    """Dibuja texto (lista de (cadena, color)) con opacidad real, centrado en `centro`.

    Se compone con máscara para poder hacer fundidos sin dibujar todo en RGBA.
    """
    if alfa <= 0.003:
        return
    f = fuente(max(4, int(round(tamano * escala))))
    partes = [(c, col, f.getlength(c)) for c, col in cadena_colores]
    total = sum(w for _, _, w in partes)
    asc, desc = f.getmetrics()
    alto = asc + desc
    cx, cy = centro[0] * escala, centro[1] * escala
    x0 = cx - total / 2 if ancla[0] == "m" else (cx if ancla[0] == "l" else cx - total)
    y0 = cy - alto / 2
    margen = int(4 * escala)
    caja = (int(x0) - margen, int(y0) - margen, int(x0 + total) + margen, int(y0 + alto) + margen)
    w, h = caja[2] - caja[0], caja[3] - caja[1]
    x = x0 - caja[0]
    for cad, col, ancho in partes:
        mascara = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mascara).text((x, y0 - caja[1]), cad, font=f, fill=int(255 * min(1.0, alfa)))
        img.paste(col, caja, mascara)
        x += ancho
    return caja


def capa(img: Image.Image, caja, dibujar, alfa: float):
    """Dibuja con `dibujar(draw, x0, y0)` en una capa RGBA y la funde con opacidad `alfa`."""
    if alfa <= 0.003:
        return
    x0, y0, x1, y1 = (int(v) for v in caja)
    c = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    dibujar(ImageDraw.Draw(c), x0, y0)
    if alfa < 1:
        a = c.getchannel("A").point(lambda v: int(v * alfa))
        c.putalpha(a)
    img.paste(c.convert("RGB"), (x0, y0), c.getchannel("A"))
