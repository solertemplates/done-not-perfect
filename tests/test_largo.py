"""Vídeo largo (1920x1080, 8:30): guion, línea de tiempo, fotogramas, audio, textos y publicación."""
from pathlib import Path

import numpy as np
import pytest

from dnp import errores, largo, largo_escenas as es, largo_textos
from dnp.config import ErrorConfig

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "tests" / "datos" / "largos" / "01_mismo_sueldo.txt"
TXT = EJEMPLO.read_text(encoding="utf-8")
UMBRAL_LUMA = 26


@pytest.fixture(scope="module")
def video():
    return largo.VideoLargo(largo.cargar(EJEMPLO))


def luma(img):
    a = np.asarray(img).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


# ----------------------------------------------------------------- guion
def test_lee_el_guion():
    L = largo.cargar(EJEMPLO)
    assert L.id == "largo01_mismo_sueldo"
    assert L.capitulos == ("savings", "debt", "habits", "decisions", "business")
    assert L.gancho == "Same salary. 10 years later."
    assert L.siguiente == "Same age. Different choices."


def test_comillas_curvas_y_capitulos_en_una_linea_y_en_espanol():
    t = ("gancho: “Same salary. 10 years later.”\ncapitulos: Ahorro, Deuda, Hábitos, Decisiones, Negocio\n"
         "mensaje: Not in a day.\nsiguiente: Next one.")
    L = largo.leer(t, Path("02_prueba.txt"))
    assert L.id == "largo02_prueba" and L.gancho == "Same salary. 10 years later."
    assert L.titulos == ("SAVINGS", "DEBT", "HABITS", "DECISIONS", "BUSINESS")


def test_errores_en_espanol():
    with pytest.raises(ErrorConfig) as e:
        largo.leer("gancho: x\ncapitulos: Savings, Debts, Habit\nmensage: y", Path("03_x.txt"))
    texto = str(e.value)
    assert "debe tener 5 líneas" in texto
    assert "¿Querías decir 'mensaje'?" in texto
    assert "Falta el campo 'siguiente:'" in texto


def test_capitulo_desconocido_sugiere():
    with pytest.raises(ErrorConfig) as e:
        largo.leer(TXT.replace("- Decisions", "- Decisons"), EJEMPLO)
    assert "¿Querías decir \"decisions\"?" in str(e.value)


# ----------------------------------------------------------- línea de tiempo
def test_duracion_y_capitulos():
    L = largo.cargar(EJEMPLO)
    assert largo.DURACION == 510 and largo.N_FOTOGRAMAS == 15300
    marcas = [(largo_textos.minutos(t), n) for t, n in L.marcas()]
    assert marcas == [("0:00", "Hook"), ("0:20", "Savings"), ("1:52", "Debt"), ("3:24", "Habits"),
                      ("4:56", "Decisions"), ("6:28", "Business"), ("8:00", "Ending")]
    assert L.inicio(4) + largo.CAPITULO == largo.FINAL


def test_miniganchos_cada_dos_minutos_y_mensaje_varias_veces():
    assert largo.MINIGANCHOS == [120, 240, 360, 480]
    assert len(largo.MENSAJE_EN) >= 3


def test_progreso_compuesto_lento_y_luego_rapido():
    vals = [es.compuesto(u / 10) for u in range(11)]
    assert vals[0] == 0 and vals[-1] == pytest.approx(1)
    assert all(a < b for a, b in zip(vals, vals[1:]))
    assert vals[5] < 0.25  # a mitad de camino aún va lento


def test_estilo_de_musica_distinto_en_cada_capitulo(video):
    estilos = [e for _, _, e in video.tramos_musica()]
    assert all(a != b for a, b in zip(estilos, estilos[1:]))
    assert len(set(estilos[1:-1])) == 5


# ---------------------------------------------------------------- fotogramas
@pytest.mark.parametrize("t", [0, 10, 17, 19.5, 21, 60, 121, 150, 241, 300, 361, 450, 481, 487, 495, 505])
def test_nunca_negro_y_tamano(video, t):
    img = video.fotograma(t)
    assert img.size == (1920, 1080)
    assert float(np.mean(luma(img) > UMBRAL_LUMA)) > 0.05


def test_el_ultimo_fotograma_es_el_primero(video):
    primero = np.asarray(video.fotograma(0)).astype(int)
    ultimo = np.asarray(video.fotograma((largo.N_FOTOGRAMAS - 1) / largo.FPS)).astype(int)
    assert np.mean(np.abs(primero - ultimo)) < 1.0


def test_personajes_siempre_blancos(video):
    arr = np.asarray(video.fotograma(60)).astype(int)
    blancos = (arr > 235).all(-1)
    assert blancos.mean() > 0.003  # los muñecos (y sus cabezas) siguen blancos


def test_miniatura(video):
    m = video.miniatura()
    assert m.size == (1280, 720)
    arr = np.asarray(m).astype(int)
    verde = ((arr[..., 1] > 200) & (arr[..., 0] < 120)).mean()
    rojo = ((arr[..., 0] > 200) & (arr[..., 1] < 80)).mean()
    assert verde > 0.002 and rojo > 0.002  # verde frente a rojo


# --------------------------------------------------------------------- audio
def test_la_musica_nunca_se_queda_en_silencio(video):
    from dnp.musica import SR

    pista = video.pista()
    assert pista.shape == (int(largo.DURACION * SR), 2)
    ventana = int(0.5 * SR)
    rms = np.sqrt(np.mean(pista[: len(pista) // ventana * ventana].reshape(-1, ventana, 2) ** 2, axis=(1, 2)))
    assert rms.min() > 0.01
    assert np.abs(pista).max() < 1


def test_eventos_de_sonido_dentro_del_video(video):
    from dnp import audio

    ev = video.eventos()
    assert all(0 <= e[0] < largo.DURACION and e[1] in audio.EFECTOS for e in ev)


# --------------------------------------------------------------------- textos
def test_textos_del_largo():
    t = largo_textos.generar(largo.cargar(EJEMPLO))
    assert "CHAPTERS\n0:00 Hook\n0:20 Savings\n1:52 Debt" in t
    assert "8:00 Ending" in t
    assert "piggy bank" in t
    assert "As an Amazon Associate I earn from qualifying purchases." in t
    assert "PRIMER COMENTARIO" in t
    assert "https://www.amazon.com/s?k=piggy+bank&tag=styleesencial-20" in t
    for palabra in ("guarantee", "get rich", "make money", "income", "millionaire"):
        assert palabra not in t.lower()


# ---------------------------------------------------------------- publicación
def test_un_largo_que_falla_no_bloquea_y_va_a_errores(tmp_path):
    malo = tmp_path / "02_malo.txt"
    malo.write_text("gancho: x", encoding="utf-8")

    def render(ruta, carpeta):
        raise AssertionError("no debería renderizar")

    destino = tmp_path / "videos"
    assert largo.procesar([malo], destino, tmp_path / "s", render=render) == 1
    assert "02_malo.txt" in (destino / "ERRORES_LARGOS.txt").read_text(encoding="utf-8")


def test_errores_de_shorts_y_largos_por_separado(tmp_path):
    videos, salida = tmp_path / "videos", tmp_path / "salida"
    videos.mkdir()
    salida.mkdir()
    (videos / "ERRORES.txt").write_text("error viejo de un short\n", encoding="utf-8")
    (salida / "ERRORES_LARGOS.txt").write_text("error del largo\n", encoding="utf-8")
    errores.fusionar(salida, videos)
    t = (videos / "ERRORES.txt").read_text(encoding="utf-8")
    assert "error viejo de un short" in t and "error del largo" in t
    # Los Shorts se arreglan: su apartado desaparece y el del largo se queda
    salida2 = tmp_path / "s2"
    salida2.mkdir()
    (salida2 / ".sin_errores").write_text("")
    errores.fusionar(salida2, videos)
    t = (videos / "ERRORES.txt").read_text(encoding="utf-8")
    assert "short" not in t and "error del largo" in t
    # Y luego el largo: ya no queda nada y el archivo se borra
    salida3 = tmp_path / "s3"
    salida3.mkdir()
    (salida3 / ".sin_errores_largos").write_text("")
    errores.fusionar(salida3, videos)
    assert not (videos / "ERRORES.txt").exists()
