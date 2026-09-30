# Auditoría — Latin Barber Cali (index.html)

> Método Compuertas · C5 Juicio (evaluación de lo ya construido)
> Fecha: 2026-09-27 · Archivos revisados: `index.html`, `css/style.css`, render en navegador

**Veredicto general: la base es mejor que el promedio de una landing genérica.** Hay un sistema tipográfico real (Unbounded + Plus Jakarta Sans), una paleta monocromática deliberada y firmas visuales propias (texto con stroke, banda inclinada, bordes de 2px). No es "otra landing con degradado morado". El problema no es que se vea a IA — es que le faltan piezas de producción (fotos reales, metadatos, manejo de errores) y tiene un par de inconsistencias que rompen el sistema que ya construyó.

No existe `referencias/`, `.impeccable.md` ni `design-system.css` en el proyecto — nunca pasó por C1/C2 del método. Esta auditoría documenta el sistema *implícito* que ya está en el CSS, para que el siguiente cambio lo respete en vez de reinventarlo.

---

## 1. Sistema de color — diagnóstico

```css
--ink:    #101012   /* base, texto, fondo oscuro */
--charcoal: #26262a  /* hover states, segundo oscuro */
--steel:  #6f6f76   /* texto secundario, iconos apagados */
--smoke:  #e9e8e5   /* fondo claro alterno */
--cloud:  #ffffff   /* fondo base, texto sobre oscuro */
```

**Lo que funciona:**
- Escala neutra de 5 pasos, bien ordenada de oscuro a claro. Contraste texto/fondo alto en todos los bloques de servicio (`tone-1` a `tone-4`) — pasa AA sin esfuerzo.
- Cero color "de marca genérico" (nada de azul SaaS ni morado IA). Es una decisión de diseño, no un accidente, y es la parte más fuerte del sitio.

**Lo que rompe el sistema:**
- **`#1a7a3c` (verde) y `#b3261e` (rojo) aparecen una sola vez cada uno**, en `.booking-status[data-state]` (`css/style.css:449-450`), para éxito/error del formulario. Son los **únicos dos colores saturados de todo el sitio**. Cuando aparecen, se sienten ajenos al sistema — el usuario nunca vio ese verde o ese rojo en ningún otro lado. No hay que quitarlos (son semántica de estado, no decoración), pero hay que **anclarlos a la paleta**: derívalos en el mismo espacio de color que `--ink` (ej. un verde y un rojo con la misma temperatura fría/neutra que el resto), no un verde-Bootstrap y un rojo-Material sueltos.
- **No hay ningún acento cromático para la marca.** Todo el sitio es escala de grises. Es válido como decisión (funciona para el tono editorial/barbershop), pero significa que el *único* lugar donde el ojo puede anclar "esto es Latin Barber" es la tipografía con stroke — no hay un segundo recurso si ese primero falla en un contexto (ej. compartido en redes, donde solo se ve una miniatura). Vale la pena decidir conscientemente: ¿de verdad cero acento, o falta un rojo/dorado de barbería en dosis mínima (ej. solo en el punto del rating o en el ícono de WhatsApp)?

## 2. Estructura — diagnóstico

**Jerarquía de contenido:** Hero → banda de servicios → servicios en detalle → reservar → galería → reseñas → visítanos → footer. El orden es correcto para conversión (la acción única — reservar — aparece dos veces: CTA del hero y sección dedicada). Esto cumple la pregunta 2 del método ("¿cuál es la única acción?") sin ambigüedad.

**Hallazgos:**

| # | Hallazgo | Dónde | Severidad |
|---|---|---|---|
| 1 | **Los íconos de servicio no corresponden al servicio.** "Barbería" usa un ícono de gota/pin de ubicación; "Peluquería" usa un círculo vacío sin ningún rasgo distintivo; "Sala de uñas" usa un ícono de **reloj**. Solo "Bar" (copa) acierta. Un usuario que escanea rápido no puede identificar la sección por el ícono — tiene que leer el texto, que es exactamente lo que el ícono debería evitarle. | `index.html:79,85,91,97` | Alta |
| 2 | **El selector de "Servicio" en el formulario depende 100% del backend en vivo** (`js/script.js` hace fetch a la API). Si el backend no responde, el `<option>` se queda en "Cargando..." para siempre, sin mensaje de error ni fallback estático con los 3 servicios ya conocidos (Barbería/Peluquería/Uñas). El usuario ve un formulario roto sin saber por qué. | `index.html:127-129` | Alta — bloquea la conversión si el backend cae |
| 3 | **Galería 100% de fotos de stock (Unsplash) que no son del local**, correctamente etiquetadas como "Fotos de referencia — pronto sumamos las nuestras". Honesto, pero es una dependencia externa (URLs de Unsplash pueden caerse o cambiar) y, mientras no haya fotos reales, la sección de "galería" no construye confianza del negocio real — más bien la resta si un cliente que ya conoce el local nota que ninguna foto coincide. | `index.html:167-190` | Alta — es la sección más floja del sitio |
| 4 | **Reseñas sin fuente verificable.** "Reseña de Google", "Reseña de Facebook", "Cliente frecuente" son etiquetas genéricas sin nombre, foto ni link al perfil real. Con reseñas reales (367 en Google) sobra material para citar con nombre y fecha, lo cual sube la credibilidad sin costo. | `index.html:204-217` | Media |
| 5 | **El acceso a la intranet del equipo está en el footer público** (`Acceso del equipo → intranet.html`), visible para cualquier visitante del sitio. No es una falla de seguridad per se (la intranet debe tener su propio login), pero expone la existencia y ruta del panel admin a cualquiera que mire el footer — innecesario. | `index.html:273` | Media |
| 6 | **Cero metadatos para compartir.** No hay `og:title`, `og:image`, `twitter:card` ni favicon. Para un negocio que vive de WhatsApp e Instagram, cuando alguien comparte el link el preview sale vacío o con datos por defecto del navegador — se pierde la primera impresión antes de que carguen la página. | `<head>`, `index.html:3-11` | Alta |
| 7 | **Sin datos estructurados de negocio local** (`LocalBusiness` JSON-LD: dirección, horario, teléfono, rating). Para una barbería que compite por aparecer en búsquedas locales de Cali, es la ganancia de SEO más barata que falta. | `<head>` | Media |
| 8 | **Horario poco claro**: "Abrimos todos los días — escríbenos para confirmar el horario de hoy." Funciona como copy honesto si de verdad el horario varía, pero si es fijo, un horario explícito (ej. "Lun–Sáb 9am–8pm") reduce fricción antes de reservar. | `index.html:242` | Baja |

## 3. Diseño / tipografía / composición — diagnóstico

**Lo que funciona (mantenlo, no lo toques sin razón):**
- Par tipográfico Unbounded (800/900, display geométrico) + Plus Jakarta Sans (texto) — evita el cliché Inter+Poppins. Coherente en todo el sitio, incluida la intranet.
- El truco de texto con stroke (`-webkit-text-stroke`) en la última línea del hero y en el intro — firma visual propia, con fallback correcto vía `@supports` para navegadores sin soporte.
- Bordes de 2px sólidos en `--ink` como recurso estructural repetido (grid de servicios, galería, mapa, tarjetas de stats en intranet) — es un lenguaje consistente, no decoración suelta.
- Botones pastilla (`border-radius: 999px`) uniformes en las 4 variantes (`btn-header`, `btn-cloud`, `btn-line`, `btn-ink`) con estados hover coherentes.
- Banda inclinada (`skewY(-1.4deg)`) entre hero y servicios — gesto editorial con personalidad, no genérico.
- Respeta `prefers-reduced-motion` en intro, hero y scroll — buena práctica de accesibilidad que muchos sitios "bonitos" olvidan.

**Lo que hay que revisar:**
- **La galería mezcla 3 formas (rectángulo, círculo, blob orgánico) más rotación aleatoria dentro de un grid de filas fijas (`grid-auto-rows: 190px`).** Es un recurso "scrapbook" válido, pero con 8 fotos de aspect ratios distintos forzadas a `object-fit: cover` dentro de un círculo o un blob, el recorte puede cortar mal la cara/sujeto de la foto — hay que revisar caso por caso una vez entren las fotos reales del local, no asumir que el `object-fit` compensa el blob.
- **El ícono de servicio (`.service-icon`, 34×34px) es el único elemento del sitio sin el 2px de borde estructural que domina el resto** — son trazos finos de 1.6px `stroke-width`. Funciona, pero conviene decidir si el grosor de línea de los íconos debería subir para que dialogue con el grosor de 2px que ya es la firma del sitio (bordes, header, service-grid).
- **Contraste de `hero-sub` (`#d3d3d6`) y `hero-rating` (`#a3a3aa`) depende de que el overlay del hero (`rgba(16,16,18,0.35)` en la base de la imagen) sea suficientemente oscuro.** Con fotos reales del local (no el interior genérico de Unsplash actual) hay que volver a verificar que el gradiente siga garantizando contraste legible sobre la imagen real, porque el punto más claro del gradiente (35% de opacidad) es justo donde vive el copy.

## 4. Prioridad de corrección (qué atacar primero)

1. **Fotos reales del local** — reemplaza la galería y el hero de Unsplash. Es el gap más grande entre "se ve bien" y "se ve confiable".
2. **Fallback del formulario de reserva** — si falla el fetch de servicios, mostrar las 3 opciones fijas en vez de "Cargando..." infinito. Es lo único que puede matar una conversión ya iniciada.
3. **Íconos de servicio correctos** (barbería/peluquería/uñas con símbolos que se lean sin texto).
4. **Meta tags de compartido + favicon + JSON-LD LocalBusiness** — bajo esfuerzo, alto retorno para un negocio que vive de WhatsApp/Instagram y búsqueda local.
5. **Anclar los colores de estado del formulario (verde/rojo) a la temperatura de la paleta**, para que no se sientan importados de otro sitio.
6. Reseñas con nombre real donde sea posible; horario explícito si es fijo; reconsiderar si el link a la intranet debe vivir en el footer público.

---

*No se tocó ningún archivo del proyecto — esta es solo la auditoría. Cuando decidan qué corregir, lo ideal es documentar la paleta y los principios que sí quieren conservar en un `design-system.css` / `.impeccable.md` antes de tocar código, para que futuras páginas del sitio hereden el mismo sistema en vez de reinventarlo.*
