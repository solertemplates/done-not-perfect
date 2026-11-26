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


def test_fondos_muy_oscuros_y_distintos_de_los_colores_de_concepto():
    from dnp.lienzo import AMARILLO, AZUL, FONDOS, ROJO, VERDE

    for nombre, (r, g, b) in FONDOS.items():
        assert 0.2126 * r + 0.7152 * g + 0.0722 * b < 25, nombre  # tan oscuro como el negro de la serie
        for concepto in (VERDE, ROJO, AMARILLO, AZUL):
            assert sum(abs(x - y) for x, y in zip((r, g, b), concepto)) > 250, nombre


def test_episodio_2_es_valido():
    from tests.conftest import EP2

    ep = cargar(EP2)
    assert ep["fondo"] == "marron_cafe"


def test_episodio_3_es_valido():
    from tests.conftest import EP3

    ep = cargar(EP3)
    assert ep["fondo"] == "gris_pizarra"
    assert ep["hacedor"] == {"inclinacion_tapa_grados": 2.5}


def test_hacedor_depende_del_episodio(datos):
    datos["episodio"] = 3
    e = " ".join(errores(datos))
    assert "Campo desconocido 'hacedor.inclinacion_inicial_grados'" in e
    assert "Falta el campo obligatorio 'hacedor.inclinacion_tapa_grados'." in e


def test_episodio_sin_animacion(datos):
    datos["episodio"] = 42
    assert errores(datos) == ["Todavía no hay animación para el episodio 42. Episodios disponibles: 1, 2, 3."]
