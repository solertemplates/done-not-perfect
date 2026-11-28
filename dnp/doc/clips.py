"""Clips reales de vídeo: Pixabay (clave en PIXABAY_API_KEY) y, si hay clave, Pexels (PEXELS_API_KEY).

Para cada frase se busca con SUS palabras clave, se puntúa cada resultado y se descartan:
* los de aspecto barato (animaciones, 3D, fondos, pantallas verdes, textos...);
* la cámara lenta y los timelapses (siempre velocidad normal);
* los de menos de 1920x1080;
* los que enseñan una cara de cerca (detector de caras de OpenCV sobre fotogramas del clip);
* los que no encajan con la continuidad del personaje (Sarah y Mark: piel clara; se mira el color de la piel).
Nunca se repite un clip en el mismo vídeo. Las búsquedas y las descargas se guardan en caché.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

BARATO = {"animation", "animated", "cartoon", "3d", "render", "rendering", "motion graphics", "graphics",
          "background", "abstract", "loop", "green screen", "chroma", "chroma key", "text", "intro", "particles",
          "illustration", "logo", "template", "vector", "glitch", "fractal", "hologram", "neon", "screen saver"}
LENTO = {"slow motion", "slowmotion", "slow-motion", "slowmo", "time lapse", "timelapse", "time-lapse", "hyperlapse"}
CARAS = {"face", "portrait", "selfie", "headshot", "smile", "smiling", "eyes", "close up face", "facial", "model",
         "beauty", "makeup", "laughing", "talking"}
MUJER = {"woman", "women", "female", "girl", "lady", "her", "mother", "wife"}
HOMBRE = {"man", "men", "male", "guy", "businessman", "father", "husband", "boy"}
# Si no hay clip que encaje: plano neutro del lugar, sin manos.
NEUTROS = {"casa": ["cozy living room interior", "modern apartment interior", "home interior lamp evening",
                    "living room sofa lamp", "apartment window evening", "bedroom interior morning light"],
           "cocina": ["modern kitchen interior", "kitchen counter coffee", "coffee kitchen morning",
                      "kitchen table morning light", "coffee cup kitchen window"],
           "ciudad": ["city aerial", "city street evening", "skyline aerial", "city traffic night",
                      "downtown street people walking", "city buildings aerial drone"],
           "oficina": ["office interior empty", "desk office", "office building", "office desk computer evening",
                       "modern office interior"],
           "tienda": ["store shelves", "shopping mall interior", "supermarket aisle", "shop window display",
                      "retail store interior"]}
CONTINUIDAD = {"sarah": "woman beige sweater", "mark": "man blue shirt"}
# El plano neutro tiene que ser de verdad ese lugar (una de estas palabras) y no otra cosa.
ANCLA = {"casa": {"interior", "living", "apartment", "bedroom", "sofa", "couch", "lamp"},
         "cocina": {"kitchen"},
         "ciudad": {"city", "skyline", "street", "urban", "downtown", "aerial"},
         "oficina": {"office", "desk", "workplace"},
         "tienda": {"store", "shop", "mall", "supermarket", "shopping"}}
EXTERIOR = {"garden", "forest", "jungle", "nature", "tree", "plant", "beach", "mountain", "field", "park", "flower"}
# Lugares venidos a menos o de miedo: no encajan con la casa de Mark y Sarah (mismo nivel económico).
DESENTONA = {"abandoned", "ruin", "ruins", "destroyed", "dirty", "decay", "horror", "creepy", "grunge", "messy",
             "war", "broken", "derelict", "spooky",
             # La historia pasa en ciudades de EE. UU.: nada de letreros ni ciudades de otros países.
             "korea", "korean", "seoul", "japan", "japanese", "tokyo", "china", "chinese", "hong kong", "asia", "asian",
             "india", "thailand", "vietnam", "taiwan", "bangkok", "shanghai", "beijing", "singapore", "dubai",
             # Animales: "bill" también es el pico de un pájaro.
             "bird", "birds", "animal", "animals", "wildlife", "feeder"}
# Objetos que llaman la atención: si la frase no los pide, el clip no encaja (p. ej. "notebook" no es un portátil).
LLAMATIVOS = {"laptop", "computer", "keyboard", "smartphone", "phone", "tablet", "car", "dog", "cat", "baby"}


@dataclass
class Candidato:
    fuente: str
    id: int
    url: str  # vídeo a descargar (1920 de ancho si existe)
    ancho: int
    alto: int
    duracion: float
    etiquetas: set = field(default_factory=set)
    popularidad: float = 0.0
    pagina: str = ""

    @property
    def clave(self) -> str:
        return f"{self.fuente}-{self.id}"


GENERICOS = {"man", "woman", "men", "women", "person", "people", "hand", "hands", "girl", "boy", "guy", "lady", "young",
             "adult", "close", "up", "closeup", "view", "background", "footage", "video", "her", "his", "him"}
VACIAS = {"of", "the", "a", "an", "and", "with", "in", "on", "at", "to", "for", "from", "by"}


def _singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _palabras(texto: str) -> set:
    return {_singular(w) for w in re.split(r"[^a-z0-9]+", texto.lower()) if w}


class Buscador:
    def __init__(self, cache: Path, avisos: list | None = None):
        self.cache = cache / "clips"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.k_pixabay = os.environ.get("PIXABAY_API_KEY", "").strip()
        self.k_pexels = os.environ.get("PEXELS_API_KEY", "").strip()
        self.usados: set[str] = set()
        self.avisos = avisos if avisos is not None else []
        self._analisis: dict = {}
        if not self.k_pixabay and not self.k_pexels:
            raise RuntimeError("Falta la clave PIXABAY_API_KEY (secret del repositorio).")

    # ----------------------------------------------------------------- red
    def _get_json(self, url: str, cabeceras: dict | None = None) -> dict:
        k = hashlib.sha1(url.encode()).hexdigest()[:24]
        f = self.cache / f"api_{k}.json"
        if f.exists() and time.time() - f.stat().st_mtime < 7 * 86400:
            return json.loads(f.read_text())
        req = urllib.request.Request(url, headers={"User-Agent": "done-not-perfect/1.0", **(cabeceras or {})})
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    datos = json.loads(r.read().decode())
                f.write_text(json.dumps(datos))
                return datos
            except Exception:  # noqa: BLE001
                if intento == 2:
                    raise
                time.sleep(2 + 2 * intento)
        return {}

    def pixabay(self, consulta: str) -> list[Candidato]:
        if not self.k_pixabay:
            return []
        q = urllib.parse.urlencode({"key": self.k_pixabay, "q": consulta[:100], "per_page": 50, "safesearch": "true",
                                    "video_type": "film", "order": "popular"})
        datos = self._get_json(f"https://pixabay.com/api/videos/?{q}")
        out = []
        for h in datos.get("hits", []):
            variantes = [v for v in h.get("videos", {}).values() if v.get("url") and v.get("width", 0) >= 1920]
            if not variantes:
                continue
            v = min(variantes, key=lambda v: abs(v["width"] - 1920))  # 1920 si hay; si no, el 4K
            out.append(Candidato("pixabay", h["id"], v["url"], v["width"], v["height"], float(h.get("duration", 0)),
                                 {t.strip().lower() for t in h.get("tags", "").split(",") if t.strip()},
                                 float(h.get("downloads", 0)) + 20 * float(h.get("likes", 0)), h.get("pageURL", "")))
        return out

    def pexels(self, consulta: str) -> list[Candidato]:
        if not self.k_pexels:
            return []
        q = urllib.parse.urlencode({"query": consulta[:100], "per_page": 40, "orientation": "landscape", "size": "large"})
        datos = self._get_json(f"https://api.pexels.com/videos/search?{q}", {"Authorization": self.k_pexels})
        out = []
        for v in datos.get("videos", []):
            ficheros = [f for f in v.get("video_files", []) if (f.get("width") or 0) >= 1920 and f.get("link")]
            if not ficheros:
                continue
            f = min(ficheros, key=lambda f: abs(f["width"] - 1920))
            slug = re.sub(r"[-/]", " ", urllib.parse.urlparse(v.get("url", "")).path)
            out.append(Candidato("pexels", v["id"], f["link"], f["width"], f["height"], float(v.get("duration", 0)),
                                 _palabras(slug), 500.0, v.get("url", "")))
        return out

    def buscar(self, consulta: str) -> list[Candidato]:
        return self.pixabay(consulta) + self.pexels(consulta)

    def por_id(self, ident: int) -> list[Candidato]:
        if not self.k_pixabay:
            return []
        q = urllib.parse.urlencode({"key": self.k_pixabay, "id": ident})
        datos = self._get_json(f"https://pixabay.com/api/videos/?{q}")
        return [c for c in self._de_hits(datos)]

    def _de_hits(self, datos):
        out = []
        for h in datos.get("hits", []):
            variantes = [v for v in h.get("videos", {}).values() if v.get("url") and v.get("width", 0) >= 1920]
            if variantes:
                v = min(variantes, key=lambda v: abs(v["width"] - 1920))
                out.append(Candidato("pixabay", h["id"], v["url"], v["width"], v["height"], float(h.get("duration", 0)),
                                     {t.strip().lower() for t in h.get("tags", "").split(",")}, 1e9, h.get("pageURL", "")))
        return out

    # ------------------------------------------------------------- puntuar
    def puntuar(self, c: Candidato, consulta: str, quien: str, minimo: float, objeto=None) -> float | None:
        """Puntuación del clip para esta frase (None = descartado).

        `objeto`: lo que la voz nombra y TIENE que verse (lista de alternativas, p. ej. ["red mug", "mug"]).
        """
        etiquetas = " ".join(c.etiquetas)
        if c.duracion < minimo or c.alto < 1080 or c.ancho < 1920 or c.ancho / max(1, c.alto) < 1.6:
            return None
        if any(b in etiquetas for b in BARATO) or any(s in etiquetas for s in LENTO):
            return None
        if any(t in c.etiquetas for t in CARAS):
            return None
        if (_palabras(etiquetas) & {_singular(d) for d in DESENTONA}) - _palabras(consulta):  # salvo si se pide
            return None
        palabras_tags = _palabras(etiquetas)
        if objeto and not any(_palabras(o) - VACIAS <= palabras_tags for o in objeto):
            return None  # no se ve el objeto que dice la voz: mejor un plano neutro que otro objeto
        if quien == "sarah" and palabras_tags & HOMBRE and not palabras_tags & MUJER:
            return None
        if quien == "mark" and palabras_tags & MUJER and not palabras_tags & HOMBRE:
            return None
        todas = _palabras(consulta) - VACIAS
        clave = todas - {_singular(g) for g in GENERICOS}  # lo importante: objetos, acciones, lugares
        coinciden = len(clave & palabras_tags)
        hace_falta = 1 if len(clave) <= 1 else 2
        if coinciden < hace_falta:
            return None  # no muestra lo que dice la voz: mejor un plano neutro del lugar
        genericas = len((todas - clave) & palabras_tags)
        sobran = ({_singular(x) for x in LLAMATIVOS} & palabras_tags) - todas
        if sobran:
            return None  # sale algo que la voz no dice (un portátil, un perro...)
        extra = len(_palabras(CONTINUIDAD.get(quien, "")) & palabras_tags)
        return coinciden * 12 + genericas * 3 + extra * 4 + np.log1p(c.popularidad) + min(c.duracion, 20) * 0.1

    # ------------------------------------------------------------- descargar
    def descargar(self, c: Candidato) -> Path:
        destino = self.cache / f"{c.clave}.mp4"
        if destino.exists() and destino.stat().st_size > 10000:
            return destino
        tmp = destino.with_suffix(".tmp")
        req = urllib.request.Request(c.url, headers={"User-Agent": "done-not-perfect/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                bloque = r.read(1 << 20)
                if not bloque:
                    break
                f.write(bloque)
        tmp.rename(destino)
        return destino

    def analizar(self, ruta: Path, quien: str) -> tuple[bool, str]:
        """Mira 3 fotogramas: sin caras grandes y, si hay piel, que sea clara (continuidad)."""
        k = (str(ruta), quien)
        if k in self._analisis:
            return self._analisis[k]
        import cv2

        detectores = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in
                      ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
        info = sondear(ruta)
        ok, motivo = True, ""
        for f in (0.1, 0.3, 0.5, 0.7, 0.9):
            img = fotograma(ruta, info["duracion"] * f, 640, 360)
            if img is None:
                continue
            r, g, b = (img[..., i].astype(int) for i in range(3))
            if ((g > 140) & (g > r + 60) & (g > b + 50)).mean() > 0.01:
                ok, motivo = False, "pantalla verde (croma)"
                break
            gris = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            caras = [c for d in detectores for c in d.detectMultiScale(gris, 1.12, 5, minSize=(30, 30))]
            caras += [c for d in detectores[1:] for c in d.detectMultiScale(cv2.flip(gris, 1), 1.12, 5, minSize=(30, 30))]
            if len(caras) and max(w * h for _, _, w, h in caras) > 0.012 * 640 * 360:  # cara de cerca o a media distancia
                ok, motivo = False, "cara de cerca"
                break
            if quien in ("sarah", "mark", "pareja"):
                ycc = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb).reshape(-1, 3).astype(int)
                piel = ycc[(ycc[:, 1] > 138) & (ycc[:, 1] < 175) & (ycc[:, 2] > 85) & (ycc[:, 2] < 125)]
                if len(piel) > 0.03 * len(ycc) and np.median(piel[:, 0]) < 105:
                    ok, motivo = False, "piel distinta a la del personaje"
                    break
        if info["fps"] > 0 and info["fps"] < 23:
            ok, motivo = False, f"solo {info['fps']:.0f} fps"
        self._analisis[k] = (ok, motivo)
        return ok, motivo

    # ------------------------------------------------------------- elegir
    def elegir(self, frase, segundos: list[float]) -> list[tuple[Candidato, Path]]:
        """Un clip distinto (y no usado antes) para cada trozo de la frase."""
        candidatos: list[tuple[float, Candidato]] = []
        vistos = set()
        largo = max(segundos) + 1.0
        for pid in frase.pin:
            for c in self.por_id(pid):
                candidatos.append((1e9, c))
                vistos.add(c.clave)
        objeto = getattr(frase, "objeto", None) or None
        consultas = list(objeto or []) + [q for q in frase.clip if q not in (objeto or [])]  # primero el objeto exacto
        for consulta in consultas:
            for c in self.buscar(consulta):
                if c.clave in vistos:
                    continue
                vistos.add(c.clave)
                p = self.puntuar(c, consulta, frase.quien, largo, objeto)
                if p is not None:
                    candidatos.append((p, c))
        candidatos.sort(key=lambda x: -x[0])
        elegidos = []
        for p, c in candidatos:
            if len(elegidos) == len(segundos):
                break
            if c.clave in self.usados:
                continue
            try:
                ruta = self.descargar(c)
            except Exception as e:  # noqa: BLE001
                self.avisos.append(f"No se pudo descargar {c.pagina or c.clave}: {e}")
                continue
            ok, motivo = self.analizar(ruta, frase.quien)
            if not ok:
                continue
            self.usados.add(c.clave)
            elegidos.append((c, ruta))
        # Lo que falte: plano neutro del lugar (sin manos), nunca uno sin relación.
        for consulta in NEUTROS[frase.lugar]:
            if len(elegidos) == len(segundos):
                break
            for c in sorted(self.buscar(consulta), key=lambda c: -c.popularidad):
                if len(elegidos) == len(segundos):
                    break
                if c.clave in self.usados or self.puntuar(c, consulta, "nadie", largo) is None:
                    continue
                tags = _palabras(" ".join(c.etiquetas))
                if tags & {"hand", "person", "people", "woman", "man"}:
                    continue
                if not tags & ANCLA[frase.lugar] or (frase.lugar != "ciudad" and tags & EXTERIOR):
                    continue  # tiene que ser ese lugar, sin jardines ni paisajes
                try:
                    ruta = self.descargar(c)
                except Exception:  # noqa: BLE001
                    continue
                if self.analizar(ruta, "nadie")[0]:
                    self.usados.add(c.clave)
                    elegidos.append((c, ruta))
        if len(elegidos) < len(segundos):
            raise RuntimeError(f"No hay clips para \"{frase.texto['en'][:60]}\" (buscado: {', '.join(frase.clip)}).")
        return elegidos


def sondear(ruta: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(ruta)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    num, _, den = (s.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0
    return {"ancho": s.get("width", 0), "alto": s.get("height", 0), "fps": fps,
            "duracion": float(d.get("format", {}).get("duration", 0) or 0)}


def fotograma(ruta: Path, seg: float, ancho: int, alto: int):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{seg:.2f}", "-i", str(ruta), "-frames:v", "1", "-vf",
                        f"scale={ancho}:{alto}:force_original_aspect_ratio=increase,crop={ancho}:{alto}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if len(r.stdout) != ancho * alto * 3:
        return None
    return np.frombuffer(r.stdout, np.uint8).reshape(alto, ancho, 3)
