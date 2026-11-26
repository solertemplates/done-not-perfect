# Guía de guiones — "Done, not perfect"

Con esta guía puedes crear un episodio nuevo **solo con un archivo JSON**, sin programar. Solo tienes que subir el JSON a la carpeta `episodios/`, añadirlo al desplegable del workflow "Render episodio" y lanzarlo. El MP4 aparece en `videos/`.

Un episodio hecho con JSON se reconoce porque lleva un bloque `"guion"`. Los episodios 1, 2 y 3 están programados a mano y no lo llevan.

---

## 1. Reglas fijas de la serie

| Regla | Valor |
|---|---|
| Formato | vertical 1080x1920, 30 fps, de 15 a 20 s, sin voz |
| Personajes | **siempre blancos**, con cara de puntos y sonrisa simple. El Perfeccionista lleva gafas y lápiz en la oreja |
| Decorado | líneas blancas finas, estilo boceto, sobre un fondo muy oscuro |
| Carteles | como mucho 1 en la pared |
| Estructura | gancho (segundo 0) → rebobinado → acción → vuelve la imagen del gancho con el texto final |
| Bucle | el último fotograma es idéntico al primero (lo hace el motor solo) |

### Colores (solo como concepto, siempre pequeños y suaves)

| Color | Significa |
|---|---|
| verde | logro / ahorro |
| rojo | fallo / deuda |
| amarillo | riesgo |
| azul | IA |
| ámbar **#FFC873** | luz de las lámparas (luz de ambiente, **no** es el amarillo de riesgo) |

### Fondos permitidos (campo `"fondo"`)

| `"fondo"` | Código |
|---|---|
| `negro` | #0E0F12 |
| `azul_noche` | #0D1424 |
| `marron_cafe` | #1A130E |
| `gris_pizarra` | #15181C |
| `morado_oscuro` | #171222 |

---

## 2. Campos del JSON

Todos los campos son obligatorios salvo los marcados como *opcional*. Si algo está mal, la ejecución se para y explica el error en español, con la línea o el campo exacto y, si puede, una sugerencia.

| Campo | Tipo | Valores |
|---|---|---|
| `serie` | texto | siempre `"Done, not perfect"` |
| `episodio` | entero | 1-999 |
| `id` | texto | minúsculas, números y `_`. Es el nombre del MP4: `videos/<id>.mp4` |
| `titulo` | texto | hasta 60 caracteres |
| `fondo` | texto | uno de los 5 fondos |
| `video.ancho` / `video.alto` | entero | 1080 / 1920 (fijos) |
| `video.fps` | entero | 30 (fijo) |
| `video.duracion_s` | número | 15-20 |
| `tiempos.gancho_fin_s` | número | fin del gancho (normalmente 1) |
| `tiempos.rebobinado_fin_s` | número | fin del rebobinado (normalmente 3) |
| `tiempos.accion_fin_s` | número | fin de la acción. Después vuelve el gancho (mínimo 3 s hasta el final) |
| `textos.gancho` | texto | hasta 40 caracteres. Se ve en el gancho y vuelve al final |
| `textos.cierre` | texto | hasta 24 caracteres. Si lleva `>`, la parte de la izquierda sale verde y la de la derecha roja |
| `textos.marca` | texto | `"Done, not perfect"`, pequeño en una esquina |
| `guion` | objeto | ver abajo |
| `audio.musica` | texto | `"auto"` (tu `audio/musica.mp3` si existe), `"generada"` o `"audio/archivo.mp3"` |
| `audio.volumen_musica` / `audio.volumen_efectos` | número | 0-1 |
| `audio.bpm_aproximado` | número | 50-160 (se ajusta solo para que la música haga bucle) |

**Reglas de tiempo:** el gancho acaba antes que el rebobinado, el rebobinado antes que la acción, la acción dura al menos 8 s y desde el final de la acción hasta el final del vídeo hay al menos 3 s.

---

## 3. El bloque `"guion"`

| Campo | Valores |
|---|---|
| `formato` | `"pantalla_partida"` (arriba y abajo) |
| `escena` | `"cantera_noche"` |
| `gancho` *(opcional)* | `"centro"` (tarjeta sobre la línea central; por defecto) o `"arriba"` |
| `arriba` | panel de arriba |
| `abajo` | panel de abajo |

### Panel (`arriba` / `abajo`)

| Campo | Valores |
|---|---|
| `personaje` | `"hacedor"` o `"perfeccionista"` |
| `herramienta` *(opcional)* | `"mandarria"` o `"ninguna"` (por defecto) |
| `objeto` *(opcional)* | `{"tipo": "roca", "golpes_para_partir": 1-999, "brillo": "verde"}`. `brillo` es opcional: es el color de la grieta al partirse |
| `contador` *(opcional)* | `{"color_final": "verde"}`. Muestra un número grande arriba a la derecha que sube con cada golpe. `color_final` (opcional: verde, rojo, amarillo, azul o blanco) dibuja una barrita de ese color debajo cuando el panel termina |
| `acciones` | lista de acciones, en orden y sin solaparse |

### Acciones

Todas llevan `accion`, `desde_s` y `hasta_s`, en **segundos del vídeo**, entre `rebobinado_fin_s` y `accion_fin_s`.

| `accion` | Campos extra | Qué hace |
|---|---|---|
| `"golpear"` | `golpes` (1-999), `velocidad` (`"rapida"` o `"lenta"`) | Golpea el objeto con la herramienta. Cada golpe suma 1 al contador y agrieta la roca. **Rápida:** los primeros golpes se ven uno a uno y luego se aceleran (el contador "vuela"). **Lenta:** golpes regulares, uno detrás de otro. Al llegar a `golpes_para_partir`, la roca se parte (crac + ding) |
| `"rendirse"` | — | Suelta la herramienta, suspira, se da la vuelta y se aleja **de espaldas** y cabizbajo hacia el fondo |
| `"celebrar"` | — | Levanta la herramienta, da dos saltitos y acaba feliz con la herramienta al hombro |

Antes de su primera acción, el personaje espera preparado. Entre acciones mantiene la última postura.

### Escena `"cantera_noche"`

Cantera al aire libre de noche: cielo estrellado (algunas estrellas parpadean), luna en el panel de arriba, sierra lejana, bancales de piedra y suelo de grava.

### Objeto `"roca"`

Roca grande que se agrieta poco a poco con cada golpe: la grieta principal crece y salen grietas secundarias. Al llegar a `golpes_para_partir`, se parte en dos, salen esquirlas y, si tiene `brillo`, la grieta se ilumina de ese color. Las dos rocas de un episodio son la misma ("same rock").

### Herramienta `"mandarria"`

Mazo grande que se sujeta con las dos manos.

---

## 4. Sonidos (automáticos, generados por código)

No hace falta escribirlos en el JSON: salen de las acciones.

| Cuándo | Sonido |
|---|---|
| Rebobinado | cinta rebobinando |
| Cada golpe de mandarria | golpe seco contra la piedra (si los golpes van muy seguidos, no se amontonan) |
| Cada 20 golpes | crujido de grieta |
| La roca se parte | crac + ding |
| Rendirse | la herramienta cae, suspiro y pasos |
| Aparece el texto final | "pop" suave |
| Siempre | música suave en bucle (o tu `audio/musica.mp3`) |

---

## 5. Ejemplo completo (episodio 4, `episodios/04_roca.json`)

```json
{
  "serie": "Done, not perfect",
  "episodio": 4,
  "id": "ep04_la_roca",
  "titulo": "La roca",
  "fondo": "azul_noche",
  "video": { "ancho": 1080, "alto": 1920, "fps": 30, "duracion_s": 18 },
  "tiempos": { "gancho_fin_s": 1, "rebobinado_fin_s": 3, "accion_fin_s": 15 },
  "textos": {
    "gancho": "99 hits. Same rock.",
    "cierre": "Don't quit at 99",
    "marca": "Done, not perfect"
  },
  "guion": {
    "formato": "pantalla_partida",
    "escena": "cantera_noche",
    "gancho": "centro",
    "arriba": {
      "personaje": "hacedor",
      "herramienta": "mandarria",
      "objeto": { "tipo": "roca", "golpes_para_partir": 100, "brillo": "verde" },
      "contador": { "color_final": "verde" },
      "acciones": [
        { "accion": "golpear", "desde_s": 3.0, "hasta_s": 13.0, "golpes": 99, "velocidad": "rapida" },
        { "accion": "golpear", "desde_s": 13.4, "hasta_s": 14.0, "golpes": 1, "velocidad": "lenta" },
        { "accion": "celebrar", "desde_s": 14.15, "hasta_s": 15.0 }
      ]
    },
    "abajo": {
      "personaje": "perfeccionista",
      "herramienta": "mandarria",
      "objeto": { "tipo": "roca", "golpes_para_partir": 100 },
      "contador": { "color_final": "rojo" },
      "acciones": [
        { "accion": "golpear", "desde_s": 3.0, "hasta_s": 13.0, "golpes": 99, "velocidad": "rapida" },
        { "accion": "rendirse", "desde_s": 13.0, "hasta_s": 15.0 }
      ]
    }
  },
  "audio": { "musica": "auto", "volumen_musica": 0.35, "volumen_efectos": 0.9, "bpm_aproximado": 80 }
}
```

---

## 6. Publicar un episodio nuevo

1. Sube `episodios/<nombre>.json` (en github.com: **Add file → Create new file**).
2. Añade su ruta a las `options` del desplegable en `.github/workflows/render.yml` (o pídeselo a Claude).
3. Ve a Actions → **Render episodio** → elige el episodio → **Run workflow**.
4. En unos 2 minutos el MP4 estará en `https://github.com/solertemplates/done-not-perfect/raw/main/videos/<id>.mp4`.

## 7. Qué necesita código

Si un guion necesita una escena, un objeto, una herramienta o una acción que no aparece en esta guía, hay que añadirla a la biblioteca (`dnp/biblioteca.py` y `dnp/guion.py`). Después ya se puede usar desde cualquier JSON.
