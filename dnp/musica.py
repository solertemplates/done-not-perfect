"""Música generada por código, DISTINTA en cada episodio.

El id del episodio elige un estilo (8 estilos) y, dentro del estilo, la
tonalidad, el tempo, la progresión de acordes, la melodía, el ritmo de la
batería y los instrumentos. Siempre en bucle perfecto: la duración es un
número entero de compases y las colas de las notas dan la vuelta al final.
"""
from __future__ import annotations

import random
import re

import numpy as np

SR = 48000

ESTILOS = ["alegre", "epico_suave", "lofi", "piano", "ukelele", "electronico_suave", "misterio", "triunfal"]

ESCALAS = {
    "mayor": [0, 2, 4, 5, 7, 9, 11],
    "menor": [0, 2, 3, 5, 7, 8, 10],
    "dorica": [0, 2, 3, 5, 7, 9, 10],
    "menor_armonica": [0, 2, 3, 5, 7, 8, 11],
    "mixolidia": [0, 2, 4, 5, 7, 9, 10],
}
PROGRESIONES = {  # grados de la escala (0 = tónica)
    "mayor": [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 3], [5, 3, 0, 4], [0, 3, 5, 4], [0, 1, 3, 4]],
    "menor": [[0, 5, 2, 6], [0, 3, 4, 0], [0, 6, 5, 6], [0, 5, 3, 4], [0, 2, 5, 6]],
}

# estilo: escalas posibles, tempo, instrumentos y batería
_DEF = {
    "alegre": dict(escalas=["mayor", "mixolidia"], bpm=(108, 128), acordes="pulsado", melodia="campanita",
                   bajo="saltarin", bateria=["pop", "pop2"], dens=(0.55, 0.8)),
    "epico_suave": dict(escalas=["menor"], bpm=(78, 94), acordes="cuerdas", melodia="trompa", bajo="largo",
                        bateria=["tambores", "tambores2"], dens=(0.3, 0.5)),
    "lofi": dict(escalas=["dorica", "menor"], bpm=(70, 86), acordes="epiano", melodia="epiano_suave",
                 bajo="lofi", bateria=["lofi", "lofi2"], dens=(0.35, 0.6), septimas=True, swing=True, vinilo=True),
    "piano": dict(escalas=["mayor", "menor"], bpm=(66, 90), acordes="piano_arpegio", melodia="piano",
                  bajo="piano", bateria=[None], dens=(0.4, 0.7)),
    "ukelele": dict(escalas=["mayor"], bpm=(96, 116), acordes="rasgueo", melodia="silbido", bajo="saltarin",
                    bateria=["shaker", "palmas"], dens=(0.45, 0.7)),
    "electronico_suave": dict(escalas=["menor", "dorica"], bpm=(100, 122), acordes="pad_sierra",
                              melodia="arpegio_16", bajo="sinte", bateria=["house", "house2"], dens=(0.5, 0.8)),
    "misterio": dict(escalas=["menor_armonica"], bpm=(70, 90), acordes="dron", melodia="celesta",
                     bajo="pizzicato", bateria=["reloj"], dens=(0.25, 0.45)),
    "triunfal": dict(escalas=["mayor"], bpm=(98, 118), acordes="metales", melodia="metal_lead", bajo="timbal",
                     bateria=["marcha", "marcha2"], dens=(0.45, 0.65)),
}
_RITMOS = {  # (instrumento: pasos de semicorchea 0..15)
    "pop": {"bombo": [0, 8, 10], "caja": [4, 12], "charles": [2, 6, 10, 14]},
    "pop2": {"bombo": [0, 6, 8], "caja": [4, 12], "charles": list(range(0, 16, 2))},
    "tambores": {"taiko": [0, 10], "toms": [6, 12, 14]},
    "tambores2": {"taiko": [0, 3, 8], "toms": [12, 13, 14, 15]},
    "lofi": {"bombo": [0, 7, 10], "caja": [4, 12], "charles": list(range(0, 16, 2))},
    "lofi2": {"bombo": [0, 3, 9], "caja": [4, 12], "charles": [0, 2, 4, 6, 8, 10, 12, 14, 15]},
    "shaker": {"shaker": list(range(16)), "bombo": [0, 8]},
    "palmas": {"palmas": [4, 12], "shaker": list(range(0, 16, 2)), "bombo": [0, 10]},
    "house": {"bombo": [0, 4, 8, 12], "charles": [2, 6, 10, 14], "palmas": [4, 12]},
    "house2": {"bombo": [0, 4, 8, 12], "charles": [2, 6, 10, 14, 15], "shaker": list(range(1, 16, 2))},
    "reloj": {"tic": [0, 4, 8, 12], "tac": [2, 6, 10, 14]},
    "marcha": {"caja": [0, 3, 4, 8, 11, 12, 14, 15], "bombo": [0, 8], "platillo": [0]},
    "marcha2": {"caja": [2, 4, 6, 10, 12, 13, 14], "bombo": [0, 4, 8, 12]},
}


# --- utilidades ---------------------------------------------------------------------

def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _env(n, ataque, caida=None, sostenido=None, suelta=0.05):
    t = np.arange(n) / SR
    e = np.clip(t / max(ataque, 1e-4), 0, 1)
    if caida is not None:
        e = e * np.exp(-t / caida)
    r = int(suelta * SR)
    if r and n > r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _armonicos(f, dur, pesos, decaes, inarm=0.0, vibrato=0.0, ataque=0.004):
    t = _t(dur)
    if vibrato:
        fase_v = vibrato * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.3, 0, 1)
    else:
        fase_v = 0
    x = np.zeros_like(t)
    for k, (p, d) in enumerate(zip(pesos, decaes), 1):
        fk = f * k * (1 + inarm * k * k)
        if fk > SR / 2.2:
            break
        x += p * np.sin(2 * np.pi * fk * t + k * fase_v) * (np.exp(-t / d) if d else 1)
    return x * _env(len(t), ataque)


def _ruido(n, rng, lo, hi):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    X[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(X, n)


# --- instrumentos (devuelven mono) -------------------------------------------------

def instrumento(nombre, f, dur, rng):
    if nombre == "pluck":  # ukelele / guitarra pulsada
        return _armonicos(f, dur, [1, .6, .4, .25, .15, .1], [.5, .3, .2, .14, .1, .08], ataque=0.002)
    if nombre == "piano":
        return _armonicos(f, dur, [1, .5, .3, .2, .1, .06], [1.4, .8, .5, .35, .25, .2], inarm=0.0004, ataque=0.003)
    if nombre == "epiano":
        t = _t(dur)
        x = (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t) * np.exp(-t / .3)
             + .12 * np.sin(2 * np.pi * 14 * f * t) * np.exp(-t / .03)) * np.exp(-t / 1.6)
        return x * (1 + .12 * np.sin(2 * np.pi * 4.5 * t)) * _env(len(t), .004)
    if nombre == "campanita":
        t = _t(dur)
        x = np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / .15) \
            + .2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / .06)
        return x * np.exp(-t / .5) * _env(len(t), .002)
    if nombre == "celesta":
        t = _t(dur)
        x = np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / .2)
        return x * np.exp(-t / .9) * _env(len(t), .002)
    if nombre == "silbido":
        return _armonicos(f, dur, [1, .08], [0, 0], vibrato=.004 * 60, ataque=.04) * _env(int(dur * SR), .04, suelta=.08)
    if nombre in ("pad", "cuerdas", "pad_sierra"):
        n = 10 if nombre == "pad_sierra" else 6
        pesos = [1 / k for k in range(1, n + 1)]
        a = _armonicos(f, dur, pesos, [0] * n, vibrato=.01 if nombre == "cuerdas" else 0, ataque=.35)
        b = _armonicos(f * 1.004, dur, pesos, [0] * n, ataque=.35)
        return (a + b) * .5 * _env(int(dur * SR), .35, suelta=min(.6, dur / 3))
    if nombre in ("metales", "trompa", "metal_lead"):
        n = 8 if nombre != "trompa" else 5
        x = _armonicos(f, dur, [1 / k ** .8 for k in range(1, n + 1)], [0] * n, vibrato=.006, ataque=.06)
        return x * _env(len(x), .06, suelta=.1)
    if nombre == "bajo":
        return _armonicos(f, dur, [1, .35, .1], [.9, .5, .3], ataque=.006)
    if nombre == "sinte_bajo":
        return _armonicos(f, dur, [1, .5, .33, .25], [.5, .3, .2, .15], ataque=.004)
    if nombre == "pizzicato":
        return _armonicos(f, dur, [1, .5, .3], [.25, .15, .1], ataque=.002)
    if nombre == "timbal":
        t = _t(dur)
        return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * 1.5 * f * t)) * np.exp(-t / .5) * _env(len(t), .003)
    raise ValueError(nombre)


def percusion(nombre, rng):
    if nombre in ("bombo", "taiko"):
        d = .35 if nombre == "bombo" else .8
        t = _t(d)
        f0, f1 = (110, 45) if nombre == "bombo" else (90, 38)
        fase = 2 * np.pi * (f1 * t + (f0 - f1) * .04 * (1 - np.exp(-t / .04)))
        return np.sin(fase) * np.exp(-t / (d / 3)) * (1.0 if nombre == "bombo" else 1.3)
    if nombre == "toms":
        t = _t(.4)
        return np.sin(2 * np.pi * (150 * t)) * np.exp(-t / .12) * .7
    if nombre == "caja":
        n = int(.2 * SR)
        return (_ruido(n, rng, 1500, 9000) * .6 + np.sin(2 * np.pi * 190 * _t(.2)) * .4) * _env(n, .001, .05)
    if nombre == "palmas":
        n = int(.18 * SR)
        x = _ruido(n, rng, 900, 6000) * _env(n, .001, .04)
        return x + np.roll(x, int(.011 * SR)) * .6
    if nombre in ("charles", "shaker"):
        d = .06 if nombre == "charles" else .09
        n = int(d * SR)
        return _ruido(n, rng, 6000, 14000) * _env(n, .001 if nombre == "charles" else .015, d / 4) * \
            (.5 if nombre == "charles" else .35)
    if nombre in ("tic", "tac"):
        t = _t(.04)
        return np.sin(2 * np.pi * (2400 if nombre == "tic" else 1800) * t) * np.exp(-t / .006) * .5
    if nombre == "platillo":
        n = int(1.2 * SR)
        return _ruido(n, rng, 4000, 15000) * _env(n, .002, .4) * .45
    raise ValueError(nombre)


# --- composición -----------------------------------------------------------------------

def _poner(buf, x, inicio, gl, gr):
    n = len(buf)
    i = inicio % n
    pos = 0
    while pos < len(x):
        m = min(len(x) - pos, n - i)
        buf[i:i + m, 0] += x[pos:pos + m] * gl
        buf[i:i + m, 1] += x[pos:pos + m] * gr
        pos += m
        i = 0


def receta(ident: str, estilo: str | None = None) -> dict:
    """Decide estilo y variaciones a partir del id (siempre igual para el mismo id)."""
    from .variedad import numero

    rnd = random.Random(numero(ident, "musica"))
    if estilo not in ESTILOS:
        # Con número de episodio, 8 episodios seguidos nunca repiten estilo (0, 3, 6, 1, 4, 7, 2, 5...).
        m = re.match(r"ep(\d+)", ident)
        i = int(m.group(1)) * 3 if m else numero(ident, "estilo")
        estilo = ESTILOS[i % len(ESTILOS)]
    d = _DEF[estilo]
    escala = rnd.choice(d["escalas"])
    familia = "mayor" if escala in ("mayor", "mixolidia") else "menor"
    return dict(
        estilo=estilo,
        escala=escala,
        tonica=rnd.randrange(12),
        bpm=rnd.uniform(*d["bpm"]),
        progresion=rnd.choice(PROGRESIONES[familia]),
        bateria=rnd.choice(d["bateria"]),
        densidad=rnd.uniform(*d["dens"]),
        semilla=rnd.randrange(1 << 30),
        octava=rnd.choice((0, 12)) if estilo in ("piano", "alegre", "lofi") else 0,
    )


def _acorde(escala, grado, septima=False):
    notas = [escala[(grado + k) % 7] + 12 * ((grado + k) // 7) for k in (0, 2, 4)]
    if septima:
        notas.append(escala[(grado + 6) % 7] + 12 * ((grado + 6) // 7))
    return notas


def generar(duracion: float, ident: str, estilo: str | None = None) -> tuple[np.ndarray, dict]:
    r = receta(ident, estilo)
    d = _DEF[r["estilo"]]
    rng = np.random.default_rng(r["semilla"])
    rnd = random.Random(r["semilla"])
    n = int(round(duracion * SR))
    compases = max(2, round(duracion / (4 * 60 / r["bpm"])))
    pulso = duracion / (compases * 4)
    r["bpm_real"] = 60 / pulso
    buf = np.zeros((n, 2))
    escala = ESCALAS[r["escala"]]
    raiz = 48 + (r["tonica"] + 5) % 12  # entre F3 y E4
    semi = pulso / 4

    def paso(c, k):  # instante de la semicorchea k del compás c (con swing)
        t = c * 4 * pulso + k * semi
        if d.get("swing") and k % 4 == 2:
            t += semi * 0.33
        return t

    def tocar(inst, midi, t0, dur, gan, pan=0.0):
        x = instrumento(inst, _hz(midi), dur, rng)
        _poner(buf, x * gan, int(round(t0 * SR)), 1 - pan, 1 + pan)

    # Melodía: motivo de 2 compases, repetido con variaciones (A A' A B)
    def motivo():
        notas, grado = [], rnd.choice((0, 2, 4))
        for k in range(32):
            fuerte = k % 4 == 0
            if rnd.random() < (r["densidad"] if not fuerte else min(1, r["densidad"] + .3)):
                grado = max(-2, min(9, grado + rnd.choice((-2, -1, -1, 1, 1, 2, 0))))
                largo = rnd.choice((2, 2, 4)) if fuerte else 2
                notas.append((k, grado, largo))
        return notas

    A = motivo()
    B = motivo()
    for c in range(compases):
        g = r["progresion"][c % len(r["progresion"])]
        acorde = _acorde(escala, g, d.get("septimas", False))
        t0 = c * 4 * pulso
        estilo_ac = d["acordes"]
        # --- acordes
        if estilo_ac in ("cuerdas", "pad_sierra", "dron"):
            inst = "pad_sierra" if estilo_ac == "pad_sierra" else ("cuerdas" if estilo_ac == "cuerdas" else "pad")
            notas = acorde if estilo_ac != "dron" else [acorde[0], acorde[0] + 7]
            for j, s in enumerate(notas):
                tocar(inst, raiz + s, t0, 4 * pulso + .5, .05 if estilo_ac != "pad_sierra" else .035, (j - 1) * .3)
        elif estilo_ac == "epiano":
            for k in (0, 6) if c % 2 else (0, 10):
                for s in acorde:
                    tocar("epiano", raiz + s, paso(c, k), 1.4, .045)
        elif estilo_ac == "piano_arpegio":
            orden = [0, 1, 2, 1, 2, 1, 0, 1] if rnd.random() < .5 else [0, 2, 1, 2, 0, 2, 1, 2]
            for j, idx in enumerate(orden):
                tocar("piano", raiz + acorde[idx] + (12 if j == 4 else 0), paso(c, j * 2), 1.6, .07, .3 * np.sin(j))
        elif estilo_ac == "pulsado":
            for k in (0, 4, 8, 12):
                for s in acorde:
                    tocar("pluck", raiz + s + 12, paso(c, k + (2 if r["semilla"] % 2 else 0)), .5, .05, -.2)
        elif estilo_ac == "rasgueo":
            patron = [0, 3, 6, 8, 10, 14] if r["semilla"] % 3 else [0, 4, 6, 10, 12, 14]
            for k in patron:
                for j, s in enumerate(acorde + [acorde[0] + 12]):
                    tocar("pluck", raiz + s + 12, paso(c, k) + j * .012, .6, .045, -.25)
        elif estilo_ac == "metales":
            for k, largo in ((0, 6), (6, 2), (8, 8)):
                for s in acorde:
                    tocar("metales", raiz + s, paso(c, k), largo * semi, .035)
        # --- bajo
        f_bajo = raiz - 12 + acorde[0] % 12 - (12 if acorde[0] % 12 > 7 else 0)
        estilo_b = d["bajo"]
        if estilo_b == "largo":
            tocar("bajo", f_bajo, t0, 4 * pulso, .16)
        elif estilo_b == "timbal":
            for k in (0, 8, 12):
                tocar("timbal", f_bajo, paso(c, k), 1.0, .2)
        elif estilo_b == "pizzicato":
            for j, k in enumerate((0, 4, 8, 12)):
                tocar("pizzicato", f_bajo + (0, 7, 12, 7)[j], paso(c, k), .5, .14)
        elif estilo_b == "sinte":
            for k in range(0, 16, 2):
                tocar("sinte_bajo", f_bajo + (12 if k % 8 == 6 else 0), paso(c, k), semi * 1.8, .1)
        else:
            golpes = (0, 6, 8, 14) if estilo_b == "saltarin" else ((0, 10) if estilo_b == "lofi" else (0, 8))
            for k in golpes:
                tocar("bajo", f_bajo, paso(c, k), 1.5 * pulso, .17)
        # --- melodía
        motivo_c = (A if c % 4 != 3 else B)
        mitad = (c % 2) * 16
        inst_mel = {"campanita": "campanita", "trompa": "trompa", "epiano_suave": "epiano", "piano": "piano",
                    "silbido": "silbido", "celesta": "celesta", "metal_lead": "metal_lead",
                    "arpegio_16": "pluck"}[d["melodia"]]
        if d["melodia"] == "arpegio_16":
            for k in range(16):
                s = acorde[k % len(acorde)] + 12 * (k // len(acorde) % 2) + 12
                tocar("pluck", raiz + s, paso(c, k), .35, .04, .4 * np.sin(k))
        for k, grado, largo in motivo_c:
            if not (mitad <= k < mitad + 16):
                continue
            g2 = grado + (1 if (c % 4 == 2 and k % 8 == 4) else 0)  # pequeña variación (A')
            midi = raiz + 12 + r["octava"] + escala[g2 % 7] + 12 * (g2 // 7)
            gan = {"silbido": .05, "trompa": .06, "metal_lead": .05, "campanita": .07, "celesta": .07}.get(inst_mel, .08)
            tocar(inst_mel, midi, paso(c, k - mitad), max(.25, largo * semi * 1.6), gan, .15)
        # --- batería
        if r["bateria"]:
            for nombre, pasos in _RITMOS[r["bateria"]].items():
                for k in pasos:
                    if nombre == "platillo" and c % 4:
                        continue
                    gan = {"bombo": .35, "taiko": .3, "toms": .18, "caja": .16, "palmas": .14, "charles": .12,
                           "shaker": .12, "tic": .1, "tac": .07, "platillo": .1}[nombre]
                    _poner(buf, percusion(nombre, rng) * gan, int(round(paso(c, k) * SR)), 1, 1)
    if d.get("vinilo"):  # crepitar de vinilo, muy suave
        clics = rng.integers(0, n, size=int(duracion * 25))
        buf[clics] += rng.uniform(-.06, .06, size=(len(clics), 1))
        buf += _ruido(n, rng, 2000, 8000)[:, None] * .004
    rms = np.sqrt(np.mean(buf ** 2)) + 1e-9
    return buf * (0.10 / rms), r
