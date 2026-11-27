# Guía de guiones — "Done, not perfect"

Todos los episodios se escriben en la carpeta `episodios/`: con un **guion corto `.txt`** de 5 a 8 líneas (plantillas, abajo) o con un **JSON completo** (secciones 1-8). No hay que programar ni tocar el workflow.

## Publicar

1. Sube o edita un archivo en `episodios/` desde github.com (**Add file → Create new file**, o el lápiz para editar) y guarda.
2. El workflow se lanza solo y renderiza **solo los episodios que has subido o cambiado**.
3. En unos 3 minutos el vídeo está en `videos/<id>.mp4` y la portada en `videos/<id>_miniatura.png`. Enlace directo: `https://github.com/solertemplates/done-not-perfect/raw/main/videos/<id>.mp4`.
4. Si el JSON tiene errores, en lugar del vídeo aparece **`videos/ERRORES.txt`**, que explica en español qué corregir. Cuando lo corriges y guardas, el vídeo se hace solo y `ERRORES.txt` desaparece.

## Guiones cortos con plantillas (.txt)

La forma más rápida: un `.txt` de 5 a 8 líneas en `episodios/`, por ejemplo `episodios/07_kioscos.txt`. El workflow lo convierte en el JSON completo y lo renderiza. El número y el `id` salen del nombre del archivo (`07_kioscos.txt` → `ep07_kioscos`). Las comillas curvas del iPhone, la flecha `→` y las mayúsculas se aceptan.

```
plantilla: kioscos
barato: $1
caro: $3 -> $5
gancho: Same lemonade.
cierre: Smart > Cheap
fondo: azul_noche
```

| Plantilla | Campos propios |
|---|---|
| `roca` | `golpes: 99`: los golpes del que se rinde. El Hacedor da uno más y la parte. |
| `kioscos` | `barato: $1`, `caro: $3` o `caro: $3 -> $5` (sube el precio) y `clientes: 1-8` |
| `construir` | `objeto: silla` o `objeto: escalera` |
| `martillos` | ninguno |
| `paneles` | `paneles: MOTIVATION, TALENT, EGO, DISCIPLINE`: de 3 a 6 franjas apiladas, una por palabra, cada una con un muñeco que golpea su roca. Solo el último la rompe (su palabra se pone verde); los demás se rinden en momentos distintos (su palabra se pone roja). |

Campos comunes (todos opcionales menos `plantilla`):
- `leccion`: frase fija arriba durante todo el vídeo, máximo 50 letras;
- `etiqueta_arriba` y `etiqueta_abajo`: palabra grande en negrita del Hacedor y del Perfeccionista, máximo 14 letras (por defecto DONE y PERFECT). Al final se pone verde la del que lo consigue y roja la del que no (no se usan en `paneles`);
- `gancho`: máximo 40 letras;
- `cierre`: máximo 24 letras; con `>` sale en verde > rojo;
- `fondo`: uno de los 11 fondos (ver «Fondos»). Si no lo pones, se elige solo uno distinto al de los últimos 6 episodios;
- `titulo`, `episodio` e `id`.

Cada plantilla pone sola un **marcador** bajo cada lado, con números que cambian durante el vídeo:

| Plantilla | Marcador |
|---|---|
| `roca` | HITS 99 · DONE 1 |
| `paneles` | HITS 37 · QUIT (y HITS 100 · DONE 1 el último) |
| `construir` | NAILS 9 · DONE 1 / SKETCHES 4 · DONE 0 |
| `kioscos` | SALES 5 · $12 |
| `martillos` | NAILS 17 · DONE 1 / MEASURES 6 · DONE 0 |

Lo que no pongas se queda como en el episodio original de esa plantilla. Si algo está mal, `videos/ERRORES.txt` lo explica. Un episodio con errores (o con el mismo nombre de vídeo que otro) no bloquea a los demás: los demás se publican igual.

---

## 1. Reglas fijas de la serie

| Regla | Valor |
|---|---|
| Formato | vertical 1080x1920, 30 fps, de 15 a 20 s, sin voz |
| Personajes | **siempre blancos**, con cara de puntos y sonrisa simple. El Perfeccionista lleva gafas y lápiz en la oreja (o, si es un objeto, gafas pequeñas) |
| Decorado | líneas blancas finas, estilo boceto, sobre un fondo de color vivo con degradado radial |
| Carteles | como mucho **1** en todo el episodio |
| Estructura | gancho (segundo 0) → rebobinado → acción → vuelve la imagen del gancho con el texto final |
| Bucle | el último fotograma es idéntico al primero (lo hace el motor solo) |

### Colores de concepto (pequeños, puros y saturados, con un halo oscuro para que destaquen sobre cualquier fondo)

| Color | Significa |
|---|---|
| verde | logro / ahorro |
| rojo | fallo / deuda |
| amarillo | riesgo |
| azul | IA |

### Paleta de AMBIENTE (no son colores de concepto)

Sirve para dar vida: luces, farolas, ventanas encendidas, toldos y letreros.

| Nombre | Código |
|---|---|
| `ambar` | #FFC873 (luz de lámparas y farolas) |
| `naranja` | #FF9F5A |
| `rosa_neon` | #FF6FB5 |
| `violeta` | #9B7BFF |

### Fondos (`"fondo"`)

Degradado **radial**: el centro es el color vivo del fondo y los bordes se oscurecen hasta el negro. Los personajes siguen siempre blancos. El código es el color del centro.

| Valor | Centro |
|---|---|
| `negro` | #341896 |
| `azul_noche` | #0030A8 |
| `marron_cafe` | #964000 |
| `gris_pizarra` | #005C7C |
| `morado_oscuro` | #5A0096 |
| `azul_electrico` | #0050FF |
| `violeta` | #8228FF |
| `naranja_atardecer` | #F05A00 |
| `rosa` | #C800A0 |
| `verde_esmeralda` | #008C5A |
| `rojo_vino` | #96002D |

### Variedad automática

Cada episodio, a partir de su `id`, cambia solo:
- las estrellas y la ciudad;
- el centro y el tamaño del degradado;
- el color del resplandor del horizonte;
- el color dominante de las ventanas encendidas;
- la música.

Dos vídeos nunca se ven ni suenan iguales.

### Música

Se genera por código y es distinta en cada episodio. Hay 8 estilos: alegre, epico_suave, lofi, piano, ukelele, electronico_suave, misterio y triunfal. El estilo sale del número del episodio, así que 8 episodios seguidos nunca lo repiten. La tonalidad, el tempo, los acordes, la melodía y la batería salen del `id`. Para forzar un estilo: `"audio": {..., "estilo": "lofi"}`.

### Textos para publicar

Junto a cada vídeo se crea `videos/<id>_textos.txt`, en inglés:
- **FACEBOOK:** texto con gancho, 2-3 emojis y 5 hashtags.
- **YOUTUBE:** título (máx. 60 letras, con #shorts), descripción de 2 líneas y 5 hashtags.

Al final del post de FACEBOOK y de la descripción de YOUTUBE va un bloque fijo de Amazon con un objeto que **se ve en el vídeo**:

```
Línea 1: frase puente que une el objeto con la lección
Línea 2: 🧰 Get this <producto> and <acción ligada a la lección> — link in the first comment 👇
Línea 3: As an Amazon Associate I earn from qualifying purchases.
```

Debajo hay un apartado **PRIMER COMENTARIO**, para pegarlo como primer comentario:

```
🛒 Shop now 👇
https://www.amazon.com/s?k=<producto>&tag=<id>
```

La tienda y el ID están en `config/amazon.txt`.

| Lo que sale en el vídeo | Producto |
|---|---|
| roca, paneles | sledgehammer o Atomic Habits (alternando) |
| silla | desk chair |
| escalera | step ladder |
| kioscos | lemonade dispenser |
| martillos | home tool kit |
| lámpara | desk lamp |
| portátil | laptop |

- **Sin repeticiones seguidas:** si el episodio anterior llevaba el mismo producto, se usa otro objeto que también salga en el vídeo (por ejemplo la lámpara).
- **Variedad:** la frase puente, la acción de la línea 2, el emoji y el texto del comentario tienen al menos 10 variantes cada uno. Dos episodios seguidos nunca repiten ninguna de ellas, así que no hay dos publicaciones iguales.
- **Sin promesas:** ni de éxito ni de dinero.

---

## 2. Estructura del JSON

| Campo | Valores |
|---|---|
| `serie` | siempre `"Done, not perfect"` |
| `episodio` | entero 1-999 |
| `id` | minúsculas, números y `_`. Es el nombre del vídeo: `videos/<id>.mp4` |
| `titulo` | hasta 60 caracteres |
| `fondo` | uno de los 11 fondos |
| `video` | `{"ancho": 1080, "alto": 1920, "fps": 30, "duracion_s": 15-20}` |
| `tiempos` | `{"gancho_fin_s", "rebobinado_fin_s", "accion_fin_s"}` (normalmente 1, 3 y 14). La acción dura al menos 8 s y quedan al menos 3 s hasta el final |
| `textos` | `{"gancho": "...", "cierre": "...", "marca": "Done, not perfect"}`. Si `cierre` lleva `>`, la izquierda sale verde y la derecha roja |
| `guion` | ver abajo |
| `audio` | `{"musica": "auto" \| "generada" \| "audio/x.mp3", "volumen_musica": 0-1, "volumen_efectos": 0-1, "estilo": opcional}` (`bpm_aproximado` ya no hace falta: se ignora) |

Todos los tiempos de las acciones van en **segundos del vídeo**, entre `rebobinado_fin_s` y `accion_fin_s`.

### El bloque `"guion"`

| Campo | Valores |
|---|---|
| `formato` | `"pantalla_partida"` (zonas `arriba` y `abajo`, 1080x960 cada una), `"escena_unica"` (una zona con los dos personajes juntos) o `"franjas"` (de 3 a 6 zonas apiladas en `"franjas": [ ... ]`, cada una con un muñeco más pequeño; la usa la plantilla `paneles`) |
| `gancho` *(opcional)* | `"arriba"` (texto sobre la escena) o `"centro"` (tarjeta en el centro) |
| `cierre_y` *(opcional)* | altura de la tarjeta final (por defecto 960). Úsala para no tapar a los personajes |
| `arriba` / `abajo` | en pantalla partida, una **zona** cada una |
| `escena`, `objetos`, `personajes` | en escena única, directamente dentro de `guion` |

Una **zona** tiene `"escena"` (obligatoria), `"objetos"` (lista, opcional), `"personajes"` (lista) y `"marcadores"` (lista, opcional). Los objetos se dibujan detrás de los personajes; en la lista de personajes, los últimos quedan delante.

**Marcadores** (`"marcadores"`): una línea con números que cambian bajo cada lado, por ejemplo:

```
{ "texto": "HITS {g} · DONE {d}", "x": 540, "y": 885,
  "valores": { "g": { "golpes": true, "de": "hacedor" },
               "d": { "cuenta": ["crac"], "de": "roca", "max": 1, "color": "verde" } } }
```

Cada `{nombre}` del texto sale de `valores`:
- `"golpes": true` cuenta los golpes de un personaje;
- `"cuenta": [sonidos]` cuenta los sonidos de un personaje u objeto (por ejemplo `martillo`, `hoja`, `regla`, `crac` o `ding`);
- `"ventas": true` y `"dinero": true` leen un `kiosco`;
- `"fijo": 0` es un número que no cambia.

Opciones: `"max"` pone un tope y `"color"` (verde, rojo, amarillo o azul) colorea el número cuando es mayor que 0. Por defecto `x`=540 e `y`=885 (bajo el suelo de la zona).

**Lección** (`"textos": {"leccion": "..."}`, máximo 50 letras): frase fija arriba durante todo el vídeo. La marca "Done, not perfect" baja a la esquina de abajo.

**Coordenadas:** en pantalla partida, cada zona mide 1080x960 y el suelo está en y=800. En escena única con `taller`, se usa la pantalla entera (la mesa está en y=1250). En escena única con `habitacion`, `cantera_noche` o `calle_mercado`, se usan las mismas coordenadas (suelo en y=800), que en pantalla quedan con el suelo abajo (y=1500) y el cielo llenando la parte de arriba.

---

## 3. Escenas y ambiente (`"escena"`)

| Campo | Valores |
|---|---|
| `tipo` | `"habitacion"` (suelo de tablas), `"taller"` (techo, mesa de taller con balda y suelo; solo con escena única), `"cantera_noche"` (cantera al aire libre, cielo estrellado, sierra, bancales y grava) o `"calle_mercado"` (calle de noche con farolas de luz ámbar, cielo estrellado, luna y ciudad con ventanas encendidas en colores de ambiente) |
| `farolas` *(opcional)* | en `calle_mercado`, lista de x de las farolas (por defecto `[150, 930]`) |
| `ventana` *(opcional)* | `{"x", "y", "ancho", "alto", "estrellas": 0-4 (densidad, 1 por defecto), "luna": {"x", "y", "radio"}, "semilla"}`: ventana con estrellitas detrás, algunas con parpadeo suave |
| `lampara` *(opcional)* | `{"x", "cable" (largo del cable), "luz": true, "techo" (y del techo), "luz_hasta_y" (dónde llega la luz; suelo por defecto), "ancho_luz", "semilla"}`: lámpara colgante con cono de luz **ámbar #FFC873**, suave y con degradado hacia abajo |
| `cartel` *(opcional)* | `{"dibujo": "silla_ideal" \| "escalera_ideal", "x", "y", "ancho", "alto"}`: el cartel "perfecto" de la pared (máximo 1 en todo el episodio) |
| `luna` *(opcional)* | en `cantera_noche` y `calle_mercado`, `true`/`false` (por defecto, solo en la zona de arriba) |
| `siluetas` *(opcional)* | `"sierra"`, `"ciudad"` (con ventanas encendidas), `"bancales"` o `"ninguna"`: siluetas lejanas. `siluetas_y` fija su altura |
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
| `kiosco` | `x`, `toldo`: `"naranja_blanco"` \| `"rosa_blanco"` \| `"violeta_blanco"`, `ancho` (300), `cola`: `"derecha"` \| `"izquierda"` | Puesto con mostrador y toldo a rayas de colores vivos. El vendedor se pone detrás (mismo `x`); los clientes hacen cola por el lado de `cola` |
| `limonada` | `kiosco`, `stock` (6), `reponer`: `[{"desde_s", "cantidad"}]` | Jarra y vasos sobre el mostrador. El stock baja con cada venta, sube al reponer y se queda a cero (jarra vacía) con `comprar_todo` |
| `cartel_precio` | `x`, `y`, `precio` ("$1"), `cambios`: `[{"desde_s", "precio"}]`, `tachado_s`, `borde` (color de ambiente) | Letrero con el precio. Cambia con un pequeño salto o se tacha en rojo |
| `monedas` | `x`, `y`, `cantidad` | Montón de monedas |
| `bolsa_dinero` | `x`, `y`, `kiosco`, `monedas` (inicial), `detalle`: `{"color": "verde" \| "rojo", "aparece_s"}` | Bolsa que crece con cada moneda que entra en su kiosco. Detalle verde (llena) o rojo (casi vacía) |
| `clientes` | `kiosco`, `cantidad` (1-8), `movimientos`: `[{"desde_s", "kiosco"}]` | Siluetas grises que hacen cola, se llevan un vaso cuando les venden y se van; con `movimientos` se cambian de kiosco |

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
| `mira` | `"izquierda"` (por defecto) o `"derecha"`: hacia dónde mira al empezar |
| `x`, `y` | posición (en los martillos, el punto donde apoyan) |
| `espejo` | martillos: `true` = miran hacia la izquierda |
| `tamano` | martillos: 0,5-2 (1,25 por defecto) |
| `parpadeos_s` | lista de segundos en los que parpadea |
| `paneo` | dónde suena: -1 izquierda, 1 derecha |
| `dx` | mueve al personaje en horizontal. Usa el mismo `dx` que los objetos con los que trabaja |
| `id` | por defecto, el tipo |
| `etiqueta` | palabra grande en negrita: `{"texto": "DONE", "color_final": "verde", "desde_s": 14}`. Se pone del color final en ese segundo. Opcionales: `x`, `y` y `tamano`. En pantalla partida va arriba a la izquierda de su zona |
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
| `vender` | `kiosco`, `veces` (1-20) | Detrás del mostrador: entrega un vaso al primero de la cola y recibe una moneda (que vuela a la bolsa del kiosco) |
| `comprar_todo` | `kiosco`, `pago` (5), `x` (opc.) | Paga (monedas a la bolsa de ese kiosco) y se lleva todo el stock en cajas |
| `cambiar_precio` | `cartel`, `precio` | Alarga la mano al cartel y cambia el precio |
| `contar_dinero` | — | Cuenta monedas pasándolas de una mano a otra |
| `burlarse` | `hacia`: `"izquierda"` \| `"derecha"` | Señala y se ríe (ojos cerrados, risa corta sin palabras) |
| `encogerse` | — | Hombros caídos, manos abiertas, cara de "qué le vamos a hacer" |
| `cruzar_brazos` | — | Se cruza de brazos |
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
| `vender` | monedas en cada venta y caja registradora al final |
| `comprar_todo` | monedas, caja registradora y cajas |
| `contar_dinero` | monedas una a una y caja registradora al terminar |
| `burlarse` | risa corta sin palabras |
| `cambiar_precio` | ding |
| Texto final | "pop" suave |
| Siempre | música en bucle, distinta en cada episodio (o tu `audio/musica.mp3`) |

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

### Ejemplo de negocio (calle del mercado, escena única)

En `tests/datos/mercado.json` hay un ejemplo completo y comprobado. Esto es lo esencial:

```text
"guion": {
  "formato": "escena_unica", "gancho": "arriba", "cierre_y": 1650,
  "escena": { "tipo": "calle_mercado", "farolas": [540] },
  "objetos": [
    { "id": "kh", "tipo": "kiosco", "x": 250, "toldo": "naranja_blanco", "cola": "derecha" },
    { "id": "kp", "tipo": "kiosco", "x": 830, "toldo": "violeta_blanco", "cola": "izquierda" },
    { "id": "limo_h", "tipo": "limonada", "kiosco": "kh", "stock": 4 },
    { "id": "precio_p", "tipo": "cartel_precio", "x": 830, "y": 170, "precio": "$5", "borde": "violeta", "tachado_s": 12.0 },
    { "id": "bolsa_h", "tipo": "bolsa_dinero", "kiosco": "kh", "x": 60, "detalle": { "color": "verde", "aparece_s": 11.6 } },
    { "id": "gente", "tipo": "clientes", "kiosco": "kp", "cantidad": 3, "movimientos": [ { "desde_s": 5.6, "kiosco": "kh" } ] }
  ],
  "personajes": [
    { "tipo": "perfeccionista", "x": 830, "acciones": [
      { "accion": "cruzar_brazos", "desde_s": 3.0, "hasta_s": 4.2 },
      { "accion": "burlarse", "desde_s": 4.2, "hasta_s": 5.4, "hacia": "izquierda" },
      { "accion": "encogerse", "desde_s": 8.0, "hasta_s": 9.5 } ] },
    { "tipo": "hacedor", "x": 250, "mira": "derecha", "acciones": [
      { "accion": "vender", "desde_s": 6.6, "hasta_s": 9.3, "kiosco": "kh", "veces": 3 },
      { "accion": "contar_dinero", "desde_s": 10.0, "hasta_s": 11.4 },
      { "accion": "comprar_todo", "desde_s": 12.7, "hasta_s": 13.9, "kiosco": "kp" } ] }
  ]
}
```

En escena única con `habitacion`, `cantera_noche` o `calle_mercado`, el suelo está en y=1500 de la pantalla y el cielo llena la parte de arriba (las coordenadas de la zona siguen siendo las de siempre: suelo en y=800).

Más ejemplos en `episodios/`:
- `ep01_la_silla.json`: pantalla partida, construir, sentarse, tambalearse, arreglar y planos.
- `ep02_la_escalera.json`: subir, bajar, refuerzo y señalar.
- `ep03_los_dos_martillos.json`: escena única con objetos vivos.

---

## 9. Qué necesita código

Una escena, un objeto, un personaje o una acción que no aparezca aquí hay que añadirla primero a la biblioteca (`dnp/escena.py`, `dnp/piezas.py`, `dnp/actores.py`). Después ya se puede usar desde cualquier JSON.
