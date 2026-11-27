# Atajo "Nuevo episodio" (app Atajos del iPhone)

Copias el guion corto (el texto `plantilla: ...`) y tocas el atajo. El atajo:

1. lee el portapapeles;
2. mira en `episodios/` cuál es el último número y usa el siguiente;
3. crea `episodios/NN_plantilla.txt` en GitHub (por ejemplo `07_kioscos.txt`);
4. te enseña el enlace al vídeo y al archivo de textos. El vídeo tarda unos 4 minutos en aparecer.

Apple no deja instalar atajos desde un archivo creado fuera de un iPhone o un Mac, así que se monta una sola vez a mano, siguiendo los pasos de abajo (unos 10 minutos).

## 1. Crear la llave de GitHub (una sola vez)

1. En github.com, toca tu foto y ve a **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. Rellena:
   - **Token name**: Atajo episodios.
   - **Expiration**: 1 año.
   - **Repository access**: *Only select repositories* → `done-not-perfect`.
   - **Permissions → Repository permissions → Contents**: **Read and write**.
3. Pulsa **Generate token** y copia el token (empieza por `github_pat_`). Solo se ve una vez.

## 2. Montar el atajo

Abre **Atajos**, toca **+** y ponle de nombre **Nuevo episodio**. Añade estas acciones en orden. El nombre entre comillas es lo que hay que escribir en el buscador de acciones.

**A. Datos fijos**

1. "Texto": pega el token. Toca la acción → **Establecer variable**… o añade "Establecer variable" con el nombre **Token**.
2. "Texto": `https://api.github.com/repos/solertemplates/done-not-perfect/contents/episodios` → "Establecer variable" **API**.

**B. Leer el guion**

3. "Obtener portapapeles" → "Establecer variable" **Guion**.
4. "Si": *Guion* **no contiene** `plantilla` →
   - "Mostrar alerta": *Copia primero el guion corto (con la línea plantilla:).*
   - "Detener este atajo".
   - (Fin del Si.)

**C. Siguiente número de episodio**

5. "Obtener contenido de URL": URL = variable **API**. Toca *Mostrar más*:
   - **Método**: GET.
   - **Cabeceras**: `Authorization` = `Bearer ` + variable **Token** (con un espacio después de Bearer), y `Accept` = `application/vnd.github+json`.
6. "Repetir con cada" elemento de *Contenido de la URL*:
   - "Obtener valor del diccionario": clave `name` de *Elemento repetido*.
   - "Coincidir texto": patrón `^(?:ep)?(\d+)` en *Valor del diccionario*.
   - "Obtener grupo en el índice": grupo **1** de *Coincidencias*.
   - "Añadir a variable": **Numeros**.
   - (Fin de Repetir.)
7. "Calcular estadísticas": **Máximo** de *Numeros*.
8. "Calcular": *Máximo* **+** `1` → "Establecer variable" **N**.
9. "Si": *N* **es menor que** `10` →
   - "Texto": `0` + *N* → "Establecer variable" **NN**.
   - **Si no**: "Texto": *N* → "Establecer variable" **NN**.
   - (Fin del Si.)

**D. Nombre del archivo**

10. "Coincidir texto": patrón `(?i)plantilla\s*:\s*([a-z]+)` en *Guion*.
11. "Obtener grupo en el índice": grupo **1**.
12. "Cambiar mayúsculas y minúsculas": **minúsculas** → "Establecer variable" **Plantilla**.
13. "Texto": *NN*`_`*Plantilla* → "Establecer variable" **Nombre**. Ejemplo: `07_kioscos`.

**E. Subir el .txt a GitHub**

14. "Codificar con Base64" *Guion*. Toca la acción y pon **Saltos de línea: Ninguno**.
15. "Obtener contenido de URL": URL = **API** + `/` + *Nombre* + `.txt`. En *Mostrar más*:
    - **Método**: PUT.
    - **Cabeceras**: las mismas dos del paso 5.
    - **Cuerpo de la solicitud**: **JSON**, con tres campos de tipo Texto:
      - `message` = `Nuevo episodio ` + *Nombre*;
      - `content` = *Texto codificado* (Base64);
      - `branch` = `main`.
16. "Obtener valor del diccionario": clave `content` de *Contenido de la URL*.
17. "Si": *Valor del diccionario* **no tiene ningún valor** →
    - "Mostrar alerta": *GitHub no aceptó el archivo. ¿Ha caducado el token?*
    - "Detener este atajo".
    - (Fin del Si.)

**F. Mostrar los enlaces**

18. "Texto":

    ```
    ✅ Episodio NN subido. El vídeo estará listo en unos 4 minutos.

    🎬 Vídeo:
    https://github.com/solertemplates/done-not-perfect/raw/main/videos/epNombre.mp4

    📝 Textos para Facebook y YouTube:
    https://github.com/solertemplates/done-not-perfect/blob/main/videos/epNombre_textos.txt
    ```

    Cambia `NN` por la variable *NN* y `Nombre` por la variable *Nombre*. Así queda `ep` seguido de, por ejemplo, `07_kioscos`.
19. "Mostrar resultado" con ese *Texto*. Los enlaces se pueden tocar.

Listo. Para tenerlo a mano: mantén pulsado el atajo → **Compartir → Añadir a pantalla de inicio**.

## Uso diario

1. Escribe el guion corto en Notas, por ejemplo:

   ```
   plantilla: kioscos
   barato: $1
   caro: $3 -> $5
   gancho: Same lemonade.
   cierre: Smart > Cheap
   ```

2. Selecciónalo todo y pulsa **Copiar**.
3. Toca **Nuevo episodio**.

Notas:
- Las comillas curvas del teclado del iPhone se aceptan.
- Si no pones `fondo:`, se elige uno distinto al de los últimos 6 episodios.
- Si el guion tiene un error, en lugar del vídeo aparece `videos/ERRORES.txt` explicando qué corregir.
- Si subes varios seguidos, se renderizan todos: los que se quedan en cola se recuperan en el siguiente render.
- Si pones `id:` en el guion, el vídeo se llamará así y los enlaces del atajo no coincidirán. Lo más fácil es no ponerlo.
