"""Variaciones de ambiente por episodio, elegidas a partir del id (siempre las mismas para un id).

Así dos vídeos nunca se ven iguales aunque usen la misma plantilla: cambian las
estrellas, la ciudad, el centro y el tamaño del degradado radial, el color del
resplandor del horizonte y el color dominante de las ventanas encendidas.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from .lienzo import AMBIENTE


def numero(texto: str, sal: str = "") -> int:
    """Número estable (no cambia entre ejecuciones, a diferencia de hash())."""
    return int(hashlib.sha1(f"{sal}:{texto}".encode()).hexdigest()[:12], 16)


@dataclass(frozen=True)
class Variacion:
    semilla: int = 0
    dx: float = 0.0  # desplazamiento del centro del degradado radial (px)
    dy: float = 0.0
    radio: float = 1.0  # tamaño del centro de color
    resplandor: tuple = AMBIENTE["naranja"]  # color del resplandor del horizonte
    pesos_ventanas: tuple = (0.55, 0.2, 0.12, 0.13)  # ámbar, naranja, rosa, violeta
    estrellas: float = 1.0  # densidad de estrellas


def para(ident: str) -> Variacion:
    rnd = random.Random(numero(ident, "variedad"))
    colores = list(AMBIENTE.values())
    pesos = [rnd.uniform(0.1, 1.0) for _ in colores]
    pesos[0] += 0.6  # el ámbar sigue mandando
    total = sum(pesos)
    return Variacion(
        semilla=rnd.randrange(1, 10_000),
        dx=rnd.uniform(-90, 90),
        dy=rnd.uniform(-110, 110),
        radio=rnd.uniform(0.85, 1.2),
        resplandor=rnd.choice(colores),
        pesos_ventanas=tuple(p / total for p in pesos),
        estrellas=rnd.uniform(0.75, 1.35),
    )


_actual = [Variacion()]


def actual() -> Variacion:
    return _actual[0]


def usar(v: Variacion) -> None:
    _actual[0] = v
