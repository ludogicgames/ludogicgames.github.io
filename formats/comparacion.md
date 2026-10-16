# Formato · Comparación y mejora (motor `engine/splitquiz.py`)

Reglas del usuario (16-17 oct 2026). Leer antes de producir cualquier reel de esta categoría.
Ejemplo de referencia aprobado en iteración: `specs/2026-W42-C01.json` ("Like this, or like this?").

## Categorías de vídeo (decisión 16-oct)
1. **Comparación y mejora**: misma formación en dos versiones (aburrida vs gamificada), pantalla partida, consejos aplicables. (este documento)
2. **Casos reales**: empresas que aplican gamificación (p. ej. Duolingo) con logos, casos y ejemplos. Antes de usar logos: revisión del Director Legal (uso de marcas).
3. **Mecánicas**: una mecánica completa explicada en modo tutorial.

## Reglas generales (todas las categorías)
- Aportar valor **aplicable**, no solo un dato ("el 97 % no termina" no basta). Cada vídeo deja algo que se pueda hacer mañana.
- **No decir quiénes somos** (ni "At Ludogic..."): el logo/la web ya se ven. Cerrar con la idea, no con la marca.
- **Final con movimiento**, nunca estático.
- **Muchas imágenes y animaciones.**
- Las **fuentes van en la descripción** (caption), no en la voz ni en pantalla: dan fiabilidad pero aburren. No cargar el guion de cifras.
- Idioma: **inglés**.
- Cuando se **añade algo en pantalla**: que haga **"POP"** muy vistoso (flash, onda, chispas, confeti, etiqueta "+ NOMBRE" que rebota) con sonido.
- **Pausas** entre elementos que se añaden uno a uno (≈1,5 s entre cada uno) y, al completar el conjunto, **1-2 s de resultado final** antes de seguir hablando.
- Nada que parezca plagio de una marca/app concreta (p. ej. nada de cuadrícula 2×2 roja/azul/amarilla/verde con triángulo-rombo-círculo-cuadrado tipo Kahoot): estilo propio navy + coral.

## Composición de pantalla
- Pantalla completa 1080×1920 **partida por la mitad**:
  - **Arriba: versión gamificada.** Interfaz moderna (no pixel art): presentador/a en estilo **vectorial** que lanza la pregunta, **tarjetas de respuesta apiladas** (navy, insignia coral A-D), **bomba arriba a la izquierda** cuya mecha baja por pregunta (cuanto antes respondes, más puntos), **vidas**, **marcador** que suma, **% del quiz** como progreso, racha.
  - **Abajo: versión tradicional.** Formulario realista **blanco y negro, tipografía tipo Arial** (Liberation Sans), pregunta con respuestas **A-D**, botón "Next >", **sin feedback de ningún tipo**.
  - **Mismas preguntas** en las dos.
- **Siempre se ve un ratón** navegando y respondiendo en cada mitad.
- **Feedback distinto al seleccionar y al responder** (solo en la gamificada):
  - Seleccionar → la opción se resalta (borde coral, check), las demás se apagan, clic suave.
  - Responder (Next) → feedback grande: CORRECT!, puntos que vuelan al marcador, confeti, racha / OOPS!, corazón roto, respuesta correcta marcada y explicación del porqué.
- Mientras se habla de una mitad, **la otra se congela en gris**; ahí aparece la **chica pixel art** (lo único pixel art del vídeo; boca sincronizada) presentando, con **subtítulos en Poppins**. Subtítulos no pegados al borde inferior, pero tampoco demasiado altos.
- Frases sobre las dos a la vez: ambas animadas, chica + subtítulo sobre la línea divisoria.
- Música solo con la mitad gamificada activa; la tradicional suena a oficina (zumbido, reloj).

## Estructura de guion que funcionó (C01)
1. Gancho: "Would you rather take a training like this?" (se ve la buena) — pausa 2 s — "Or like this?" (la mala) — pausa 2 s.
2. La buena: juegas, ves progreso, tienes feedback, motiva.
3. La mala: solo ven una obligación, dejan de prestar atención y baja la calidad del aprendizaje.
4. "Get one wrong, and you see why right away. That's the moment people actually learn." (sincronizado con el OOPS).
5. Las dos: la gamificación mejora el aprendizaje y la motivación y reduce el abandono.
6. Acción concreta: "You don't need a new course. Take the quiz you already have, and add three things." → **la mitad tradicional se transforma en directo**, una mecánica por frase con POP: timer, lives, instant feedback. Pausas entre cada una y 2 s de resultado final.
7. Gancho final: "So, how do you want your training to feel?"
8. CTA de **una sola palabra**: "Comment TRAINING, and we'll send you our free guide." (la guía debe existir antes de publicar; sin recoger emails ni datos).

## Producción
`python3 engine/splitquiz.py build specs/<ID>.json out/<ID> [--preview]`
Claves de spec: `scenes[].active` (top|bottom|both), `quiz[]` (q, opts, answer, pick, why), `feedback_sync` (OOPS en una palabra),
`upgrade.steps[]` (line, word, kind timer|lives|feedback, label), `end` (pre, word, sub), `top_offset`, `outro`.
