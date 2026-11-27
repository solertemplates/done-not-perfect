"""Vídeo LARGO para YouTube: 1920x1080, 30 fps, 8:30 exactos (510 s), sin voz.

Entrada: un .txt en episodios_largos/ (por ejemplo 01_mismo_sueldo.txt):

    id: largo01_mismo_sueldo
    gancho: Same salary. 10 years later.
    capitulos:
    - Savings
    - Debt
    - Habits
    - Decisions
    - Business
    mensaje: Not in a day. Not in a month. But with consistency and discipline, it happens.
    siguiente: Same age. Different choices.

Estructura (siempre igual):
    0:00  GANCHO (20 s): se ve el final (Hacedor tranquilo en verde, Perfeccionista agobiado en rojo),
          luego rebobina hasta "Year 1".
    0:20  5 capítulos de 92 s (2 años cada uno), con contador de años y marcador verde/rojo.
    2:00, 4:00, 6:00, 8:00  MINIGANCHOS (3 s de texto grande).
    8:00  FINAL (30 s): vuelve la escena del gancho, "Done > Perfect" y el enlace al siguiente.
          El último fotograma es igual que el primero.

Uso:
    python -m dnp.largo episodios_largos/01_mismo_sueldo.txt --destino salida/videos
    python -m dnp.largo --todos --solo-comprobar
"""
from __future__ import annotations

import argparse
import difflib
import math
import multiprocessing as mp
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from . import color, variedad
from . import largo_escenas as es
from .config import ErrorConfig
from .lienzo import (BLANCO, ESCALA, FONDOS, ROJO, VERDE, Lienzo, capa, fuente, mezcla, tenue, texto,
                     usar_fondo)
from .tiempo import rebote, tramo

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = "episodios_largos"
ANCHO, ALTO, FPS = 1920, 1080, 30
DURACION = 510.0  # 8:30
N_FOTOGRAMAS = int(DURACION * FPS)
GANCHO = 20.0
CAPITULO = 92.0
FINAL = 480.0  # 8:00
MINIGANCHOS = [120.0, 240.0, 360.0, 480.0]
TEXTOS_MINIGANCHO = ["But year 5 changes everything…", "Wait for the next mistake…",
                     "This is where most people quit…", "10 years later…"]
MENSAJE_EN = [200.0 - 4, 384.0 - 4, 484.0]  # el mensaje central aparece varias veces (6 s cada una)
DUR_MENSAJE = 6.5

# Capítulos posibles (nombre en inglés o en español) -> clave interna.
CAPITULOS = {
    "savings": "savings", "saving": "savings", "ahorro": "savings", "ahorros": "savings",
    "debt": "debt", "deuda": "debt", "deudas": "debt",
    "habits": "habits", "habit": "habits", "habitos": "habits", "hábitos": "habits",
    "decisions": "decisions", "decision": "decisions", "decisiones": "decisions",
    "business": "business", "negocio": "business", "negocios": "business",
}
TITULOS = {"savings": "SAVINGS", "debt": "DEBT", "habits": "HABITS", "decisions": "DECISIONS", "business": "BUSINESS"}
FONDO_CAP = {"savings": "violeta", "debt": "azul_noche", "habits": "naranja_atardecer", "decisions": "gris_pizarra",
             "business": "morado_oscuro"}
FONDO_GANCHO = "azul_electrico"
ESTILO_CAP = {"savings": "piano", "debt": "lofi", "habits": "ukelele", "decisions": "epico_suave",
              "business": "alegre"}
CAMPOS = {"id", "gancho", "capitulos", "mensaje", "siguiente", "titulo"}


# ============================================================ GUION (.txt)
@dataclass(frozen=True)
class Largo:
    id: str
    gancho: str
    capitulos: tuple  # claves internas (savings, debt...)
    titulos: tuple  # cómo se escriben en pantalla
    mensaje: str
    siguiente: str
    archivo: str = ""

    def inicio(self, i: int) -> float:
        return GANCHO + CAPITULO * i

    def marcas(self) -> list[tuple[float, str]]:
        """Capítulos de YouTube: (segundo, nombre)."""
        return ([(0.0, "Hook")] + [(self.inicio(i), t.title()) for i, t in enumerate(self.titulos)]
                + [(FINAL, "Ending")])


def leer(texto: str, ruta: Path | str = "") -> Largo:
    """Lee el guion de un largo. Lanza ErrorConfig con los errores en español."""
    from .plantillas import _clave, normalizar

    ruta = Path(ruta)
    errores: list[str] = []
    campos: dict[str, str] = {}
    caps: list[str] = []
    en_capitulos = False
    for n, linea in enumerate(normalizar(texto).splitlines(), 1):
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        item = re.match(r"^(?:[-*•]|\d+[.)])\s*(.+)$", s)
        if en_capitulos and item:
            caps.append(item.group(1).strip())
            continue
        if ":" not in s:
            errores.append(f"La línea {n} (\"{s[:40]}\") no tiene \"campo: valor\".")
            continue
        k, v = s.split(":", 1)
        clave = _clave(k)
        v = v.strip().strip('"').strip()
        en_capitulos = clave == "capitulos"
        if clave == "capitulos":
            caps += [c.strip() for c in v.split(",") if c.strip()]
            continue
        if clave not in CAMPOS:
            sug = difflib.get_close_matches(clave, sorted(CAMPOS), n=1, cutoff=0.6)
            extra = f" ¿Querías decir '{sug[0]}'?" if sug else ""
            errores.append(f"El campo '{clave}' no existe.{extra} Campos: {', '.join(sorted(CAMPOS))}.")
            continue
        campos[clave] = v
    m = re.match(r"^(?:largo)?(\d+)[_\- ]*(.*)$", ruta.stem.lower())
    ident = campos.get("id") or (f"largo{int(m.group(1)):02d}_{_clave(m.group(2)) or 'video'}" if m else "")
    if not ident:
        errores.append("Falta 'id:' (por ejemplo id: largo01_mismo_sueldo) o un número al principio del nombre del archivo.")
    elif not re.fullmatch(r"[a-z0-9_]{3,60}", ident):
        errores.append(f"'id' solo puede tener minúsculas sin tildes, números y guiones bajos. Ahora vale \"{ident}\".")
    for campo, maximo in (("gancho", 40), ("mensaje", 110), ("siguiente", 40)):
        if not campos.get(campo):
            errores.append(f"Falta el campo '{campo}:'.")
        elif len(campos[campo]) > maximo:
            errores.append(f"'{campo}' es demasiado largo ({len(campos[campo])} letras, máximo {maximo}).")
    claves = []
    if len(caps) != 5:
        errores.append(f"'capitulos' debe tener 5 líneas (una por capítulo), y tiene {len(caps)}. "
                       "Por ejemplo: Savings, Debt, Habits, Decisions, Business.")
    for c in caps:
        k = CAPITULOS.get(_clave(c)) or CAPITULOS.get(c.strip().lower())
        if k is None:
            sug = difflib.get_close_matches(_clave(c), list(CAPITULOS), n=1, cutoff=0.5)
            extra = f" ¿Querías decir \"{sug[0]}\"?" if sug else ""
            errores.append(f"El capítulo \"{c}\" no existe.{extra} Capítulos: Savings, Debt, Habits, Decisions, Business.")
        claves.append(k)
    if errores:
        raise ErrorConfig(errores, str(ruta))
    return Largo(id=ident, gancho=campos["gancho"], capitulos=tuple(claves),
                 titulos=tuple(TITULOS[k] for k in claves), mensaje=campos["mensaje"],
                 siguiente=campos["siguiente"], archivo=str(ruta))


def cargar(ruta: Path | str) -> Largo:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfig([f"No existe el archivo '{ruta}'."], str(ruta))
    return leer(ruta.read_text(encoding="utf-8"), ruta)


# ============================================================ RÓTULOS
def _ancho(cadena, tam):
    return fuente(max(4, int(round(tam * ESCALA)))).getlength(cadena) / ESCALA


def banda(img, lineas, y, tam, alfa, colores=None, ancho_max=1700):
    """Texto grande centrado sobre una banda oscura translúcida (una o varias líneas)."""
    if alfa <= 0.01:
        return
    w = max(_ancho(x if isinstance(x, str) else "".join(c for c, _ in x), tam) for x in lineas)
    if w > ancho_max:
        tam *= ancho_max / w
        w = ancho_max
    alto_b = len(lineas) * tam * 1.3 + tam * 0.9
    s = ESCALA

    def fondo_banda(d, x0, y0):
        d.rounded_rectangle(((ANCHO / 2 - w / 2 - 50) * s - x0, (y - alto_b / 2) * s - y0,
                             (ANCHO / 2 + w / 2 + 50) * s - x0, (y + alto_b / 2) * s - y0),
                            radius=int(34 * s), fill=(0, 0, 0, 255))

    caja = (int((ANCHO / 2 - w / 2 - 60) * s), int((y - alto_b / 2 - 10) * s),
            int((ANCHO / 2 + w / 2 + 60) * s), int((y + alto_b / 2 + 10) * s))
    capa(img, caja, fondo_banda, 0.55 * alfa)
    y0 = y - (len(lineas) - 1) * tam * 1.3 / 2
    for i, linea in enumerate(lineas):
        trozos = [(linea, (colores or {}).get(i, BLANCO))] if isinstance(linea, str) else linea
        trozos = [(c, mezcla((0, 0, 0), col, alfa)) for c, col in trozos]
        texto(img, trozos, (ANCHO / 2, y0 + i * tam * 1.3), tam, 1.0)


def partir(frase: str, max_chars: int = 46) -> list[str]:
    """Parte una frase en líneas cortas, por frases y luego por palabras."""
    trozos = [x.strip() for x in re.split(r"(?<=[.!?…])\s+", frase) if x.strip()]
    lineas: list[str] = []
    for t in trozos:
        if lineas and len(lineas[-1]) + 1 + len(t) <= max_chars:
            lineas[-1] += " " + t
        elif len(t) <= max_chars:
            lineas.append(t)
        else:
            palabras, actual = t.split(), ""
            for p in palabras:
                if actual and len(actual) + 1 + len(p) > max_chars:
                    lineas.append(actual)
                    actual = p
                else:
                    actual = f"{actual} {p}".strip()
            lineas.append(actual)
    return lineas


def ventana(t, t0, dur, entra=0.35, sale=0.45):
    """Opacidad de un rótulo que aparece en t0 y dura `dur` segundos."""
    if t < t0 or t > t0 + dur:
        return 0.0
    return min(tramo(t, t0, t0 + entra), 1 - tramo(t, t0 + dur - sale, t0 + dur))


# ============================================================ VÍDEO
class VideoLargo:
    def __init__(self, largo: Largo):
        self.L = largo
        self.var = variedad.para(largo.id)
        self._fondos: dict = {}  # tramo -> imagen estática (a ESCALA)
        self._comp: dict = {}  # tramo -> Componedor

    # --------------------------------------------------------------- tramos
    def tramo_en(self, t: float):
        """('gancho'|'final', None) o ('cap', índice)."""
        if t < GANCHO:
            return "gancho", None
        if t >= FINAL:
            return "final", None
        return "cap", min(4, int((t - GANCHO) // CAPITULO))

    def _nombre_fondo(self, clave):
        return FONDO_GANCHO if clave in ("gancho", "final") else FONDO_CAP[self.L.capitulos[clave]]

    def _preparar(self, clave):
        if clave in self._fondos:
            return
        nombre = self._nombre_fondo(clave)
        B = FONDOS[nombre]
        usar_fondo(B)
        img = Image.new("RGB", (ANCHO * ESCALA, ALTO * ESCALA), B)
        lz = Lienzo(img)
        import random

        from .decorado import decor

        rnd = random.Random(f"{self.L.id}{clave}")
        for lado in (0, 1):  # suelo de boceto y algunas estrellas en cada mitad
            x0 = lado * es.MITAD
            lz.boceto((x0 + 30, es.SUELO), (x0 + es.MITAD - 30, es.SUELO), 3, decor(0.72), semilla=lado + 5)
            for j in range(5):
                x = x0 + 60 + j * 190
                lz.boceto((x, es.SUELO + 30), (x - 30, es.SUELO + 150), 1.6, decor(0.25), semilla=40 + j, doble=False)
            for _ in range(34):
                lz.circulo((x0 + rnd.uniform(20, es.MITAD - 20), rnd.uniform(170, 640)), rnd.choice((1.4, 1.9, 2.5)),
                           relleno=decor(rnd.uniform(0.35, 0.8)))
        lz.boceto((es.MITAD, 165), (es.MITAD, ALTO - 20), 3, decor(0.7), semilla=77, amp=1.2)
        self._fondos[clave] = img
        mapa = color.mapa_radial(ANCHO, ALTO, B, [(0, ALTO, None)], self.var)
        self._comp[clave] = color.Componedor(B, mapa)

    # --------------------------------------------------------------- fotograma
    def fotograma(self, t: float, rotulos: bool = True) -> Image.Image:
        tipo, i = self.tramo_en(t)
        clave = i if tipo == "cap" else ("final" if tipo == "final" else "gancho")
        self._preparar(clave)
        if clave == "final" and "gancho" not in self._fondos:
            self._preparar("gancho")
        clave_fondo = "gancho" if clave == "final" else clave  # el final repite el gancho tal cual
        usar_fondo(FONDOS[self._nombre_fondo(clave_fondo)])
        variedad.usar(self.var)
        img = self._fondos[clave_fondo].copy()
        if tipo == "cap":
            u = (t - self.L.inicio(i)) / CAPITULO
            self._capitulo(img, i, u, t)
        else:
            self._escena_gancho(img, t)
        if rotulos:
            self._rotulos(img, t, tipo, i)
        out = self._comp[clave_fondo](img.reduce(ESCALA))
        if 15.0 <= t < GANCHO:
            out = self._rebobinar(out, t)
        return out

    def fase(self, t):
        return (t / (DURACION - 1 / FPS)) % 1.0 if t < DURACION - 0.5 / FPS else 1.0

    # --------------------------------------------------------------- gancho / final
    def _escena_gancho(self, img, t):
        """El final de la historia: Hacedor tranquilo (verde) y Perfeccionista agobiado (rojo).
        Todo depende solo de la fase del bucle: el último fotograma es igual que el primero."""
        tv = self.fase(t) * DURACION  # tiempo "virtual" periódico
        L, R = es.mitad(img, 0), es.mitad(img, 1)
        # Hacedor: hucha llena con brillo, barra verde
        p = es.pose(es.X_FIG, tv, "tranquilo", mira=1)
        p.mano_delante = (p.cadera[0] + 52, p.cadera[1] + 40)
        p.mano_atras = (p.cadera[0] - 52, p.cadera[1] + 40)
        es.hucha(L, (650, 740), 1.45, 0.95)
        es.destello(L, (650, 600), (tv / 3.0) % 1.0, VERDE, 90)
        es.marca(L, (820, 470), 90, VERDE)
        es.dibujar_muneco(L, p, False)
        # Perfeccionista: hucha vacía y rota, bolsas con etiqueta roja, sudor
        q = es.pose(es.X_FIG, tv, "agobiado", mira=1)
        temblor = math.sin(2 * math.pi * tv * 2.0) * 4
        q.cadera = (q.cadera[0] + temblor, q.cadera[1])
        q.mano_delante = (q.cadera[0] + 30, q.cadera[1] - 170)  # mano a la cabeza
        es.hucha(R, (650, 770), 0.85, 0.0, rota=True)
        for k in range(6):
            es.bolsa_compra(R, (520 + (k % 3) * 120 + (k // 3) * 50, es.SUELO - (k // 3) * 70), 0.9)
        es.cruz(R, (820, 470), 80, ROJO)
        es.dibujar_muneco(R, q, True)
        es.gota_sudor(R, q, tv)

    def _rebobinar(self, img, t):
        """Efecto de cinta rebobinando (líneas desplazadas y ruido), de 15 s a 20 s."""
        arr = np.array(img)
        fuerza = min(1.0, tramo(t, 15.0, 15.4)) * (1 - tramo(t, 19.2, GANCHO))
        if fuerza <= 0:
            return img
        rnd = np.random.default_rng(int(t * 1000))
        for _ in range(7):
            y0 = int(rnd.integers(0, ALTO - 80))
            hh = int(rnd.integers(10, 70))
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(rnd.integers(-60, 60) * fuerza), axis=1)
        arr[::4] = (arr[::4].astype(np.float32) * (1 - 0.25 * fuerza)).astype(np.uint8)
        return Image.fromarray(arr)

    # --------------------------------------------------------------- capítulos
    def _capitulo(self, img, i, u, t):
        L, R = es.mitad(img, 0), es.mitad(img, 1)
        getattr(self, "_cap_" + self.L.capitulos[i])(img, L, R, u, t)

    def marcadores(self, i, u):
        """Textos de los marcadores verde/rojo de un capítulo: (izquierda, derecha)."""
        k = self.L.capitulos[i]
        meses = min(24, int(u * 24))
        if k == "savings":
            return f"SAVED {meses} MONTHS", "SAVED 0 MONTHS"
        if k == "debt":
            return f"BILLS PAID {meses} · DEBT 0", f"PURCHASES {int(es.compuesto(u) * 60)} · DEBT ↑"
        if k == "habits":
            return f"STREAK {self._dias_hacedor(u)} DAYS", f"STREAK {self._dias_perf(u)} DAYS"
        if k == "decisions":
            return f"DECISIONS MADE {int(es.compuesto(u) * 40) + meses}", f"STILL WAITING {meses} MONTHS"
        return (f"VERSION {1 + int(es.compuesto(u) * 11)} · CUSTOMERS {int(es.compuesto(u) * 120)}",
                f"PLANS {1 + int(u * 23)} · LAUNCHED 0")

    # SAVINGS: guarda un poco cada mes / espera el momento perfecto
    def _cap_savings(self, img, L, R, u, t):
        meses = u * 24
        m, f = int(meses), meses - int(meses)
        crece = es.compuesto(u)
        tam = 0.8 + 0.75 * crece
        c = (660, es.SUELO - 100 * tam - 10)
        es.hucha(L, c, tam, 0.08 + 0.9 * crece)
        p = es.pose(es.X_FIG, t, "alegre")
        ranura = (c[0] - 120 * tam * 0.02, c[1] - 88 * tam)
        ida = tramo(f, 0.05, 0.4) * (1 - tramo(f, 0.55, 0.9))
        es.mano_hacia(p, (ranura[0] - 30, ranura[1] - 40), ida)
        es.dibujar_muneco(L, p, False)
        if 0.2 <= f < 0.55:  # la moneda cae en la hucha
            v = tramo(f, 0.2, 0.55)
            mano = (es.X_FIG + 150, 520)
            x = mano[0] + (ranura[0] - mano[0]) * v
            y = mano[1] + (ranura[1] - mano[1]) * v - math.sin(math.pi * v) * 90
            es.moneda(L, (x, y), 18)
        if m in (11, 23) and f > 0.55 or m in (12, 0) and f < 0.1 and m:
            es.destello(L, (c[0], c[1] - 40), tramo(f if f > 0.5 else f + 1, 0.55, 1.1), VERDE, 110 * tam)
        # Perfeccionista: hucha vacía, pensando
        es.hucha(R, (660, es.SUELO - 90), 0.8, 0.0)
        q = es.pose(es.X_FIG, t, "neutro" if u < 0.55 else "triste")
        q.mano_delante = (q.cadera[0] + 46, q.cadera[1] - 120)  # mano a la barbilla
        es.dibujar_muneco(R, q, True)
        frases = ["Waiting for the perfect moment…", "Maybe next month…", "When I earn more…", "Prices might change…"]
        es.bocadillo(img, R, (560, 300), frases[(m // 3) % len(frases)], 30, ventana(f * 3 % 1, 0.0, 1.0, 0.1, 0.1))

    # DEBT: compras pequeñas que se acumulan / pagar primero
    def _cap_debt(self, img, L, R, u, t):
        meses = u * 24
        m, f = int(meses), meses - int(meses)
        p = es.pose(es.X_FIG, t, "tranquilo")
        es.mano_hacia(p, (560, 640), tramo(f, 0.1, 0.4) * (1 - tramo(f, 0.6, 0.9)))
        es.dibujar_muneco(L, p, False)
        for k in range(min(m, 10)):  # facturas pagadas, apiladas
            es.factura(L, (700 + (k % 2) * 16, es.SUELO - 70 - k * 14), 1.0, semilla=k)
        es.factura(L, (600, 600), tramo(f, 0.35, 0.6), semilla=m + 50)
        es.barra(L, 470, 260, 420, 1.0, VERDE)
        texto(img, [("PAID FIRST", VERDE)], (680, 240), 30, 1.0)
        # Perfeccionista: bolsas y cajas que se acumulan; la barra roja crece (efecto compuesto)
        n = int(es.compuesto(u) * 22) + int(u * 6)
        q = es.pose(es.X_FIG, t, "alegre" if u < 0.35 else ("neutro" if u < 0.6 else "agobiado"))
        es.mano_hacia(q, (520, 700), tramo(f, 0.1, 0.4) * (1 - tramo(f, 0.6, 0.9)))
        es.dibujar_muneco(R, q, True)
        for k in range(n):
            fila, col = divmod(k, 5)
            x = 480 + col * 92 + (fila % 2) * 30
            y = es.SUELO - fila * 62
            if fila % 2:
                es.caja(R, (x, y), 80, 58, semilla=k)
            else:
                es.bolsa_compra(R, (x, y), 0.85)
        es.barra(R, 470, 260, 420, es.compuesto(u), ROJO)
        texto(img, [("DEBT", ROJO)], (es.MITAD + 680, 240), 30, 1.0)
        if u > 0.6:
            es.gota_sudor(R, q, t)

    # HABITS: un poco cada día / empieza y lo deja
    def _dias_hacedor(self, u):
        return int(u * 730)

    def _dias_perf(self, u):
        dia = int(u * 730) % 60
        return min(dia, 3)

    def _cap_habits(self, img, L, R, u, t):
        paginas = u * 12
        pg, f = int(paginas), paginas - int(paginas)
        hechos = min(35, int(f * 38))
        nuevo = (f * 38) % 1
        es.calendario(L, 470, 330, 60, hechos, [], nuevo=nuevo)
        p = es.pose(es.X_FIG, t, "alegre")
        cel = min(34, max(0, hechos - 1))
        es.mano_hacia(p, (470 + (cel % 7 + 0.5) * 60, 330 + (cel // 7 + 0.5) * 60), 0.6 + 0.4 * math.sin(t * 6) ** 2)
        es.dibujar_muneco(L, p, False)
        if hechos >= 35:
            es.destello(L, (680, 480), tramo(f, 0.92, 1.0), VERDE, 160)
        # Perfeccionista: 3 marcas, luego cruces; cada página empieza otra vez y lo deja
        intentos = 3 if pg % 2 == 0 else 1
        dias = min(35, int(f * 38))
        hechos_p = min(intentos, dias)
        fallos = list(range(intentos, min(dias, 12)))
        es.calendario(R, 470, 330, 60, hechos_p, fallos, nuevo=1.0)
        q = es.pose(es.X_FIG, t, "alegre" if dias <= intentos else "triste")
        if dias > intentos:
            q.mano_delante = (q.cadera[0] + 40, q.cadera[1] + 100)
            q.inclinacion = 16
        es.dibujar_muneco(R, q, True)

    # DECISIONS: caminos que se separan; elegir hoy / esperar
    def _cap_decisions(self, img, L, R, u, t):
        # Hacedor: camina por su camino "TODAY"; los postes pasan y van saliendo banderas verdes
        avance = t * 110
        for k in range(6):
            x = 960 - ((avance + k * 210) % 1260) + 150
            if -60 < x < 1000:
                L.linea([(x, es.SUELO), (x, es.SUELO - 120)], 6, tenue(0.8))
                bandera = (k + int((avance) // 1260)) % 3 == 0 or u > 0.5
                if bandera:
                    L.poligono([(x, es.SUELO - 120), (x + 54, es.SUELO - 104), (x, es.SUELO - 88)], relleno=VERDE)
        L.linea([(20, es.SUELO + 40), (940, es.SUELO + 40)], 4, tenue(0.5))
        p = es.pose(es.X_FIG, t, "alegre")
        fase = 2 * math.pi * t * 1.25
        y = p.cadera[1] - abs(math.sin(fase)) * 8
        p.cadera = (p.cadera[0], y)
        p.pie_delante = (p.cadera[0] + 34 * math.sin(fase), es.SUELO - 2 - max(0, math.cos(fase)) * 14)
        p.pie_atras = (p.cadera[0] - 34 * math.sin(fase), es.SUELO - 2 - max(0, -math.cos(fase)) * 14)
        p.mano_delante = (p.cadera[0] - 40 * math.sin(fase), y + 96)
        p.mano_atras = (p.cadera[0] + 40 * math.sin(fase), y + 96)
        es.dibujar_muneco(L, p, False)
        texto(img, [("TODAY →", VERDE)], (760, 250), 46, 1.0)
        # Perfeccionista: en el cruce, da un paso y vuelve
        R.linea([(560, es.SUELO), (560, es.SUELO - 300)], 8, BLANCO)
        R.poligono([(560, es.SUELO - 300), (760, es.SUELO - 300), (800, es.SUELO - 270), (760, es.SUELO - 240),
                    (560, es.SUELO - 240)], borde=VERDE, ancho=4)
        R.poligono([(560, es.SUELO - 220), (360 + 520, es.SUELO - 220), (360 + 560, es.SUELO - 190),
                    (360 + 520, es.SUELO - 160), (560, es.SUELO - 160)], borde=ROJO, ancho=4)
        texto(img, [("TODAY", VERDE)], (es.MITAD + 665, es.SUELO - 270), 30, 1.0)
        texto(img, [("LATER", ROJO)], (es.MITAD + 700, es.SUELO - 190), 30, 1.0)
        duda = math.sin(2 * math.pi * t / 4.0)
        q = es.pose(es.X_FIG + 30 * max(0.0, duda), t, "neutro" if u < 0.5 else "triste")
        q.mano_delante = (q.cadera[0] + 46, q.cadera[1] - 120)
        es.dibujar_muneco(R, q, True)
        es.bocadillo(img, R, (300, 300), ["Let me wait…", "Not yet…", "What if it's wrong?"][int(t / 4) % 3], 30,
                     0.9)

    # BUSINESS: empieza pequeño y mejora / sigue planeando
    def _cap_business(self, img, L, R, u, t):
        nivel = 0 if u < 0.3 else (1 if u < 0.65 else 2)
        es.puesto_limonada(L, 640, nivel, t)
        for cambio in (0.3, 0.65):
            es.destello(L, (640, 520), tramo(u, cambio, cambio + 0.03), VERDE, 150)
        clientes = es.compuesto(u)
        frecuencia = 0.15 + clientes * 1.1  # clientes por segundo
        for k in range(6):
            ciclo = (t * frecuencia * 0.25 + k / 6) % 1.0
            if k / 6 < 0.2 + clientes * 0.8:
                x = 950 - ciclo * 220
                es.cliente(L, x, t + k, -1, alfa=min(1.0, (1 - ciclo) * 4))
        p = es.pose(es.X_FIG + 80, t, "alegre")
        es.mano_hacia(p, (560, 690), 0.5 + 0.5 * math.sin(t * 2.4))
        es.dibujar_muneco(L, p, False)
        texto(img, [(f"v{1 + int(clientes * 11)}", VERDE)], (860, 250), 44, 1.0)
        # Perfeccionista: planos y bolas de papel
        planos = 1 + int(u * 23)
        es.escritorio(R, 640, planos, int(u * 30), t)
        q = es.pose(es.X_FIG, t, "neutro" if u < 0.5 else "triste")
        es.mano_hacia(q, (560 + 30 * math.sin(t * 5), es.SUELO - 190), 1.0)
        es.dibujar_muneco(R, q, True)
        es.bocadillo(img, R, (560, 300), f"Business plan v{planos}", 32, 1.0)

    # --------------------------------------------------------------- rótulos
    def _rotulos(self, img, t, tipo, i):
        D = DURACION
        verde_rojo = tipo != "cap"
        # Etiquetas de cada lado
        for lado, (palabra, col) in enumerate((("DONE", VERDE), ("PERFECT", ROJO))):
            c = col if verde_rojo else BLANCO
            texto(img, [(palabra, c)], (60 + lado * es.MITAD, 220), 64, 1.0, ancla="lm")
        if tipo == "cap":
            u = (t - self.L.inicio(i)) / CAPITULO
            anio = min(10, 2 * i + 1 + int(u * 2))
            mes = int(u * 24) % 12 + 1
            sub = "Day 1" if u * CAPITULO < 4 else f"Month {mes}"
            texto(img, [(f"YEAR {anio}", BLANCO)], (ANCHO / 2, 64), 62, 1.0)
            texto(img, [(sub, tenue(0.85))], (ANCHO / 2, 122), 32, 1.0)
            texto(img, [(f"CHAPTER {i + 1} · {self.L.titulos[i]}", tenue(0.9))], (40, 64), 32, 1.0, ancla="lm")
            texto(img, [("SAME SALARY", tenue(0.9))], (ANCHO - 40, 64), 32, 1.0, ancla="rm")
            izq, der = self.marcadores(i, u)
            texto(img, [(izq, VERDE)], (es.MITAD / 2, ALTO - 50), 40, 1.0)
            texto(img, [(der, ROJO)], (es.MITAD * 1.5, ALTO - 50), 40, 1.0)
            # Tarjeta de capítulo (3,5 s)
            a = ventana(t, self.L.inicio(i), 3.6, 0.3, 0.5)
            if a:
                banda(img, [f"CHAPTER {i + 1}", self.L.titulos[i], f"Year {2 * i + 1}"], ALTO / 2, 70, a)
        else:
            anio = 10
            if 15 <= t < GANCHO:  # rebobinado: los años bajan hasta el 1
                anio = max(1, 10 - int(tramo(t, 15.4, 18.6) * 9))
            texto(img, [(f"YEAR {anio}", BLANCO)], (ANCHO / 2, 64), 62, 1.0)
            texto(img, [("SAME SALARY", tenue(0.9))], (ANCHO - 40, 64), 32, 1.0, ancla="rm")
            texto(img, [("SAVED 10 YEARS", VERDE)], (es.MITAD / 2, ALTO - 50), 40, 1.0)
            texto(img, [("STILL WAITING", ROJO)], (es.MITAD * 1.5, ALTO - 50), 40, 1.0)
        texto(img, [("Done, not perfect", tenue(0.7))], (ANCHO / 2, ALTO - 14), 20, 1.0)
        # Gancho: título al principio y otra vez al final (para que el último fotograma sea el primero)
        a_tit = 1.0 - tramo(t, 14.4, 15.0) if t < GANCHO else tramo(t, D - 1.5, D - 1 / FPS)
        if a_tit > 0:
            banda(img, [self.L.gancho], 400, 92, a_tit)
        if 15.0 <= t < GANCHO:
            a = ventana(t, 15.2, 3.4, 0.2, 0.3)
            banda(img, ["◀◀  REWIND"], 400, 80, a)
            banda(img, ["YEAR 1"], ALTO / 2, 130, ventana(t, 18.6, 1.4, 0.25, 0.25))
        # Minigancho cada 2 minutos
        for t0, frase in zip(MINIGANCHOS, TEXTOS_MINIGANCHO):
            banda(img, [frase], ALTO / 2, 84, ventana(t, t0, 3.0, 0.3, 0.4))
        # Mensaje central (varias veces)
        for t0 in MENSAJE_EN:
            a = ventana(t, t0, DUR_MENSAJE, 0.5, 0.6)
            if a:
                banda(img, partir(self.L.mensaje), ALTO / 2, 62, a)
        if tipo == "final":
            a = ventana(t, FINAL + 11.5, 9.0, 0.3, 0.5)
            if a:
                esc = max(0.3, rebote(tramo(t, FINAL + 11.5, FINAL + 12.0), 2.0))
                banda(img, [[("Done ", VERDE), ("> ", BLANCO), ("Perfect", ROJO)]], ALTO / 2, 130 * esc, a)
            a = ventana(t, FINAL + 21.0, 7.4, 0.4, 0.5)
            if a:
                banda(img, [f"Next: {self.L.siguiente}"], 380, 60, a)
                self._ver_siguiente(img, a, t)

    def _ver_siguiente(self, img, alfa, t):
        """Flecha y botón "Watch next ▶" (abajo a la derecha, donde YouTube pone las pantallas finales)."""
        s = ESCALA
        x0, y0, x1, y1 = 1300, 720, 1860, 860

        def boton(d, ox, oy):
            d.rounded_rectangle((x0 * s - ox, y0 * s - oy, x1 * s - ox, y1 * s - oy), radius=int(30 * s),
                                fill=(0, 0, 0, 255), outline=BLANCO + (255,), width=int(5 * s))

        capa(img, (x0 * s - 10, y0 * s - 10, x1 * s + 10, y1 * s + 10), boton, 0.75 * alfa)
        texto(img, [("Watch next ▶", mezcla((0, 0, 0), BLANCO, alfa))], ((x0 + x1) / 2, (y0 + y1) / 2), 56, 1.0)
        lz = Lienzo(img)
        mueve = 18 * math.sin(t * 5)
        col = mezcla((0, 0, 0), VERDE, alfa)
        lz.linea([(900 + mueve, 790), (1250 + mueve, 790)], 12, col)
        lz.poligono([(1250 + mueve, 760), (1295 + mueve, 790), (1250 + mueve, 820)], relleno=col)

    # --------------------------------------------------------------- audio
    def eventos(self) -> list[tuple[float, str, float, float, dict]]:
        """(segundo, efecto, ganancia, paneo, parámetros)."""
        ev = [(0.05, "titulo", 0.6, 0.0, {}), (15.0, "rebobinado", 0.7, 0.0, {"dur": 4.6}), (18.6, "ding", 0.5, 0.0, {})]
        for i, k in enumerate(self.L.capitulos):
            t0 = self.L.inicio(i)
            ev.append((t0 + 0.1, "titulo", 0.6, 0.0, {}))
            for m in range(24):
                tm = t0 + (m + 0.5) / 24 * CAPITULO
                if k == "savings":
                    ev.append((tm - CAPITULO / 24 * 0.05, "monedas", 0.35, -0.4, {"semilla": m, "golpes": 2}))
                    if m in (11, 23):
                        ev.append((tm + 1.0, "ding", 0.45, -0.4, {}))
                elif k == "debt":
                    ev.append((tm - 0.8, "caja_registradora", 0.22, 0.4, {}))
                    ev.append((tm - 0.4, "papel", 0.3, -0.4, {"dur": 0.4, "semilla": m}))
                elif k == "habits":
                    if m % 2 == 0:
                        ev.append((tm, "lapiz", 0.3, -0.4, {"dur": 0.3, "semilla": m}))
                    if m % 4 == 1:
                        ev.append((tm, "bola", 0.3, 0.4, {}))
                elif k == "decisions":
                    if m % 3 == 0:
                        ev.append((tm, "ding", 0.25, -0.4, {}))
                    if m % 6 == 2:
                        ev.append((tm, "suspiro", 0.35, 0.4, {"dur": 1.1}))
                else:
                    ev.append((tm, "caja_registradora", 0.2 + 0.2 * m / 24, -0.4, {}))
                    if m % 3 == 1:
                        ev.append((tm + 0.5, "bola", 0.3, 0.4, {}))
            ev.append((t0 + CAPITULO - 3.0, "suspiro", 0.35, 0.4, {"dur": 1.1}))
        for t0 in MINIGANCHOS:
            ev.append((t0, "titulo", 0.55, 0.0, {}))
        ev += [(FINAL + 11.5, "ding", 0.6, 0.0, {}), (FINAL + 21.0, "titulo", 0.5, 0.0, {})]
        return [e for e in ev if 0 <= e[0] < DURACION]

    def tramos_musica(self):
        """(inicio, fin, estilo): cambia de estilo en cada capítulo."""
        t = [(0.0, GANCHO, "misterio")]
        for i, k in enumerate(self.L.capitulos):
            t.append((self.L.inicio(i), self.L.inicio(i) + CAPITULO, ESTILO_CAP[k]))
        t.append((FINAL, DURACION, "triunfal"))
        return t

    def pista(self) -> np.ndarray:
        from . import audio
        from .musica import SR, generar

        n = int(round(DURACION * SR))
        musica = np.zeros((n, 2))
        cruce = 2.0  # segundos de fundido entre estilos (la música nunca se para)
        for k, (t0, t1, estilo) in enumerate(self.tramos_musica()):
            ini = max(0.0, t0 - (cruce if k else 0.0))
            dur = t1 - ini
            m, _ = generar(dur, f"{self.L.id}_{k}", estilo)
            env = np.ones(len(m))
            c = int(cruce * SR)
            if k:
                env[:c] = np.sin(np.linspace(0, np.pi / 2, c)) ** 2
            if t1 < DURACION:
                env[-c:] = np.cos(np.linspace(0, np.pi / 2, c)) ** 2
            i0 = int(round(ini * SR))
            musica[i0:i0 + len(m)] += (m * env[:, None])[: n - i0]
        efectos = np.zeros((n, 2))
        for seg, nombre, gan, pan, params in self.eventos():
            s = audio.EFECTOS[nombre](**params)
            i0 = int(round(seg * SR))
            fin = min(n, i0 + len(s))
            efectos[i0:fin, 0] += s[: fin - i0] * gan * 0.55 * (1 - pan)
            efectos[i0:fin, 1] += s[: fin - i0] * gan * 0.55 * (1 + pan)
        mezcla_ = musica * 0.9 + efectos
        pico = np.max(np.abs(mezcla_))
        if pico > 0.89:
            mezcla_ = np.tanh(mezcla_ / pico * 1.2) / np.tanh(1.2) * 0.89
        return mezcla_

    # --------------------------------------------------------------- miniatura
    def miniatura(self) -> Image.Image:
        """1280x720: los dos personajes (verde frente a rojo) y el texto grande del gancho."""
        img = self.fotograma(8.0, rotulos=False).resize((1280, 720), Image.LANCZOS)
        grande = Image.new("RGB", (1280 * ESCALA, 720 * ESCALA))
        grande.paste(img.resize((1280 * ESCALA, 720 * ESCALA), Image.BILINEAR))
        lineas = partir(self.L.gancho.upper(), 22)
        tam = 96 if len(lineas) <= 2 else 74
        s = ESCALA
        alto_b = len(lineas) * tam * 1.15 + 40

        def fondo_banda(d, x0, y0):
            d.rounded_rectangle((30 * s - x0, 20 * s - y0, 1250 * s - x0, (20 + alto_b) * s - y0), radius=int(28 * s),
                                fill=(0, 0, 0, 255))

        capa(grande, (0, 0, 1280 * s, int((40 + alto_b) * s)), fondo_banda, 0.62)
        texto(grande, [("DONE", VERDE)], (320, 665), 70, 1.0)
        texto(grande, [("PERFECT", ROJO)], (960, 665), 70, 1.0)
        for k, linea in enumerate(lineas):
            y = 20 + 20 + tam * 0.58 + k * tam * 1.15
            w = _ancho(linea, tam)
            t = tam if w < 1180 else tam * 1180 / w
            texto(grande, [(linea, BLANCO)], (640, y), t, 1.0)
        return grande.reduce(ESCALA)


# ============================================================ RENDER
_video = None


def _iniciar(ruta: str):
    global _video
    _video = VideoLargo(cargar(ruta))


def _render(i: int) -> bytes:
    return _video.fotograma(i / FPS).tobytes()


def renderizar(ruta: str, carpeta: Path, procesos: int | None = None, segundos: float | None = None):
    """Renderiza el largo. `segundos` limita la duración (solo para pruebas rápidas)."""
    from . import audio
    from .render import comando_ffmpeg

    largo = cargar(ruta)
    video = VideoLargo(largo)
    carpeta.mkdir(parents=True, exist_ok=True)
    mp4 = carpeta / f"{largo.id}.mp4"
    mini = carpeta / f"{largo.id}_miniatura.png"
    n = N_FOTOGRAMAS if segundos is None else int(segundos * FPS)
    print(f"▶ Largo {largo.id}: {n} fotogramas a {FPS} fps ({n / FPS:g} s)")
    video.miniatura().save(mini)
    for seg in (0, 30, 130, 250, 370, 470, 495):
        if seg * FPS < n:
            video.fotograma(seg).save(carpeta / f"captura_{seg}s.png")
    pista = video.pista()[: int(round(n / FPS * 48000))]
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        audio.guardar_wav(wav, pista)
        proc = subprocess.Popen(comando_ffmpeg(mp4, wav, ANCHO, ALTO, FPS), stdin=subprocess.PIPE)
        t0 = time.time()
        procesos = procesos or max(1, os.cpu_count() or 2)
        with mp.get_context("fork" if sys.platform != "win32" else "spawn").Pool(
                procesos, initializer=_iniciar, initargs=(str(ruta),)) as pool:
            for k, datos in enumerate(pool.imap(_render, range(n), chunksize=8)):
                proc.stdin.write(datos)
                if (k + 1) % (FPS * 30) == 0:
                    print(f"  {k + 1}/{n} fotogramas ({time.time() - t0:.0f} s)", flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg falló al codificar el vídeo largo.")
    print(f"✔ {mp4} ({mp4.stat().st_size / 1e6:.1f} MB) en {time.time() - t0:.0f} s")
    return largo, mp4, mini


def comprobar(mp4: Path, mini: Path, duracion: float = DURACION):
    from .verificar import verificar

    return verificar(mp4, mini, ANCHO, ALTO, FPS, duracion, rango=(duracion, duracion), tam_miniatura=(1280, 720),
                     silencio=True)


# ============================================================ PUBLICAR
SECCION = "LARGOS"


def _relativo(ruta: Path) -> str:
    return os.path.relpath(ruta, RAIZ) if ruta.is_absolute() else str(ruta)


def procesar(archivos: list[Path], destino: Path | None, salida: Path, render=None) -> int:
    """Valida, renderiza, comprueba y publica. Devuelve cuántos tuvieron problemas."""
    from .publicar import texto_errores
    from .largo_textos import generar as generar_textos

    render = render or (lambda ruta, carpeta: renderizar(str(ruta), carpeta))
    problemas = []
    for ruta in archivos:
        nombre = _relativo(ruta)
        try:
            largo = cargar(ruta)
        except ErrorConfig as e:
            problemas.append((nombre, e.errores))
            print(f"❌ {nombre}: {len(e.errores)} error(es)")
            continue
        try:
            largo, mp4, mini = render(ruta, salida / largo.id)
            resultados = comprobar(mp4, mini)
        except Exception as e:  # noqa: BLE001 — un largo que falla no bloquea nada más
            import traceback

            traceback.print_exc()
            problemas.append((nombre, [f"No se pudo hacer el vídeo largo ({type(e).__name__}: {e})."]))
            continue
        fallos = [f"El vídeo no pasó la comprobación '{r.nombre}': {r.detalle}" for r in resultados if not r.ok]
        if fallos:
            problemas.append((nombre, fallos))
            print(f"❌ {nombre}: no pasó {len(fallos)} comprobación(es)")
            continue
        print(f"✅ {nombre}: {len(resultados)}/{len(resultados)} comprobaciones")
        if destino is not None:
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy(mp4, destino / f"{largo.id}.mp4")
            shutil.copy(mini, destino / f"{largo.id}_miniatura.png")
            (destino / f"{largo.id}_textos.txt").write_text(generar_textos(largo), encoding="utf-8")
    if destino is not None:
        destino.mkdir(parents=True, exist_ok=True)
        if problemas:
            (destino / "ERRORES_LARGOS.txt").write_text(texto_errores(problemas), encoding="utf-8")
        else:
            (destino / ".sin_errores_largos").write_text("", encoding="utf-8")
    return len(problemas)


def sin_video(videos: Path) -> list[Path]:
    faltan = []
    for ruta in sorted((RAIZ / CARPETA).glob("*.txt")):
        try:
            ident = cargar(ruta).id
        except ErrorConfig:
            continue
        if not (videos / f"{ident}.mp4").exists():
            faltan.append(ruta)
    return faltan


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vídeos largos (1920x1080, 8:30).")
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--faltan", action="store_true", help="añade los largos que aún no tienen vídeo en videos/")
    ap.add_argument("--destino", default=None)
    ap.add_argument("--salida", default="salida/largos")
    ap.add_argument("--solo-comprobar", action="store_true",
                    help="valida los guiones y dibuja fotogramas de muestra (rápido, para los PR)")
    args = ap.parse_args(argv)
    archivos = [Path(a) for a in args.archivos if a.strip() and a.endswith(".txt")]
    if args.todos or (not archivos and not args.faltan):
        archivos = sorted((RAIZ / CARPETA).glob("*.txt"))
    if args.faltan:
        ya = {a.resolve() for a in archivos}
        archivos += [a for a in sin_video(RAIZ / "videos") if a.resolve() not in ya]
    archivos = [a for a in archivos if a.exists()]
    if not archivos:
        print("No hay vídeos largos que procesar.")
        return 0
    if args.solo_comprobar:
        return 1 if muestra(archivos, Path(args.salida)) else 0
    destino = Path(args.destino) if args.destino else None
    return 1 if procesar(archivos, destino, Path(args.salida)) else 0


def muestra(archivos: list[Path], salida: Path) -> int:
    """Comprobación rápida: guion válido y fotogramas de muestra sin negro (para los pull requests)."""
    malos = 0
    for ruta in archivos:
        try:
            v = VideoLargo(cargar(ruta))
            carpeta = salida / v.L.id
            carpeta.mkdir(parents=True, exist_ok=True)
            for seg in (0, 17, 21, 60, 121, 160, 250, 300, 362, 420, 482, 495, 505):
                arr = np.asarray(v.fotograma(seg)).astype(np.float32)
                luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
                if np.mean(luma > 26) < 0.05:
                    raise RuntimeError(f"el segundo {seg} sale casi negro")
                Image.fromarray(arr.astype(np.uint8)).save(carpeta / f"captura_{seg}s.png")
            v.miniatura().save(carpeta / "miniatura.png")
            print(f"✅ {_relativo(ruta)}: guion válido y fotogramas de muestra correctos")
        except (ErrorConfig, RuntimeError) as e:
            malos += 1
            print(f"❌ {_relativo(ruta)}: {e}")
    return malos


if __name__ == "__main__":
    sys.exit(main())

