"""Degradado RADIAL de los fondos: centro de color vivo y bordes oscuros (hasta #000000).

Todo se dibuja sobre el color plano del fondo (el color del centro). Después, en
cada fotograma, cada píxel se vuelve a componer sobre el degradado radial:

* lo que es fondo puro pasa a ser el degradado;
* lo que es mezcla del fondo con blanco (líneas tenues, estrellas) o con negro
  (sombras) se recompone con la misma mezcla sobre el degradado;
* lo que tiene color propio (personajes blancos, colores de concepto, luces)
  se queda exactamente igual;
* alrededor de los colores de concepto (verde, rojo, amarillo, azul) el fondo se
  oscurece un poco (halo), para que destaquen sobre cualquier fondo de color.

Así los personajes siguen SIEMPRE blancos y los colores de concepto no se apagan.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .lienzo import AMARILLO, AZUL, BLANCO, ROJO, VERDE

CONCEPTOS = np.array([VERDE, ROJO, AMARILLO, AZUL], np.float32)


def _suave(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def mapa_radial(ancho: int, alto: int, centro_color, zonas, var) -> np.ndarray:
    """Imagen float32 (alto, ancho, 3) con el degradado de cada zona.

    `zonas` = [(y0, y1, horizonte o None)] en píxeles del vídeo.
    """
    base = np.array(centro_color, np.float32)
    borde = np.zeros(3, np.float32)  # los bordes pueden llegar a #000000
    mapa = np.zeros((alto, ancho, 3), np.float32)
    xs = np.arange(ancho, dtype=np.float32)[None, :]
    for y0, y1, horizonte in zonas:
        y0, y1 = int(y0), int(y1)
        ys = np.arange(y0, y1, dtype=np.float32)[:, None]
        h = y1 - y0
        cx = ancho / 2 + var.dx
        cy = y0 + h * (0.5 if h < 1200 else 0.46) + var.dy * (h / 1920)
        rx, ry = ancho * 0.62 * var.radio, h * 0.55 * var.radio
        r = np.sqrt(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2)
        f = 1 - _suave((r - 0.28) / 0.95)  # 1 en el centro (color vivo), 0 en las esquinas
        zona = borde + (base - borde) * f[..., None]
        if horizonte is not None:  # resplandor suave del horizonte (color de ambiente variable)
            sigma = np.where(ys <= horizonte, 140.0, 80.0)  # sube suave al cielo y se apaga rápido abajo
            g = np.exp(-(((ys - horizonte) / sigma) ** 2))
            zona = zona + (np.array(var.resplandor, np.float32) - zona) * (0.16 * g)[..., None]
        mapa[y0:y1] = zona
    return mapa


class Componedor:
    """Recompone cada fotograma sobre el degradado radial (ver la explicación del módulo).

    Se trabaja por planos de color (R, G y B por separado), que es mucho más rápido en numpy.
    """

    def __init__(self, centro_color, mapa: np.ndarray):
        self.B = np.array(centro_color, np.float32)
        self.dif = np.ascontiguousarray((mapa - self.B).transpose(2, 0, 1))  # (3, alto, ancho)
        W = np.array(BLANCO, np.float32)
        self.M = np.stack([W - self.B, -self.B], axis=1)  # 3x2: hacia blanco, hacia negro
        self.P = np.linalg.pinv(self.M)  # 2x3

    def __call__(self, img: Image.Image) -> Image.Image:
        arr = np.asarray(img)
        p = [arr[..., c].astype(np.float32) for c in range(3)]
        v = [p[c] - self.B[c] for c in range(3)]
        P, M = self.P, self.M
        a = np.clip(P[0, 0] * v[0] + P[0, 1] * v[1] + P[0, 2] * v[2], 0, 1)  # mezcla con blanco
        b = np.clip(P[1, 0] * v[0] + P[1, 1] * v[1] + P[1, 2] * v[2], 0, 1)  # mezcla con negro
        s = a + b
        exceso = s > 1
        if exceso.any():
            a = np.where(exceso, a / np.maximum(s, 1e-6), a)
            b = np.where(exceso, b / np.maximum(s, 1e-6), b)
            s = np.minimum(s, 1)
        resto2 = sum((v[c] - (M[c, 0] * a + M[c, 1] * b)) ** 2 for c in range(3))
        propio = np.clip((np.sqrt(resto2) - 6) / 26, 0, 1)  # 1 = color propio: no se toca
        fondo_visible = (1 - s) * (1 - propio)  # cuánto fondo se ve en ese píxel
        out = [p[c] + self.dif[c] * fondo_visible for c in range(3)]
        # Halo oscuro alrededor de los colores de concepto (solo se miran los píxeles muy saturados).
        saturados = (np.maximum(np.maximum(p[0], p[1]), p[2]) - np.minimum(np.minimum(p[0], p[1]), p[2])) > 120
        saturados &= propio > 0.5  # el fondo de color no cuenta
        ys, xs = np.nonzero(saturados)
        if len(ys):
            q = arr[ys, xs].astype(np.float32)
            cerca = np.min(((q[:, None, :] - CONCEPTOS) ** 2).sum(-1), axis=1) < 70 ** 2
            if cerca.any():
                ys, xs = ys[cerca], xs[cerca]
                y0, y1 = max(0, ys.min() - 16), min(arr.shape[0], ys.max() + 17)
                x0, x1 = max(0, xs.min() - 16), min(arr.shape[1], xs.max() + 17)
                mascara = np.zeros((y1 - y0, x1 - x0), np.uint8)
                mascara[ys - y0, xs - x0] = 255
                # A mitad de resolución (4 veces menos trabajo) y luego se amplía.
                m = Image.fromarray(mascara).reduce(2).point(lambda x: 255 if x else 0)
                m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
                m = m.resize(mascara.shape[::-1], Image.BILINEAR)
                halo = 1 - 0.6 * np.asarray(m, np.float32) / 255 * fondo_visible[y0:y1, x0:x1]
                for c in range(3):
                    out[c][y0:y1, x0:x1] *= halo
        res = np.stack(out, axis=-1)
        return Image.fromarray(np.clip(res + 0.5, 0, 255).astype(np.uint8))
