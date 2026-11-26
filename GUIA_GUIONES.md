# Guía de guiones — "Done, not perfect"

Todos los episodios se escriben **solo con un archivo JSON** en la carpeta `episodios/`. No hay que programar ni tocar el workflow.

## Publicar

1. Sube o edita un archivo en `episodios/` desde github.com (**Add file → Create new file**, o el lápiz para editar) y guarda.
2. El workflow se lanza solo y renderiza **solo los episodios que has subido o cambiado**.
3. En unos 3 minutos el vídeo está en `videos/<id>.mp4` y la portada en `videos/<id>_miniatura.png`. Enlace directo: `https://github.com/solertemplates/done-not-perfect/raw/main/videos/<id>.mp4`.
4. Si el JSON tiene errores, en lugar del vídeo aparece **`videos/ERRORES.txt`**, que explica en español qué corregir. Cuando lo corriges y guardas, el vídeo se hace solo y `ERRORES.txt` desaparece.

---

## 1. Reglas fijas de la serie

| Regla | Valor |
|---|---|
| Formato | vertical 1080x1920, 30 fps, de 15 a 20 s, sin voz |
| Personajes | **siempre blancos**, con cara de puntos y sonrisa simple. El Perfeccionista lleva gafas y lápiz en la oreja (o, si es un objeto, gafas pequeñas) |
| Decorado | líneas blancas finas, estilo boceto, sobre un fondo muy oscuro |
| Carteles | como mucho **1** en todo el episodio |
| Estructura | gancho (segundo 0) → rebobinado → acción → vuelve la imagen del gancho con el texto final |
| Bucle | el último fotograma es idéntico al primero (lo hace el motor solo) |

### Colores (solo como concepto, siempre pequeños y suaves)

| Color | Significa |
|---|---|
| verde | logro / ahorro |
| rojo | fallo / deuda |
| amarillo | riesgo |
| azul | IA |
| ámbar **#FFC873** | luz de las lámparas (ambiente, **no** es el amarillo de riesgo) |

### Fondos (`"fondo"`)

| Valor | Código |
|---|---|
| `negro` | #0E0F12 |
| `azul_noche` | #0D1424 |
| `marron_cafe` | #1A130E |
| `gris_pizarra` | #15181C |
| `morado_oscuro` | #171222 |

---

## 2. Estructura del JSON

| Campo | Valores |
|---|---|
| `serie` | siempre `"Done, not perfect"` |
| `episodio` | entero 1-999 |
| `id` | minúsculas, números y `_`. Es el nombre del vídeo: `videos/<id>.mp4` |
| `titulo` | hasta 60 caracteres |
| `fondo` | uno de los 5 fondos |
| `video` | `{"ancho": 1080, "alto": 1920, "fps": 30, "duracion_s": 15-20}` |
| `tiempos` | `{"gancho_fin_s", "rebobinado_fin_s", "accion_fin_s"}` (normalmente 1, 3 y 14). La acción dura al menos 8 s y quedan al menos 3 s hasta el final |
| `textos` | `{"gancho": "...", "cierre": "...", "marca": "Done, not perfect"}`. Si `cierre` lleva `>`, la izquierda sale verde y la derecha roja |
| `guion` | ver abajo |
| `audio` | `{"musica": "auto" \| "generada" \| "audio/x.mp3", "volumen_musica": 0-1, "volumen_efectos": 0-1, "bpm_aproximado": 50-160}` |

Todos los tiempos de las acciones van en **segundos del vídeo**, entre `rebobinado_fin_s` y `accion_fin_s`.

### El bloque `"guion"`

| Campo | Valores |
|---|---|
| `formato` | `"pantalla_partida"` (zonas `arriba` y `abajo`, 1080x960 cada una) o `"escena_unica"` (una zona con los dos personajes juntos) |
| `gancho` *(opcional)* | `"arriba"` (texto sobre la escena) o `"centro"` (tarjeta en el centro) |
| `cierre_y` *(opcional)* | altura de la tarjeta final (por defecto 960). Úsala para no tapar a los personajes |
| `arriba` / `abajo` | en pantalla partida, una **zona** cada una |
| `escena`, `objetos`, `personajes` | en escena única, directamente dentro de `guion` |

Una **zona** tiene `"escena"` (obligatoria), `"objetos"` (lista, opcional) y `"personajes"` (lista). Los objetos se dibujan detrás de los personajes; en la lista de personajes, los últimos quedan delante.

**Coordenadas:** en pantalla partida, cada zona mide 1080x960 y el suelo está en y=800. En escena única con `taller`, se usa la pantalla entera (la mesa está en y=1250). En escena única con `habitacion` o `cantera_noche`, la zona de 960 se centra en la pantalla.

---

## 3. Escenas y ambiente (`"escena"`)

| Campo | Valores |
|---|---|
| `tipo` | `"habitacion"` (suelo de tablas), `"taller"` (techo, mesa de taller con balda y suelo; solo con escena única) o `"cantera_noche"` (cantera al aire libre, cielo estrellado, sierra, bancales y grava) |
| `ventana` *(opcional)* | `{"x", "y", "ancho", "alto", "estrellas": 0-4 (densidad, 1 por defecto), "luna": {"x", "y", "radio"}, "semilla"}`: ventana con estrellitas detrás, algunas con parpadeo suave |
| `lampara` *(opcional)* | `{"x", "cable" (largo del cable), "luz": true, "techo" (y del techo), "luz_hasta_y" (dónde llega la luz; suelo por defecto), "ancho_luz", "semilla"}`: lámpara colgante con cono de luz **ámbar #FFC873**, suave y con degradado hacia abajo |
| `cartel` *(opcional)* | `{"dibujo": "silla_ideal" \| "escalera_ideal", "x", "y", "ancho", "alto"}`: el cartel "perfecto" de la pared (máximo 1 en todo el episodio) |
| `luna` *(opcional)* | en `cantera_noche`, `true`/`false` (por defecto, solo en la zona de arriba) |
| `siluetas` *(opcional)* | `"sierra"`, `"ciudad"`, `"bancales"` o `"ninguna"`: siluetas lejanas muy tenues. `siluetas_y` fija su altura |
| `semilla` *(opcional)* | cambia los detalles al azar (trazos, grava, estrellas) |

> La escena del río no existe todavía. Si hace falta, se añade a la biblioteca y luego se usa desde el JSON.

---

## 4. Objetos (`"objetos"`)

Todos llevan `"tipo"` y, opcionalmente, `"id"` (por defecto, el mismo que el tipo) y `"dx"` (mueve el objeto en horizontal; útil en escena única para poner cada cosa en su lado). Las acciones se refieren a los objetos por su `id`. La silla, la escalera, la caja y el plano tienen su sitio fijo y se mueven con `dx`.

| Tipo | Campos | Qué es |
|---|---|---|
| `pila_madera` | `x`, `tablas` (6), `cae_desde_s`, `cae_hasta_s`, `sonido` (true) | Pila de tablas que cae del cielo al empezar. Las tablas se gastan al construir |
| `silla` | `inclinacion_inicial_grados` (7), `inclinacion_final_grados` (2,5), `se_tuerce_s` | Silla de 6 piezas con una pata corta. **Estados:** por partes → torcida → tambaleándose → calzada con una cuña verde |
| `escalera` | `inclinacion_inicial_grados`, `inclinacion_final_grados` | Escalera de 2 largueros y 5 peldaños. **Estados:** por partes → peldaño torcido → tambaleo → refuerzo verde |
| `caja` | `inclinacion_tapa_grados` (2,5) | Caja de madera sobre la mesa: tabla base con clavos tumbados y 5 piezas que se clavan |
| `tabla` | `x`, `y`, `ancho`, `clavos_tumbados` (lista de x), `clavo_x` | Tabla con clavos tumbados y un sitio para un clavo |
| `plano` | `boceto`: `"silla"` \| `"escalera"` | Hoja de planos en el suelo. Se dibuja, se mide con la **regla**, se borra y se arruga en **bolas de papel** (las bolas se quedan en el suelo) |
| `roca` | `golpes_para_partir`, `brillo` (color) | Roca que se agrieta poco a poco con cada golpe y se parte en dos (crac, esquirlas, grieta con brillo) |
| `contador` | `de` (id del personaje), `x`, `y`, `color_final` | Número grande que cuenta los golpes (1, 2, 3... 100). Al terminar, sale una barrita de color debajo |
| `marca_ok` | `x`, `y`, `aparece_s` | ✓ verde con "ding" |
| `aro_rojo` | `x`, `y`, `aparece_s`, `radio` | Círculo rojo discontinuo sobre lo que quedó a medias |

Herramientas y accesorios que salen solos con las acciones: **martillo**, **mandarria** (mazo grande), **lápiz**, **goma**, **regla**, **clavos** y **bolas de papel**.

---

## 5. Personajes (`"personajes"`)

| Tipo | Qué es |
|---|---|
| `hacedor` | muñeco de palo blanco: lo hace imperfecto, pero lo termina |
| `perfeccionista` | muñeco con gafas y lápiz en la oreja: nunca termina |
| `martillo_hacedor` | martillo blanco con cara, decidido |
| `martillo_perfeccionista` | martillo con gafas pequeñas y brazos finos (sujeta la regla y el clavo) |

| Campo | Valores |
|---|---|
| `herramienta` | `"martillo"`, `"mandarria"` o `"ninguna"` (muñecos) |
| `postura` | `"de_pie"` (por defecto) o `"sentado_suelo"` (para trabajar con un plano) |
| `x`, `y` | posición (en los martillos, el punto donde apoyan) |
| `espejo` | martillos: `true` = miran hacia la izquierda |
| `tamano` | martillos: 0,5-2 (1,25 por defecto) |
| `parpadeos_s` | lista de segundos en los que parpadea |
| `paneo` | dónde suena: -1 izquierda, 1 derecha |
| `dx` | mueve al personaje en horizontal. Usa el mismo `dx` que los objetos con los que trabaja |
| `id` | por defecto, el tipo |
| `acciones` | lista de acciones, en orden y sin solaparse |

Entre dos acciones, el personaje ya está en la postura con la que empieza la siguiente. Después de la última, se queda como acabó.

---

## 6. Acciones

Todas llevan `"accion"`, `"desde_s"` y `"hasta_s"`. Los campos marcados con *(opc.)* sirven para ajustes finos.

### Muñecos (`hacedor`, `perfeccionista`)

| Acción | Campos | Qué hace |
|---|---|---|
| `esperar` | — | De pie, quieto. Sentado en el suelo: mira cómo cae la madera y saca el lápiz |
| `preparar` | `x` | Mira cómo cae la madera y saca el martillo |
| `caminar` | `x`, `de_espaldas` (opc.) | Anda hasta `x`, conservando su cara y su herramienta |
| `construir` | `objeto` (silla/escalera), `madera` (pila), `primer_golpe_s`, `cada_s` (+ opc.: `subida_s`, `rebote_s`, `paso_s`, `x_min`, `x_max`, `x_final`, `mano_final`, `mirada`, `vuelo_s`) | **Construir por partes:** cada tabla vuela de la pila y se clava de un martillazo |
| `martillear` | `golpes_s` (lista), `arregla` (silla/escalera) o `punto` [x, y] (+ opc.: `x`, `agachado`, `preparar_s`, `levantarse_s`, `mano_final`, `mirada`) | Martillazos en un punto. Con `arregla`, pone la cuña o el refuerzo verde y endereza |
| `sorprenderse` | `x` | Cara de "¡O!" cuando algo sale torcido |
| `mirar` | `x` | Mira lo que ha hecho y asiente |
| `sentarse` | `objeto` (silla), `x_inicio` | Se sienta en la silla |
| `tambalearse` | `objeto` (silla/escalera) | Se tambalea con los brazos abiertos (crujido) |
| `subir` | `objeto` (escalera), `nivel` 0-5, `acercarse_s`, `x_inicio`, `deja_herramienta` | Sube peldaño a peldaño (pasos). Con un nivel más bajo, baja |
| `golpear` | `objeto` (roca), `golpes`, `velocidad`: `"rapida"` \| `"lenta"` | Golpes de mandarria. Cada golpe suma 1 al contador y agrieta la roca. Rápida: se acelera y el contador "vuela" |
| `dudar` | — | Levanta la herramienta (o la mano), duda... y la baja |
| `rendirse` | — | Suelta la herramienta, suspira y se aleja **de espaldas**, cabizbajo |
| `celebrar` | `estilo`: `"sentado"` (en la silla), `"señalar"` (con `punto`), `"herramienta"` o `"brazos"` | Celebra feliz |
| `suspirar` | — | Suspira (hombros abajo, soplido) |
| `dibujar` | `plano` | Sentado: dibuja el boceto en el plano |
| `medir` | `plano` | Sentado: mide con la regla y entorna los ojos |
| `borrar` | `plano` | Sentado: borra (borrones grises y una ✗ roja) |
| `arrugar` | `plano` | Sentado: arruga la hoja, la tira hacia atrás y vuelve a empezar |

### Objetos vivos (`martillo_hacedor`, `martillo_perfeccionista`)

| Acción | Campos | Qué hace |
|---|---|---|
| `preparar` | — | Se agacha un poco, listo para empezar |
| `construir` | `objeto` (caja), `partes`: 5 × `{"aparece_s", "tocs_s": [...]}`, `clavo_torcido` (opc.): `{"parte", "toc", "sorpresa_hasta_s", "endereza_s"}` | Toc toc toc: clava cada pieza. Con `clavo_torcido`, el clavo se dobla ("boing", sorpresa) y lo endereza de un toque |
| `caminar` | `x`, `y`, `angulo`, `espejo`, `salto` | Va dando un saltito hasta `x` |
| `celebrar` | — | Ojos felices "^^" y dos botes |
| `mirar` | — | Mira al otro personaje y vuelve a sonreír |
| `esperar` | — | Quieto, mirando el clavo |
| `colocar_clavo` | `objeto` (tabla) | Coge un clavo tumbado y lo pone a medias |
| `medir` | `objeto` (tabla) | Mide el clavo con la regla (en la tabla o en el aire) |
| `sacar_clavo` | `objeto` (tabla) | Saca el clavo y lo sostiene |
| `poner_clavo` | `objeto` (tabla) | Lo vuelve a poner a medias |
| `dudar` | — | Levanta el martillo, duda y lo baja sin golpear |
| `suspirar` | — | Se aplasta un poco, cara triste y soplido |

---

## 7. Sonidos (automáticos, generados por código)

No se escriben en el JSON: salen de las acciones y los objetos.

| Cuándo | Sonido |
|---|---|
| Rebobinado | cinta rebobinando |
| Cae la pila de madera | golpe de tablas |
| `construir` / `martillear` | martillazos (toc toc toc) |
| La silla se tuerce, `tambalearse`, `subir` | crujidos de madera y pasos |
| `clavo_torcido` | "boing" metálico |
| `medir` (martillo) | regla de plástico |
| `dibujar` / `borrar` / `arrugar` | hoja, lápiz, borrador, papel arrugado y bola que cae |
| `golpear` | mandarria contra la piedra (cada 20 golpes, crujido de grieta) |
| La roca se parte | crac + ding |
| `marca_ok` | ding |
| `suspirar` / `rendirse` | suspiro (y en `rendirse`, la herramienta cae y pasos) |
| Texto final | "pop" suave |
| Siempre | música suave en bucle (o tu `audio/musica.mp3`) |

---

## 8. Ejemplo completo (`episodios/04_roca.json`)

```json
{
  "serie": "Done, not perfect",
  "episodio": 4,
  "id": "ep04_la_roca",
  "titulo": "La roca",
  "fondo": "azul_noche",
  "video": { "ancho": 1080, "alto": 1920, "fps": 30, "duracion_s": 18 },
  "tiempos": { "gancho_fin_s": 1, "rebobinado_fin_s": 3, "accion_fin_s": 15 },
  "textos": { "gancho": "99 hits. Same rock.", "cierre": "Don't quit at 99", "marca": "Done, not perfect" },
  "guion": {
    "formato": "pantalla_partida",
    "gancho": "centro",
    "arriba": {
      "escena": { "tipo": "cantera_noche" },
      "objetos": [
        { "tipo": "roca", "golpes_para_partir": 100, "brillo": "verde" },
        { "tipo": "contador", "de": "hacedor", "color_final": "verde" }
      ],
      "personajes": [
        { "tipo": "hacedor", "herramienta": "mandarria", "paneo": -0.2, "acciones": [
          { "accion": "golpear", "desde_s": 3.0, "hasta_s": 13.0, "golpes": 99, "velocidad": "rapida", "objeto": "roca" },
          { "accion": "golpear", "desde_s": 13.4, "hasta_s": 14.0, "golpes": 1, "velocidad": "lenta", "objeto": "roca" },
          { "accion": "celebrar", "desde_s": 14.15, "hasta_s": 15.0 }
        ] }
      ]
    },
    "abajo": {
      "escena": { "tipo": "cantera_noche" },
      "objetos": [
        { "tipo": "roca", "golpes_para_partir": 100 },
        { "tipo": "contador", "de": "perfeccionista", "color_final": "rojo" }
      ],
      "personajes": [
        { "tipo": "perfeccionista", "herramienta": "mandarria", "paneo": 0.2, "acciones": [
          { "accion": "golpear", "desde_s": 3.0, "hasta_s": 13.0, "golpes": 99, "velocidad": "rapida", "objeto": "roca" },
          { "accion": "rendirse", "desde_s": 13.0, "hasta_s": 15.0 }
        ] }
      ]
    }
  },
  "audio": { "musica": "auto", "volumen_musica": 0.35, "volumen_efectos": 0.9, "bpm_aproximado": 80 }
}
```

Más ejemplos en `episodios/`:
- `ep01_la_silla.json`: pantalla partida, construir, sentarse, tambalearse, arreglar y planos.
- `ep02_la_escalera.json`: subir, bajar, refuerzo y señalar.
- `ep03_los_dos_martillos.json`: escena única con objetos vivos.

---

## 9. Qué necesita código

Una escena, un objeto, un personaje o una acción que no aparezca aquí hay que añadirla primero a la biblioteca (`dnp/escena.py`, `dnp/piezas.py`, `dnp/actores.py`). Después ya se puede usar desde cualquier JSON.
