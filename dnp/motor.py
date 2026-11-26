"""Motor común de todos los episodios, sea cual sea el formato o el tipo de personaje.

Un episodio es una función pura del "tiempo de acción" `a` (0..11 unidades):

* el gancho (segundo 0) y el final muestran exactamente el estado a = 11,
* el rebobinado recorre `a` hacia atrás de 11 a 0,
* la acción recorre `a` hacia delante de 0 a 11.

El último fotograma es idéntico al primero, así el bucle no se nota. Lo que se
mueve siempre (estrellas que parpadean) tiene un periodo igual al del bucle.

Cada episodio define `_decorado()` (fondo estático), `_preparar()`,
`_dibujar(img, a, fase_bucle)` y `eventos_episodio()`. El motor añade el
rebobinado, los textos (gancho, cierre y marca) y el audio común.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .config import Episodio
from .lienzo import BLANCO, ESCALA, FONDOS, ROJO, VERDE, capa, fondo, fuente, tenue, texto, usar_fondo
from .tiempo import rebote, suave, tramo

A_FIN = 11.0  # duración de la acción en unidades internas


class EpisodioMotor:
    POS_GANCHO = "arriba"  # "arriba" (texto sobre la escena) o "centro" (tarjeta en Y_TARJETA)
    Y_TARJETA = 960  # altura del centro de la tarjeta "Done > Perfect" (y del gancho centrado)

    def __init__(self, ep: Episodio):
        self.ep = ep
        t = ep["tiempos"]
        self.g = float(t["gancho_fin_s"])
        self.r = float(t["rebobinado_fin_s"])
        self.A = float(t["accion_fin_s"])
        self.D = ep.duracion
        self.k = (self.A - self.r) / A_FIN  # segundos reales por unidad de acción
        # El último fotograma (D - 1/fps) debe ser idéntico al primero.
        self.periodo_bucle = self.D - 1.0 / ep.fps
        self.ancho, self.alto = ep.tamano
        self.textos = ep["textos"]
        self.color_fondo = FONDOS[ep["fondo"]]
        usar_fondo(self.color_fondo)
        self.estrellas = []
        self._preparar()
        self._fondo = self._decorado()

    # --- a definir en cada episodio ----------------------------------------------
    def _preparar(self):
        pass

    def _decorado(self) -> Image.Image:
        raise NotImplementedError

    def _dibujar(self, img: Image.Image, a: float, fase_bucle: float):
        raise NotImplementedError

    def eventos_episodio(self) -> list:
        raise NotImplementedError

    # ------------------------------------------------------------------ tiempo
    def accion(self, t: float) -> float:
        if t < self.g:
            return A_FIN
        if t < self.r:
            u = tramo(t, self.g, self.r)
            return A_FIN * (1 - (0.5 * u + 0.5 * suave(u)))
        if t < self.A:
            return (t - self.r) / self.k
        return A_FIN

    def real(self, a: float) -> float:
        """Convierte un instante de la acción a segundos del vídeo (para el audio)."""
        return self.r + a * self.k

    # ================================================================ TEXTOS
    def _alfas(self, t: float):
        D, A = self.D, self.A
        gancho = 1.0 - tramo(t, self.g - 0.18, self.g)
        if t > A:
            gancho = max(gancho, tramo(t, D - 0.45, D - 0.12))
        cierre_in = tramo(t, A + 0.45, A + 0.6)
        cierre_out = 1 - tramo(t, D - 0.75, D - 0.45)
        cierre = cierre_in * cierre_out if t > A else 0.0
        return gancho, cierre

    def _tarjeta(self, img: Image.Image, trozos, alfa: float, escala: float = 1.0, tam_max: float = 130.0,
                 ancho_max: float = 860.0):
        """Texto grande sobre un recuadro redondeado, centrado en la línea de la pantalla partida."""
        if alfa <= 0:
            return
        s = ESCALA
        cx, cy = self.ancho / 2, self.Y_TARJETA
        cadena = "".join(c for c, _ in trozos)
        tam = min(tam_max, tam_max * ancho_max / (fuente(int(tam_max * s)).getlength(cadena) / s))
        ancho_txt = fuente(int(tam * s)).getlength(cadena) / s
        w, h = (ancho_txt + 110) * escala, tam * 1.75 * escala

        def plato(d, x0, y0):
            d.rounded_rectangle(
                (cx * s - w * s / 2 - x0, cy * s - h * s / 2 - y0, cx * s + w * s / 2 - x0, cy * s + h * s / 2 - y0),
                radius=int(40 * s * escala), fill=fondo() + (255,), outline=BLANCO + (255,), width=int(4 * s))

        caja = (int((cx - w / 2) * s) - 8, int((cy - h / 2) * s) - 8, int((cx + w / 2) * s) + 8, int((cy + h / 2) * s) + 8)
        capa(img, caja, plato, alfa)
        texto(img, trozos, (cx, cy - 4), tam * escala, alfa)

    def _cierre(self, img: Image.Image, t: float, alfa: float):
        if alfa <= 0:
            return
        escala = max(0.3, rebote(tramo(t, self.A + 0.45, self.A + 0.8), 2.0))
        partes = self.textos["cierre"].split(">")
        if len(partes) == 2:
            trozos = [(partes[0].rstrip() + " ", VERDE), (">", BLANCO), (" " + partes[1].lstrip(), ROJO)]
        else:
            trozos = [(self.textos["cierre"], BLANCO)]
        self._tarjeta(img, trozos, alfa, escala)

    def _gancho(self, img: Image.Image, alfa: float):
        if self.POS_GANCHO == "centro":
            self._tarjeta(img, [(self.textos["gancho"], BLANCO)], alfa, tam_max=74, ancho_max=820)
        else:
            texto(img, [(self.textos["gancho"], BLANCO)], (self.ancho / 2, 150), 66, alfa)

    def _rebobinado(self, arr: np.ndarray, t: float):
        """Efecto de cinta rebobinando: líneas desplazadas, bandas de ruido y franjas."""
        u = tramo(t, self.g, self.r)
        fuerza = min(1.0, tramo(t, self.g, self.g + 0.12)) * (1 - tramo(t, self.r - 0.18, self.r))
        if fuerza <= 0:
            return arr
        rnd = np.random.default_rng(int(t * 1000))
        alto = arr.shape[0]
        for _ in range(5):
            y0 = int(rnd.integers(0, alto - 60))
            hh = int(rnd.integers(8, 50))
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(rnd.integers(-40, 40) * fuerza), axis=1)
        banda = int((u * 3.3 % 1) * alto)
        hb = 34
        seg = arr[banda:banda + hb].astype(np.int16)
        ruido = rnd.integers(0, 200, size=seg.shape[:2], dtype=np.int16)[..., None]
        seg = np.clip(seg + (ruido * fuerza * (ruido > 170)).astype(np.int16), 0, 255)
        arr[banda:banda + hb] = seg.astype(np.uint8)
        arr[::4] = (arr[::4].astype(np.float32) * (1 - 0.22 * fuerza)
                    + np.array(fondo(), np.float32) * 0.22 * fuerza).astype(np.uint8)
        return arr

    def _icono_rebobinar(self, img: Image.Image, t: float):
        if not (self.g <= t < self.r):
            return
        alfa = tramo(t, self.g, self.g + 0.1) * (1 - tramo(t, self.r - 0.15, self.r))
        parpadeo = 0.75 + 0.25 * (1 if int(t * 6) % 2 else 0)
        cx, cy, s = self.ancho / 2, self.Y_TARJETA, ESCALA

        def dib(d, x0, y0):
            d.ellipse(((cx - 70) * s - x0, (cy - 70) * s - y0, (cx + 70) * s - x0, (cy + 70) * s - y0),
                      fill=fondo() + (255,), outline=BLANCO + (255,), width=4 * s)
            for dx in (-34, 6):
                d.polygon([((cx + dx + 34) * s - x0, (cy - 30) * s - y0), ((cx + dx) * s - x0, cy * s - y0),
                           ((cx + dx + 34) * s - x0, (cy + 30) * s - y0)], fill=BLANCO + (255,))

        capa(img, (int((cx - 76) * s), int((cy - 76) * s), int((cx + 76) * s), int((cy + 76) * s)), dib,
             alfa * parpadeo)

    # ============================================================== FOTOGRAMA
    def fotograma(self, t: float) -> Image.Image:
        usar_fondo(self.color_fondo)
        a = self.accion(t)
        fase_bucle = (t / self.periodo_bucle) % 1.0
        img = self._fondo.copy()
        self._dibujar(img, a, fase_bucle)
        gancho, cierre = self._alfas(t)
        self._gancho(img, gancho)
        self._cierre(img, t, cierre)
        self._icono_rebobinar(img, t)
        texto(img, [(self.textos["marca"], tenue(0.75))], (44, 62), 26, 1.0, ancla="lm")
        img = img.reduce(ESCALA)
        if self.g <= t < self.r:
            arr = self._rebobinado(np.array(img), t)
            img = Image.fromarray(arr)
        return img

    # ================================================================== AUDIO
    def eventos_audio(self):
        """Lista de (segundo, efecto, ganancia, paneo, parámetros)."""
        ev = [(self.g, "rebobinado", 0.8, 0.0, {"dur": self.r - self.g})]
        ev += self.eventos_episodio()
        ev.append((self.A + 0.45, "titulo", 0.8, 0.0, {}))
        return ev
