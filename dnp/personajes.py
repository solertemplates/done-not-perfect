"""Los dos muñequitos de la serie: cabeza redonda grande, ojos de punto,
sonrisa simple y cuerpo de palo grueso. Siempre blancos.

El Perfeccionista se distingue por las gafas y el lápiz detrás de la oreja.

La postura se describe con pocos datos (cadera, inclinación y adónde van
manos y pies); codos y rodillas se calculan con cinemática inversa.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from .lienzo import BLANCO, FONDO, TINTA, Lienzo

R_CABEZA = 80
TORSO = 150
CUELLO = 12
BRAZO = (94, 92)
PIERNA = (96, 96)
GROSOR = 17


@dataclass
class Pose:
    cadera: tuple[float, float]
    inclinacion: float = 0.0  # grados; positivo = hacia donde mira
    cabeza: float = 0.0  # giro extra de la cabeza (grados)
    mano_atras: tuple[float, float] = (0, 0)
    mano_delante: tuple[float, float] = (0, 0)
    pie_atras: tuple[float, float] = (0, 0)
    pie_delante: tuple[float, float] = (0, 0)
    mira: int = 1  # 1 = derecha, -1 = izquierda
    sonrisa: float = 1.0  # 1 sonrisa, 0 recta, -1 triste, 2 boca abierta "¡O!"
    parpado: float = 0.0  # 0 ojos abiertos, 1 cerrados
    mirada: tuple[float, float] = (0.0, 0.0)  # desplazamiento de las pupilas (-1..1)
    hombros: float = 0.0  # cuánto bajan los hombros (suspiro), en px
    extra: dict = field(default_factory=dict)


def mezclar(a: Pose, b: Pose, t: float) -> Pose:
    """Interpola dos posturas. `mira` cambia de golpe a mitad (giro de dibujo animado)."""
    def l(x, y):
        return x + (y - x) * t

    def p(x, y):
        return (l(x[0], y[0]), l(x[1], y[1]))

    return replace(
        a,
        cadera=p(a.cadera, b.cadera),
        inclinacion=l(a.inclinacion, b.inclinacion),
        cabeza=l(a.cabeza, b.cabeza),
        mano_atras=p(a.mano_atras, b.mano_atras),
        mano_delante=p(a.mano_delante, b.mano_delante),
        pie_atras=p(a.pie_atras, b.pie_atras),
        pie_delante=p(a.pie_delante, b.pie_delante),
        mira=a.mira if t < 0.5 else b.mira,
        sonrisa=l(a.sonrisa, b.sonrisa),
        parpado=l(a.parpado, b.parpado),
        mirada=p(a.mirada, b.mirada),
        hombros=l(a.hombros, b.hombros),
    )


def _ik(raiz, objetivo, l1, l2, lado):
    """Articulación intermedia de un miembro de dos segmentos (codo o rodilla)."""
    dx, dy = objetivo[0] - raiz[0], objetivo[1] - raiz[1]
    d = math.hypot(dx, dy) or 1e-6
    d_c = min(max(d, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d_c * d_c - l2 * l2) / (2 * l1 * d_c)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    ang = base + lado * a
    medio = (raiz[0] + l1 * math.cos(ang), raiz[1] + l1 * math.sin(ang))
    if d > l1 + l2:  # objetivo inalcanzable: el miembro se estira hacia él
        fin = (raiz[0] + dx / d * (l1 + l2), raiz[1] + dy / d * (l1 + l2))
    else:
        fin = objetivo
    return medio, fin


def esqueleto(p: Pose) -> dict:
    """Calcula los puntos del cuerpo en coordenadas del panel."""
    inc = math.radians(p.inclinacion * p.mira)
    arriba = (math.sin(inc), -math.cos(inc))
    cadera = p.cadera
    cuello = (cadera[0] + arriba[0] * TORSO, cadera[1] + arriba[1] * TORSO + p.hombros * 0.4)
    hombro = (cuello[0] - arriba[0] * (14 + p.hombros), cuello[1] - arriba[1] * (14 + p.hombros))
    inc_c = math.radians((p.inclinacion + p.cabeza) * p.mira)
    dir_c = (math.sin(inc_c), -math.cos(inc_c))
    centro = (cuello[0] + dir_c[0] * (CUELLO + R_CABEZA), cuello[1] + dir_c[1] * (CUELLO + R_CABEZA))
    # Codos hacia atrás/abajo y rodillas hacia delante, según hacia dónde mira.
    lado_codo = p.mira
    lado_rodilla = p.mira
    codo_a, mano_a = _ik(hombro, p.mano_atras, *BRAZO, lado_codo)
    codo_d, mano_d = _ik(hombro, p.mano_delante, *BRAZO, lado_codo)
    rod_a, pie_a = _ik(cadera, p.pie_atras, *PIERNA, -lado_rodilla)
    rod_d, pie_d = _ik(cadera, p.pie_delante, *PIERNA, -lado_rodilla)
    return dict(
        cadera=cadera, cuello=cuello, hombro=hombro, cabeza=centro, inc_cabeza=inc_c,
        codo_a=codo_a, mano_a=mano_a, codo_d=codo_d, mano_d=mano_d,
        rod_a=rod_a, pie_a=pie_a, rod_d=rod_d, pie_d=pie_d,
    )


def dibujar(lz: Lienzo, p: Pose, perfeccionista: bool, en_mano=None):
    """Dibuja el personaje. `en_mano(lz, esqueleto)` dibuja un objeto sujeto
    con la mano delantera, entre el cuerpo y el brazo delantero."""
    e = esqueleto(p)
    g = GROSOR
    # Miembros traseros primero.
    lz.linea([e["cadera"], e["rod_a"], e["pie_a"]], g)
    lz.linea([e["hombro"], e["codo_a"], e["mano_a"]], g)
    lz.linea([e["cadera"], e["cuello"]], g)
    _cabeza(lz, e, p, perfeccionista)
    if perfeccionista:
        _lapiz_oreja(lz, e, p)
    lz.linea([e["cadera"], e["rod_d"], e["pie_d"]], g)
    if en_mano:
        en_mano(lz, e)
    lz.linea([e["hombro"], e["codo_d"], e["mano_d"]], g)
    return e


def _local(e, p: Pose, x, y):
    """Punto en coordenadas de la cara (x hacia donde mira, y hacia abajo)."""
    c = e["cabeza"]
    a = e["inc_cabeza"]
    xx = x * p.mira
    return (c[0] + xx * math.cos(a) - y * math.sin(a), c[1] + xx * math.sin(a) + y * math.cos(a))


def _cabeza(lz: Lienzo, e, p: Pose, gafas: bool):
    R = R_CABEZA
    lz.circulo(e["cabeza"], R, relleno=BLANCO)
    mx, my = p.mirada
    ojos = [(-0.02 * R, -0.12 * R), (0.42 * R, -0.12 * R)]
    for ox, oy in ojos:
        c = _local(e, p, ox + 0.10 * R + mx * 0.06 * R, oy + my * 0.06 * R)
        if p.parpado > 0.6:
            a = _local(e, p, ox + 0.0 * R, oy)
            b = _local(e, p, ox + 0.2 * R, oy)
            lz.linea([a, b], 5, TINTA)
        else:
            lz.circulo(c, 0.085 * R * (1 - p.parpado * 0.6), relleno=TINTA)
    if gafas:
        for ox, oy in ojos:
            lz.circulo(_local(e, p, ox + 0.10 * R, oy), 0.21 * R, borde=TINTA, ancho=5)
        lz.linea([_local(e, p, 0.29 * R, -0.13 * R), _local(e, p, 0.31 * R, -0.13 * R)], 5, TINTA)
        lz.linea([_local(e, p, -0.13 * R, -0.16 * R), _local(e, p, -0.62 * R, -0.24 * R)], 5, TINTA)
    # Boca
    s = p.sonrisa
    cx = 0.22 * R
    if s > 1.2:  # boca abierta de sorpresa
        lz.circulo(_local(e, p, cx + 0.06 * R, 0.36 * R), 0.11 * R * min(1.0, s - 1.0), relleno=TINTA)
        return
    pts = []
    for i in range(9):
        u = i / 8 * 2 - 1
        pts.append(_local(e, p, cx + u * 0.26 * R, 0.33 * R + (1 - u * u) * 0.16 * R * s - 0.02 * R * (1 - abs(s))))
    lz.linea(pts, 5.5, TINTA)


def _lapiz_oreja(lz: Lienzo, e, p: Pose):
    """Lápiz detrás de la oreja: asoma por la parte trasera-superior de la cabeza."""
    R = R_CABEZA
    base = _local(e, p, -0.52 * R, 0.02 * R)
    punta = _local(e, p, -1.68 * R, -0.30 * R)
    dx, dy = punta[0] - base[0], punta[1] - base[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy * 11, ux * 11
    cuerpo_fin = (base[0] + ux * (L - 26), base[1] + uy * (L - 26))
    cuerpo = [
        (base[0] + nx, base[1] + ny), (cuerpo_fin[0] + nx, cuerpo_fin[1] + ny),
        (cuerpo_fin[0] - nx, cuerpo_fin[1] - ny), (base[0] - nx, base[1] - ny),
    ]
    lz.poligono(cuerpo, relleno=FONDO, borde=BLANCO, ancho=4)
    lz.poligono([(cuerpo_fin[0] + nx, cuerpo_fin[1] + ny), punta, (cuerpo_fin[0] - nx, cuerpo_fin[1] - ny)],
                relleno=FONDO, borde=BLANCO, ancho=4)
    mina = (base[0] + ux * (L - 8), base[1] + uy * (L - 8))
    lz.linea([mina, punta], 5, BLANCO)
    goma = (base[0] + ux * 14, base[1] + uy * 14)
    lz.linea([(goma[0] + nx, goma[1] + ny), (goma[0] - nx, goma[1] - ny)], 4, BLANCO)


def martillo(lz: Lienzo, mano, angulo: float, largo: float = 78):
    """Martillo sujeto en `mano`; `angulo` en grados (0 = apuntando hacia arriba)."""
    a = math.radians(angulo)
    d = (math.sin(a), -math.cos(a))
    fin = (mano[0] + d[0] * largo, mano[1] + d[1] * largo)
    inicio = (mano[0] - d[0] * 14, mano[1] - d[1] * 14)
    lz.linea([inicio, fin], 9, BLANCO)
    n = (-d[1], d[0])
    w, h = 30, 13
    cabeza = [
        (fin[0] + n[0] * w + d[0] * h, fin[1] + n[1] * w + d[1] * h),
        (fin[0] - n[0] * w * 0.7 + d[0] * h, fin[1] - n[1] * w * 0.7 + d[1] * h),
        (fin[0] - n[0] * w * 0.7 - d[0] * h, fin[1] - n[1] * w * 0.7 - d[1] * h),
        (fin[0] + n[0] * w - d[0] * h, fin[1] + n[1] * w - d[1] * h),
    ]
    lz.poligono(cabeza, relleno=BLANCO)
    return fin, n
