"""Rótulos del gancho: etiquetas grandes de los personajes, marcadores con números y la lección fija.

* Etiqueta: palabra grande en negrita junto a cada personaje (DONE / PERFECT). Puede cambiar a
  un color de concepto en un momento ("color_final" desde "desde_s"): verde si lo consigue, rojo si se rinde.
* Marcador: una línea bajo cada lado con números que cambian, por ejemplo "HITS 60 · DONE 0".
  Los números salen de lo que pasa en el episodio (golpes, sonidos, ventas...).
* Lección: una frase fija arriba durante todo el vídeo.
"""
from __future__ import annotations

import re

from .lienzo import BLANCO, ESCALA, capa, fuente, mezcla, texto
from .tiempo import tramo

_VAR = re.compile(r"\{(\w+)\}")


def _color(nombre):
    from .biblioteca import COLORES

    return COLORES.get(nombre) if nombre else None


def ancho_texto(cadena: str, tam: float) -> float:
    return fuente(max(4, int(round(tam * ESCALA)))).getlength(cadena) / ESCALA


# ------------------------------------------------------------------ ETIQUETA
def color_etiqueta(conf: dict, ts: float):
    final = _color(conf.get("color_final"))
    if final is None or "desde_s" not in conf:
        return BLANCO
    return mezcla(BLANCO, final, tramo(ts, conf["desde_s"], conf["desde_s"] + 0.35))


def etiqueta(img, conf: dict, ts: float, pos, tam: float, ancla: str = "mm", ancho_max: float = 1000):
    cadena = conf["texto"]
    tam = min(tam, tam * ancho_max / max(1.0, ancho_texto(cadena, tam)))
    texto(img, [(cadena, color_etiqueta(conf, ts))], pos, tam, 1.0, ancla=ancla)


# ------------------------------------------------------------------ MARCADOR
class Marcador:
    """Línea de texto con números que cambian. `valores` dice de dónde sale cada {número}."""

    def __init__(self, conf: dict, objetos: dict, actores: list):
        self.conf = conf
        self.partes = []  # (texto fijo, nombre de valor o None)
        pos = 0
        for m in _VAR.finditer(conf["texto"]):
            if m.start() > pos:
                self.partes.append((conf["texto"][pos:m.start()], None))
            self.partes.append(("", m.group(1)))
            pos = m.end()
        if pos < len(conf["texto"]):
            self.partes.append((conf["texto"][pos:], None))
        quien = {**objetos, **{a.id: a for a in actores}}
        self.fuentes = {}
        for nombre, v in conf.get("valores", {}).items():
            self.fuentes[nombre] = (v, quien.get(v.get("de")))
        self._eventos = {}

    def valor(self, nombre: str, ts: float) -> int:
        v, cosa = self.fuentes[nombre]
        if "fijo" in v:
            return int(v["fijo"])
        if cosa is None:
            return 0
        if "golpes" in v:
            n = cosa.golpes_hasta(ts)
        elif "ventas" in v:
            n = sum(1 for t in cosa.ventas if t <= ts)
        elif "dinero" in v:
            n = sum(m for t, m in cosa.ingresos if t <= ts)
        else:
            nombres = tuple(v.get("cuenta", []))
            if nombres not in self._eventos:
                self._eventos[nombres] = sorted(e[0] for e in cosa.eventos() if e[1] in nombres)
            n = sum(1 for t in self._eventos[nombres] if t <= ts + 1e-6)
        return min(n, v["max"]) if "max" in v else n

    def trozos(self, ts: float):
        gris = mezcla(BLANCO, (0, 0, 0), 0.18)
        out = []
        for fijo, nombre in self.partes:
            if nombre is None:
                out.append((fijo, gris))
                continue
            n = self.valor(nombre, ts)
            v = self.fuentes[nombre][0]
            color = _color(v.get("color")) if (n > 0 or "fijo" in v) else None
            out.append((str(n), color or BLANCO))
        return out

    def dibujar(self, img, ts: float, pos, tam: float, ancla: str = "mm"):
        texto(img, self.trozos(ts), pos, tam, 1.0, ancla=ancla)


# ------------------------------------------------------------------- LECCIÓN
ALTO_LECCION = 150  # franja de arriba reservada para la lección


def leccion(img, cadena: str, ancho: int):
    """Frase fija arriba, en una o dos líneas, sobre una banda oscura translúcida."""
    tam = 46.0
    lineas = [cadena]
    if ancho_texto(cadena, tam) > ancho - 100:
        palabras = cadena.split()
        mejor = None
        for i in range(1, len(palabras)):
            a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
            w = max(ancho_texto(a, tam), ancho_texto(b, tam))
            if mejor is None or w < mejor[0]:
                mejor = (w, [a, b])
        if mejor:
            lineas = mejor[1]
        w = max(ancho_texto(x, tam) for x in lineas)
        if w > ancho - 100:
            tam *= (ancho - 100) / w
    s = ESCALA
    alto_banda = 46 + len(lineas) * tam * 1.25

    def banda(d, x0, y0):
        d.rounded_rectangle((24 * s - x0, 16 * s - y0, (ancho - 24) * s - x0, (16 + alto_banda) * s - y0),
                            radius=int(26 * s), fill=(0, 0, 0, 255))

    capa(img, (0, 0, ancho * s, int((24 + alto_banda) * s)), banda, 0.42)
    y = 16 + 23 + tam * 0.62
    for linea in lineas:
        texto(img, [(linea, BLANCO)], (ancho / 2, y), tam, 1.0)
        y += tam * 1.25
