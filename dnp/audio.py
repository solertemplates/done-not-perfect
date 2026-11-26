"""Audio generado por código: música suave en bucle y efectos de sonido.

Todo se sintetiza con numpy (48 kHz, estéreo). Si hay un archivo de música en
la carpeta audio/ y el JSON dice "musica": "auto", se usa ese archivo en lugar
de la música generada (los efectos se siguen generando).
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
EXT_MUSICA = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".aiff", ".aif")


# --- utilidades -----------------------------------------------------------------

def muestras(dur: float) -> int:
    """Número de muestras de una duración. Se redondea (no se trunca): 0,41249999999999964 s y
    0,4125 s deben dar el mismo sonido aunque la suma en coma flotante salga distinta."""
    return int(round(dur * SR))


def _t(dur: float) -> np.ndarray:
    return np.arange(muestras(dur)) / SR


def _ruido(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n)


def _banda(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Filtro paso banda por FFT con bordes suaves."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    ancho = 0.25
    g = np.clip((f - lo * (1 - ancho)) / (lo * ancho + 1e-9), 0, 1) * np.clip((hi * (1 + ancho) - f) / (hi * ancho), 0, 1)
    y = np.fft.irfft(X * g, len(x))
    return y / (np.max(np.abs(y)) + 1e-9)


def _decae(n: int, tau: float) -> np.ndarray:
    return np.exp(-np.arange(n) / SR / tau)


def _fundido(x: np.ndarray, entrada: float = 0.005, salida: float = 0.02) -> np.ndarray:
    n = len(x)
    a, b = min(n, int(entrada * SR)), min(n, int(salida * SR))
    env = np.ones(n)
    if a:
        env[:a] = np.linspace(0, 1, a)
    if b:
        env[n - b:] *= np.linspace(1, 0, b)
    return x * env


def _seno_barrido(f0: float, f1: float, dur: float) -> np.ndarray:
    n = muestras(dur)
    f = np.geomspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


# --- efectos ----------------------------------------------------------------------

def martillo(semilla: int = 0) -> np.ndarray:
    rng = np.random.default_rng(100 + semilla)
    n = int(0.32 * SR)
    clic = _banda(_ruido(n, rng), 2500, 9000) * _decae(n, 0.004)
    madera = _banda(_ruido(n, rng), 500, 2200) * _decae(n, 0.03)
    golpe = _seno_barrido(170, 85, 0.32) * _decae(n, 0.06)
    metal = np.sin(2 * np.pi * (2300 + 80 * semilla % 300) * _t(0.32)) * _decae(n, 0.05)
    return _fundido(0.5 * clic + 0.6 * madera + 0.9 * golpe + 0.12 * metal)


def golpe_madera() -> np.ndarray:
    rng = np.random.default_rng(7)
    n = int(0.7 * SR)
    grave = _seno_barrido(85, 45, 0.7) * _decae(n, 0.12)
    cuerpo = _banda(_ruido(n, rng), 60, 500) * _decae(n, 0.09)
    sonido = grave + 0.6 * cuerpo
    for k, dt in enumerate((0.05, 0.09, 0.14, 0.2)):  # tablas que se asientan
        i = int(dt * SR)
        m = int(0.08 * SR)
        sonido[i:i + m] += 0.35 / (k + 1) * _banda(_ruido(m, rng), 400, 2500) * _decae(m, 0.015)
    return _fundido(sonido)


def crujido(semilla: int = 0) -> np.ndarray:
    """Golpe seco de madera (la silla que se tuerce)."""
    rng = np.random.default_rng(30 + semilla)
    n = int(0.35 * SR)
    s = _banda(_ruido(n, rng), 300, 1800) * _decae(n, 0.04) + 0.7 * _seno_barrido(140, 100, 0.35) * _decae(n, 0.05)
    return _fundido(s)


def ding() -> np.ndarray:
    dur = 1.8
    t = _t(dur)
    n = len(t)
    f0 = 1318.5  # Mi6
    s = np.zeros(n)
    for mult, amp, tau in ((1.0, 1.0, 0.9), (2.0, 0.35, 0.5), (2.76, 0.25, 0.35), (4.07, 0.12, 0.2)):
        s += amp * np.sin(2 * np.pi * f0 * mult * t) * _decae(n, tau)
    s2 = np.zeros(n)
    i = int(0.09 * SR)
    s2[i:] = 0.6 * np.sin(2 * np.pi * f0 * 1.5 * t[: n - i]) * _decae(n - i, 0.7)  # quinta: "¡conseguido!"
    return _fundido(s + s2, 0.002, 0.2)


def lapiz(dur: float, semilla: int = 0) -> np.ndarray:
    rng = np.random.default_rng(40 + semilla)
    n = muestras(dur)
    base = _banda(_ruido(n, rng), 2500, 8000)
    trazos = np.clip(np.sin(2 * np.pi * 4.5 * _t(dur) + rng.uniform(0, 6)) + 0.3, 0, 1) ** 1.5
    return _fundido(base * trazos * 0.5, 0.03, 0.05)


def borrador(dur: float, semilla: int = 0) -> np.ndarray:
    rng = np.random.default_rng(50 + semilla)
    n = muestras(dur)
    base = _banda(_ruido(n, rng), 900, 5000)
    frote = np.abs(np.sin(2 * np.pi * 4.6 * _t(dur))) ** 1.2
    return _fundido(base * (0.25 + 0.75 * frote), 0.03, 0.06)


def papel(dur: float = 0.45, semilla: int = 0) -> np.ndarray:
    rng = np.random.default_rng(60 + semilla)
    n = muestras(dur)
    s = np.zeros(n)
    for _ in range(int(90 * dur / 0.45)):
        i = int(rng.beta(1.6, 1.6) * (n - 600))
        m = int(rng.uniform(0.002, 0.012) * SR)
        trozo = _ruido(m, rng) * _decae(m, rng.uniform(0.001, 0.004)) * rng.uniform(0.2, 1.0)
        s[i:i + m] += trozo[: max(0, min(m, n - i))]
    s = _banda(s, 900, 9000)
    return _fundido(s * 0.8, 0.005, 0.05)


def hoja(semilla: int = 0) -> np.ndarray:
    """Hoja nueva que se saca: un 'fsss' corto."""
    rng = np.random.default_rng(70 + semilla)
    n = int(0.28 * SR)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return _fundido(_banda(_ruido(n, rng), 1500, 7000) * env * 0.5)


def bola() -> np.ndarray:
    """Bola de papel que cae al suelo."""
    rng = np.random.default_rng(80)
    n = int(0.15 * SR)
    return _fundido(_banda(_ruido(n, rng), 600, 4000) * _decae(n, 0.02) * 0.7)


def suspiro(dur: float = 1.1) -> np.ndarray:
    """Exhalación sin voz: ruido de aire cuyo formante baja, con envolvente de suspiro."""
    rng = np.random.default_rng(90)
    n = muestras(dur)
    bloques = 14
    s = np.zeros(n)
    L = n // bloques
    ventana = np.hanning(2 * L)
    for b in range(bloques):
        u = b / (bloques - 1)
        centro = 1300 * (1 - u) + 450 * u
        trozo = _banda(_ruido(2 * L, rng), centro * 0.55, centro * 1.5) * ventana
        i = b * L - L // 2
        a0, a1 = max(0, i), min(n, i + 2 * L)
        s[a0:a1] += trozo[a0 - i:a1 - i]
    t = np.linspace(0, 1, n)
    env = np.clip(t / 0.18, 0, 1) * np.clip((1 - t) / 0.55, 0, 1) ** 1.3
    grave = _banda(_ruido(n, rng), 120, 400) * 0.25
    return _fundido((s + grave) * env * 0.9, 0.02, 0.1)


def rebobinado(dur: float) -> np.ndarray:
    """Cinta rebobinando: chirrido que sube con vibrato rápido y siseo."""
    rng = np.random.default_rng(11)
    n = muestras(dur)
    t = np.arange(n) / SR
    u = t / dur
    f = 260 + 1300 * u ** 1.4 + 70 * np.sin(2 * np.pi * 23 * t)
    fase = 2 * np.pi * np.cumsum(f) / SR
    tono = sum(np.sin(k * fase) / k for k in range(1, 7))
    chop = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 31 * t))
    siseo = _banda(_ruido(n, rng), 3000, 11000) * 0.35
    env = np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.12, 0, 1)
    return _fundido((0.22 * tono * chop + siseo) * env, 0.01, 0.03)


def titulo() -> np.ndarray:
    """'Pop' suave para el cartel final."""
    n = int(0.5 * SR)
    pop = _seno_barrido(520, 260, 0.5) * _decae(n, 0.05)
    brillo = np.sin(2 * np.pi * 1046.5 * _t(0.5)) * _decae(n, 0.18) * 0.25
    return _fundido(pop + brillo, 0.002, 0.1)


def clavo_torcido() -> np.ndarray:
    """Clavo que se dobla: 'boing' metálico que cae de tono, con un rasguño al principio."""
    rng = np.random.default_rng(12)
    dur = 0.65
    n = muestras(dur)
    t = np.arange(n) / SR
    f = 820 * np.exp(-t * 1.6) + 260 + 26 * np.sin(2 * np.pi * 17 * t) * np.exp(-t * 3)
    fase = 2 * np.pi * np.cumsum(f) / SR
    boing = (np.sin(fase) + 0.35 * np.sin(2.7 * fase)) * _decae(n, 0.22)
    m = int(0.09 * SR)
    rasguno = np.zeros(n)
    rasguno[:m] = _banda(_ruido(m, rng), 2500, 9000) * np.linspace(1, 0, m) ** 2
    return _fundido(0.6 * boing + 0.4 * rasguno, 0.002, 0.08)


def regla(semilla: int = 0) -> np.ndarray:
    """Regla de plástico: deslizamiento corto y dos clics al apoyarla."""
    rng = np.random.default_rng(140 + semilla)
    dur = 0.4
    n = muestras(dur)
    s = np.zeros(n)
    m = int(0.16 * SR)
    s[:m] = _banda(_ruido(m, rng), 1800, 7000) * np.sin(np.linspace(0, np.pi, m)) * 0.45
    for k, dt in enumerate((0.17, 0.25)):
        i = int(dt * SR)
        c = int(0.03 * SR)
        clic = (_banda(_ruido(c, rng), 2000, 8000) * _decae(c, 0.004)
                + 0.5 * np.sin(2 * np.pi * 2900 * np.arange(c) / SR) * _decae(c, 0.008))
        s[i:i + c] += clic * (0.9 if k == 0 else 0.6)
    return _fundido(s, 0.005, 0.03)


def mandarria(semilla: int = 0) -> np.ndarray:
    """Golpe de mandarria contra la roca: impacto grave y seco con chasquido de piedra."""
    rng = np.random.default_rng(160 + semilla)
    n = int(0.45 * SR)
    grave = _seno_barrido(110, 48, 0.45) * _decae(n, 0.09)
    piedra = _banda(_ruido(n, rng), 400, 3500) * _decae(n, 0.025)
    chasquido = _banda(_ruido(n, rng), 3000, 10000) * _decae(n, 0.006)
    grava = np.zeros(n)
    for _ in range(6):
        i = int(rng.uniform(0.02, 0.22) * SR)
        m = int(0.012 * SR)
        grava[i:i + m] += _banda(_ruido(m, rng), 1500, 6000) * _decae(m, 0.004) * rng.uniform(0.1, 0.3)
    return _fundido(1.0 * grave + 0.55 * piedra + 0.3 * chasquido + grava, 0.001, 0.08)


def grieta(semilla: int = 0) -> np.ndarray:
    """La roca se agrieta: crujido seco con chasquidos y un retumbo grave."""
    rng = np.random.default_rng(170 + semilla)
    dur = 0.5
    n = muestras(dur)
    s = np.zeros(n)
    for _ in range(40):
        i = int(rng.beta(1.4, 2.6) * (n - 800))
        m = int(rng.uniform(0.002, 0.009) * SR)
        s[i:i + m] += _ruido(m, rng) * _decae(m, rng.uniform(0.001, 0.003)) * rng.uniform(0.3, 1.0)
    s = _banda(s, 700, 7000)
    retumbo = _banda(_ruido(n, rng), 40, 220) * np.exp(-np.arange(n) / SR / 0.15) * 0.5
    return _fundido(0.7 * s + retumbo, 0.002, 0.08)


def crac(semilla: int = 0) -> np.ndarray:
    """La roca se parte: chasquido fuerte, golpe grave y piedrecitas que caen."""
    rng = np.random.default_rng(180 + semilla)
    dur = 1.1
    n = muestras(dur)
    chasquido = _banda(_ruido(n, rng), 1500, 12000) * _decae(n, 0.018)
    boom = _seno_barrido(80, 35, dur) * _decae(n, 0.2)
    cuerpo = _banda(_ruido(n, rng), 150, 1500) * _decae(n, 0.08)
    piedras = np.zeros(n)
    for _ in range(30):
        i = int(rng.uniform(0.1, 0.85) * n)
        m = int(rng.uniform(0.004, 0.015) * SR)
        piedras[i:i + m] += _banda(_ruido(m, rng), 1200, 7000) * _decae(m, 0.004) * rng.uniform(0.05, 0.25)
    return _fundido(0.8 * chasquido + 1.0 * boom + 0.6 * cuerpo + piedras, 0.001, 0.15)


EFECTOS = {
    "martillo": martillo, "golpe_madera": golpe_madera, "crujido": crujido, "ding": ding, "lapiz": lapiz,
    "borrador": borrador, "papel": papel, "hoja": hoja, "bola": bola, "suspiro": suspiro,
    "rebobinado": rebobinado, "titulo": titulo, "clavo_torcido": clavo_torcido, "regla": regla,
    "mandarria": mandarria, "grieta": grieta, "crac": crac,
}


# --- música -------------------------------------------------------------------------

_NOTAS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _poner(buf: np.ndarray, sonido: np.ndarray, inicio: int, gan_l: float, gan_r: float) -> None:
    """Suma `sonido` en `buf` (estéreo) a partir de `inicio`, dando la vuelta al final (bucle)."""
    n = buf.shape[0]
    i = inicio % n
    resto = len(sonido)
    pos = 0
    while resto > 0:
        m = min(resto, n - i)
        buf[i:i + m, 0] += sonido[pos:pos + m] * gan_l
        buf[i:i + m, 1] += sonido[pos:pos + m] * gan_r
        pos += m
        resto -= m
        i = 0


def musica(duracion: float, bpm_aprox: float = 80) -> np.ndarray:
    """Música suave en bucle perfecto: el tempo se ajusta para que la duración
    sea un número entero de compases y las colas de las notas dan la vuelta."""
    n = int(round(duracion * SR))
    compases = max(2, round(duracion / (4 * 60 / bpm_aprox)))
    pulso = duracion / (compases * 4)
    buf = np.zeros((n, 2))
    acordes = [("C", [0, 4, 7]), ("A", [-3, 0, 4]), ("F", [-7, -3, 0]), ("G", [-5, -1, 2])]
    seq = [acordes[i % 4] for i in range(compases)]
    seq[-1] = acordes[3]  # el último compás prepara la vuelta al primero
    raiz = 60
    rng = np.random.default_rng(3)
    for c, (nombre, notas) in enumerate(seq):
        t0 = c * 4 * pulso
        # Colchón suave (pad)
        dur_pad = 4 * pulso + 0.6
        t = _t(dur_pad)
        env = np.clip(t / 0.5, 0, 1) * np.clip((dur_pad - t) / 0.8, 0, 1)
        for k, semi in enumerate(notas):
            f = _hz(raiz + semi)
            onda = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
            det = np.sin(2 * np.pi * f * 1.003 * t)
            _poner(buf, onda * env * 0.05, int(t0 * SR), 1.0, 0.7)
            _poner(buf, det * env * 0.05, int(t0 * SR), 0.7, 1.0)
        # Bajo en los tiempos 1 y 3
        for b in (0, 2):
            d = 1.6 * pulso
            tt = _t(d)
            f = _hz(raiz - 24 + notas[0] % 12 - (12 if notas[0] % 12 > 7 else 0))
            nota = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * _decae(len(tt), 0.5)
            _poner(buf, _fundido(nota, 0.01, 0.1) * 0.22, int((t0 + b * pulso) * SR), 1.0, 1.0)
        # Arpegio tipo marimba en corcheas
        patron = [0, 1, 2, 1, 0, 2, 1, 2]
        for j, idx in enumerate(patron):
            semi = notas[idx] + 12
            if j == 4:
                semi += 12 if rng.random() < 0.5 else 0
            f = _hz(raiz + semi)
            d = 0.9
            tt = _t(d)
            nota = (np.sin(2 * np.pi * f * tt) * _decae(len(tt), 0.35)
                    + 0.2 * np.sin(2 * np.pi * 4 * f * tt) * _decae(len(tt), 0.05))
            pan = 0.3 * np.sin(j)
            _poner(buf, _fundido(nota, 0.003, 0.05) * 0.10, int((t0 + j * pulso / 2) * SR), 1 - pan, 1 + pan)
        # Shaker suave a contratiempo
        for j in range(4):
            m = int(0.05 * SR)
            sh = _banda(rng.standard_normal(m), 5000, 12000) * _decae(m, 0.012)
            _poner(buf, sh * 0.05, int((t0 + (j + 0.5) * pulso) * SR), 0.8, 1.0)
    return buf


def leer_musica_externa(ruta: Path, duracion: float) -> np.ndarray:
    """Decodifica con ffmpeg, recorta o repite hasta la duración y suaviza la unión del bucle."""
    n = int(round(duracion * SR))
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(ruta), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        capture_output=True,
    )
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"No pude leer la música '{ruta}': {r.stderr.decode(errors='ignore').strip()[:300]}")
    x = np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    if len(x) < n:
        x = np.tile(x, (n // len(x) + 1, 1))
    x = x[:n].copy()
    f = int(0.3 * SR)
    rampa = np.linspace(0, 1, f)[:, None]
    x[:f] *= rampa
    x[-f:] *= rampa[::-1]
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    return x * (0.12 / rms)


def buscar_musica(raiz: Path, ajuste: str) -> Path | None:
    """Devuelve la música elegida o None si hay que generarla."""
    if ajuste == "generada":
        return None
    if ajuste != "auto":
        ruta = raiz / ajuste
        if not ruta.exists():
            raise FileNotFoundError(f"No encuentro la música '{ajuste}'. Súbela a la carpeta audio/ o pon \"auto\".")
        return ruta
    carpeta = raiz / "audio"
    if not carpeta.is_dir():
        return None
    candidatos = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXT_MUSICA and p.is_file())
    preferidos = [p for p in candidatos if p.stem.lower() == "musica"]
    return (preferidos or candidatos or [None])[0]


def mezclar(duracion: float, eventos, ajustes: dict, raiz: Path) -> tuple[np.ndarray, str]:
    """Pista final estéreo (float, -1..1) y descripción de la música usada."""
    n = int(round(duracion * SR))
    externa = buscar_musica(raiz, ajustes["musica"])
    if externa:
        m = leer_musica_externa(externa, duracion)
        origen = f"archivo {externa.relative_to(raiz)}"
    else:
        m = musica(duracion, ajustes["bpm_aproximado"])
        origen = "generada por código"
    m = m * ajustes["volumen_musica"] / 0.35
    # La música baja durante el rebobinado.
    t = np.arange(n) / SR
    ev_reb = [e for e in eventos if e[1] == "rebobinado"]
    if ev_reb:
        t0, dur = ev_reb[0][0], ev_reb[0][4]["dur"]
        baja = np.clip((t - t0) / 0.1, 0, 1) * np.clip((t0 + dur - t) / 0.25, 0, 1)
        m = m * (1 - 0.75 * baja)[:, None]
    efectos = np.zeros((n, 2))
    for seg, nombre, gan, pan, params in eventos:
        s = EFECTOS[nombre](**params)
        g = gan * ajustes["volumen_efectos"]
        _poner(efectos, s * 0.55, int(round(seg * SR)), g * (1 - pan) , g * (1 + pan))
    mezcla = m + efectos
    pico = np.max(np.abs(mezcla))
    if pico > 0.89:
        mezcla = np.tanh(mezcla / pico * 1.2) / np.tanh(1.2) * 0.89
    return mezcla, origen


def guardar_wav(ruta: Path, x: np.ndarray) -> None:
    datos = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())
