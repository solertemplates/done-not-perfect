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


def test_la_silla_debe_quedar_mejor(datos):
    datos["hacedor"]["inclinacion_final_grados"] = 9
    assert any("tiene que quedar mejor" in e for e in errores(datos))


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
    with pytest.raises(ErrorConfig) as e:
        cargar(p)
    assert "comillas tipográficas" in str(e.value)


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorConfig) as e:
        cargar(tmp_path / "no.json")
    assert "No existe el archivo" in str(e.value)


def test_no_modifica_entrada(datos):
    copia = copy.deepcopy(datos)
    validar(datos)
    assert datos == copia
