"""Utilidades de tiempo y curvas de animación."""
from __future__ import annotations

import math


def limitar(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def tramo(t: float, t0: float, t1: float) -> float:
    """Progreso 0..1 de t entre t0 y t1."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return limitar((t - t0) / (t1 - t0))


def suave(u: float) -> float:
    u = limitar(u)
    return u * u * (3 - 2 * u)


def sale(u: float) -> float:
    u = limitar(u)
    return 1 - (1 - u) ** 3


def entra(u: float) -> float:
    u = limitar(u)
    return u ** 3


def rebote(u: float, fuerza: float = 1.70158) -> float:
    """Ease-out con un pequeño pasado de largo (efecto 'pop')."""
    u = limitar(u)
    c = fuerza
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def pulso(t: float, centro: float, ancho: float) -> float:
    """Triángulo 0..1..0 centrado en `centro` (parpadeos, destellos)."""
    return limitar(1 - abs(t - centro) / (ancho / 2)) if ancho > 0 else 0.0


def lerp(a, b, u):
    if isinstance(a, tuple):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def pista(t: float, claves, curva=suave, mezcla=lerp):
    """Interpola entre claves [(tiempo, valor), ...] ordenadas por tiempo."""
    if t <= claves[0][0]:
        return claves[0][1]
    for (t0, v0), (t1, v1) in zip(claves, claves[1:]):
        if t <= t1:
            return mezcla(v0, v1, curva(tramo(t, t0, t1)))
    return claves[-1][1]


def oscila(t: float, frecuencia: float, fase: float = 0.0) -> float:
    return math.sin(2 * math.pi * (frecuencia * t + fase))
