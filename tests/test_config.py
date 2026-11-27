import copy
import json

import pytest

from dnp.config import ErrorConfig, cargar, validar
from tests.conftest import EP1


def errores(datos):
    with pytest.raises(ErrorConfig) as e:
        validar(datos)
    return e.value.errores


def test_episodio_1_es_valido():
    ep = cargar(EP1)
    assert ep.num_fotogramas == 540
    assert ep.tamano == (1080, 1920)


def test_falta_campo(datos):
    del datos["textos"]["cierre"]
    assert errores(datos) == ["Falta el campo obligatorio 'textos.cierre'."]


def test_tipo_incorrecto(datos):
    datos["video"]["fps"] = "30"
    (e,) = errores(datos)
    assert "'video.fps' debe ser número entero, pero es texto" in e


def test_booleano_no_es_numero(datos):
    datos["episodio"] = True
    assert "debe ser número entero" in errores(datos)[0]


def test_campo_desconocido_sugiere(datos):
    datos["audio"]["volumen_muisca"] = 0.3
    e = " ".join(errores(datos))
    assert "Campo desconocido 'audio.volumen_muisca'" in e
    assert "¿Querías decir 'volumen_musica'?" in e


def test_formato_fijo(datos):
    datos["video"]["ancho"] = 1920
    assert "debe valer exactamente 1080" in errores(datos)[0]


def test_duracion_fuera_de_rango(datos):
    datos["video"]["duracion_s"] = 25
    assert "el máximo es 20" in errores(datos)[0]


def test_varios_errores_a_la_vez(datos):
    datos["video"]["fps"] = 24
    datos["textos"]["gancho"] = ""
    del datos["titulo"]
    assert len(errores(datos)) == 3


def test_coherencia_de_tiempos(datos):
    datos["tiempos"]["rebobinado_fin_s"] = 2
    datos["tiempos"]["gancho_fin_s"] = 2
    assert any("debe ser mayor que" in e for e in errores(datos))


def test_musica_invalida(datos):
    datos["audio"]["musica"] = "/etc/passwd"
    assert any("'audio.musica'" in e for e in errores(datos))


def test_json_mal_escrito(tmp_path):
    p = tmp_path / "ep.json"
    p.write_text('{\n  "serie": "Done, not perfect",\n}\n', encoding="utf-8")
    with pytest.raises(ErrorConfig) as e:
        cargar(p)
    assert "línea 2" in str(e.value) or "línea 3" in str(e.value)
    assert "coma de más" in str(e.value)


def test_comillas_del_iphone(tmp_path, datos):
    p = tmp_path / "ep.json"
    p.write_text(json.dumps(datos).replace('"titulo"', "“titulo”"), encoding="utf-8")
    ep = cargar(p)  # las comillas curvas del iPhone se aceptan
    assert ep["titulo"] == datos["titulo"]


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorConfig) as e:
        cargar(tmp_path / "no.json")
    assert "No existe el archivo" in str(e.value)


def test_no_modifica_entrada(datos):
    copia = copy.deepcopy(datos)
    validar(datos)
    assert datos == copia


def test_fondo_valido_por_nombre(datos):
    for nombre in ("negro", "azul_noche", "marron_cafe", "gris_pizarra", "morado_oscuro"):
        datos["fondo"] = nombre
        validar(datos)


def test_fondo_no_permitido(datos):
    datos["fondo"] = "rojo"
    (e,) = errores(datos)
    assert "'fondo' vale \"rojo\", que no está permitido" in e
    assert '"marron_cafe"' in e


def test_fondo_sugerencia(datos):
    datos["fondo"] = "marron"
    assert "¿Querías decir \"marron_cafe\"?" in errores(datos)[0]


def test_falta_fondo(datos):
    del datos["fondo"]
    assert errores(datos) == ["Falta el campo obligatorio 'fondo'."]


def test_fondos_vivos_y_saturados():
    """El centro de cada fondo es un color puro y saturado (nada agrisado ni desteñido)."""
    from dnp.lienzo import FONDOS

    assert len(FONDOS) >= 11
    for nuevo in ("azul_electrico", "violeta", "naranja_atardecer", "rosa", "verde_esmeralda", "rojo_vino"):
        assert nuevo in FONDOS
    for nombre, c in FONDOS.items():
        alto, bajo = max(c), min(c)
        assert (alto - bajo) / alto >= 0.8, nombre  # saturación (HSV)
        assert alto >= 115, nombre  # con color, no casi negro
        assert 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] < 130, nombre  # los personajes blancos destacan


def test_colores_de_concepto_puros():
    from dnp.lienzo import AMARILLO, AZUL, ROJO, VERDE

    for c in (VERDE, ROJO, AMARILLO, AZUL):
        assert max(c) == 255 and (max(c) - min(c)) / 255 >= 0.75


def test_episodios_2_y_3_son_validos():
    from tests.conftest import EP2, EP3

    assert cargar(EP2)["fondo"] == "marron_cafe"
    assert cargar(EP3)["guion"]["formato"] == "escena_unica"


def test_falta_guion(datos):
    del datos["guion"]
    assert "Falta el campo obligatorio 'guion'." in errores(datos)
