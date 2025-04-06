# bogabot (r)

Bogabot es un intento de crear un pequeño bot capaz de leer textos legales, vincular referencias, resumir, explicar y eventualmente buscar normas que apliquen a situaciones cotidianas.

Bogabot usa la ayuda de LLMs y scripts en python para cumplir su misión.

## Estado actual

Por ahora esto es solo un PoC (proof-of-concept) y la meta es ser comparable con un un abogado que aprobó con lo justo en la universidad de belgrano.

La principal tarea de bogabot es procesar el boletín oficial y compartir sus resumenes, referencias y análisis en https://hil.ar/bora 

En este repositorio hay una colección de scripts de baja calidad para extraer las normas del sitio oficial boletín oficial y crear diferentes tareas a ejecutar con LLMs.

El resultado de este procesamiento se comparte en HTML básico con extracción de información útil como designaciones en otros formatos (JSON y CSV).

## Futuro

Cuando finalice el PoC bogabot quedará en este repositorio como una vara a superar por futuros bogabots.

Sin embargo hay muchas tareas por realizar para terminar con el experimento; por costumbre de desarrollar en inglés las tareas futuras se encuentran en las lineas del archivo `TODO`.