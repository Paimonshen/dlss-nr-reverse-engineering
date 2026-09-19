# Ingeniería inversa de DLSS NR: módulo AMD → recuperación de fuentes multiplataforma de GPU

> **En una línea**: un estudio exhaustivo de ingeniería inversa estática del módulo DLSS NR del lado AMD — la base para **recuperar un árbol de código fuente recompilable** y, a partir de él, una **única base de código multiplataforma de GPU** con backends portátil, acelerado por Intel, acelerado por AMD y de referencia NVIDIA. El estudio está completo y es honesto sobre dónde se atascó; **el trabajo de recuperación es la siguiente etapa**.

**Languages / 语言 / 言語 / 언어 / Idioma / Langue:**
[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [**Español**](README.es.md) · [Français](README.fr.md)

> Las traducciones las mantiene la comunidad. Si una traducción va por detrás, **el inglés es la versión de referencia**. Las correcciones son bienvenidas — véase [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🎯 Hacia dónde va esto (objetivos del proyecto)

Este repositorio comenzó como un análisis estático, pero el análisis siempre fue solo **un medio para un fin**. El objetivo hacia el que trabajamos ahora, en orden:

### Stage 1 — Recuperar las fuentes: descompilar el programa principal

Pasar de *entender bytes* a **un árbol de código fuente mantenible**: descompilar el programa principal y recuperar código fuente legible y recompilable. La especificación de parámetros de kernel ([`docs/04`](docs/04-Kernel-Parameter-Spec.md)), el formato del contenedor de pesos y el mecanismo de registro son el **material de referencia** que hace verificable una reconstrucción fiel — y por eso se produjeron primero.

> ⚠️ **Bloqueo conocido, dicho por adelantado.** Recuperar un árbol de código fuente *utilizable* requiere la **vinculación de despacho `71 block → kernel`**; sin ella, la capa de planificación reconstruida sigue siendo un esqueleto con un agujero en el medio. Esa vinculación es actualmente **inobtenible en las condiciones disponibles** (las cuatro vías están cerradas — véanse [Se busca ayuda](#-se-busca-ayuda-tres-huecos-concretos-que-no-pudimos-cerrar) y [`docs/06`](docs/06-Open-Gaps-and-Limits.md)). Por lo tanto, el esfuerzo de descompilación **topará con el mismo hueco**. El trabajo sigue mereciendo la pena — la mayor parte del árbol puede recuperarse —, pero la capa de despacho no puede cerrarse solo con descompilación.

### Stage 2 — Una compilación de instrucciones comunes que se ejecute en cualquier parte

Antes de optimizar, hacer que **se ejecute**. Producir una compilación que **no use ningún conjunto de instrucciones propietario de un fabricante**: una ruta de cómputo sencilla y portátil. Esto establece la corrección y da a cada backend posterior una **referencia conocida y válida con la que comparar**.

### Stage 3 — Compilaciones aceleradas por fabricante

Con la compilación portátil funcionando, añadir **aceleración específica de cada fabricante** como backends separados:

| Backend | Objetivo | Ruta de aceleración |
|---|---|---|
| **Aceleración Intel** | Intel Arc (Xe) | Xe Matrix Extensions (XMX) |
| **Aceleración AMD** | AMD RDNA / CDNA | HIP y núcleos matriciales |
| **Original de NVIDIA** | NVIDIA | la propia implementación NGX / DLSS del fabricante |

> ⚠️ **Restricción específica de la ruta NVIDIA.** Este repositorio **no contiene binarios con derechos de autor de NVIDIA** ([`LEGAL.md`](LEGAL.md) §8), y se ha confirmado que la copia disponible públicamente del componente de NVIDIA es una **capa de interfaz que no lleva ningún metadato de kernel analizable** (véanse [`EXTERNAL_BINARIES.md`](EXTERNAL_BINARIES.md) y [`docs/03`](docs/03-DLL-Structure-Analysis.md)). La ruta NVIDIA es, por tanto, utilizable **como referencia del comportamiento de la interfaz y para contrastar resultados** — **no** es una fuente de kernels descompilables. Cualquier trabajo del lado de NVIDIA aquí se queda en el nivel de interfaz / documentación.

### Stage 4 — Una sola base de código, todas las GPU

**Integrar los backends en un único árbol de código fuente** con un mecanismo de selección de backend, de modo que **una sola base de código apunte a todas las GPU compatibles**: la ruta portátil como respaldo universal y la aceleración de cada fabricante allí donde esté disponible.

> **En una sola frase:** *recuperar las fuentes → hacerlas funcionar de forma portátil → acelerarlas por fabricante → unificarlas en una sola base de código multi-GPU.*

> **Estado de estas etapas.** Las etapas 2–4 describen la **dirección prevista, no trabajo completado**. Este repositorio contiene actualmente **solo análisis y herramientas**: ningún árbol de código fuente descompilado y ninguna implementación de backend. Todo lo publicado aquí está en el **nivel de bytes estático**. Preferimos decir esto claramente antes que insinuar un avance que no podemos evidenciar.

## 🙏 Se busca ayuda: tres huecos concretos que no pudimos cerrar

Este **no es un estudio "terminado"**. Determinamos todo lo que se puede determinar estáticamente — **los 34 nombres de kernel, la disposición de los parámetros de los kernels, el formato del contenedor de pesos y la superficie de importación de 194 entradas están cerrados** —, pero **tres huecos** siguen siendo imposibles de cerrar en las condiciones de las que disponía el autor original. Pedimos ayuda de forma explícita.

### Hueco 1: la vinculación `71 block → kernel` (**el más crítico**)

**Qué necesitamos**: qué capa (`blockN.layerM`) despacha a cuál de los 34 kernels.

**Por qué no podemos obtenerlo** (las cuatro vías están cerradas, cada una con evidencia):
1. **El análisis estático de la DLL está en su límite** — el cuerpo de la función de despacho no tiene intersección con las funciones de lanzamiento de kernels.
2. **El código fuente del espacio de trabajo es un esqueleto** — existe un proyecto de reimplementación, pero los cuerpos de sus funciones de despacho son solo `return true;`, y **no es isomorfo** a esta DLL (solo 2 de los 34 nombres de kernel coinciden).
3. **El archivo de pesos está agotado** — buscamos con **140 patrones de bytes** en **todo el archivo, incluida la región de carga útil**: `shape` / `dtype` / tipo de operador / índice de `block` / nombre de `kernel` devolvieron **0 coincidencias**, y la contabilidad byte a byte de la región de índice muestra **bytes sin atribuir = 0** (no hay una segunda tabla ni una región oculta de metadatos).
4. **La observación en tiempo de ejecución no está disponible** — no tenemos hardware AMD.

**Si puedes aportar**: ① la definición de la red de origen (`.onnx` / `.safetensors` / script de exportación); ② el código fuente del lado del pass de origen; ③ o un volcado de la secuencia de despacho real de una ejecución sobre hardware AMD — abre una Issue. **Esto determina directamente si la hoja de ruta de portabilidad puede materializarse.**

### Hueco 2: la disposición interna de los campos de dos estructuras de parámetros

**`VarParams` (168 bytes, la estructura de parámetros de usuario de los 5 kernels `k_swin_var`)** y **`SwinParams` (40 bytes, `k_swin_1h_32_fp8`)** tienen una composición interna de campos sin resolver.

**Lo que sabemos**: los metadatos de la DLL solo declaran el **número total de bytes** del parámetro `by_value` (168 / 40); **no incluyen nombres de campo ni fronteras de campo**. Leímos estructuras con el mismo nombre en un árbol de código fuente de reimplementación (92 bytes suponiendo punteros de 64 bits), pero esas **no coinciden ni con 168 ni con 40** — por lo que las estructuras del código fuente **no pueden** usarse como la disposición del lado de la DLL.

**Si puedes aportar**: las definiciones de estructura del código fuente de origen, o las reglas de disposición de estructuras `by_value` de la cadena de herramientas de AMD (incluido el relleno implícito) — abre una Issue.

### Hueco 3: confirmar las capacidades de Intel Xe / XMX (una **lista de 51 puntos**)

Construimos una tabla de correspondencia de 34 kernels × operadores, pero **las columnas "soporte directo de XMX" y "ruta recomendada" de la tabla están marcadas como "requiere documentación externa" en las 34/34 filas — deliberadamente no dimos ninguna conclusión sobre capacidades**, porque no tenemos ni cadena de herramientas de Intel ni hardware Xe para verificarlo.

**Si conoces Intel Arc / oneAPI / Level Zero / SPIR-V**, ayúdanos a confirmar los puntos concretos (máxima prioridad: el soporte de primitivas XMX y los modos de precisión para multiplicación de matrices/convolución; si el orden de reducción de split-K está restringido por la especificación; las primitivas de ventana/desplazamiento de Swin; y la frontera de viabilidad de la ruta genérica de SPIR-V). La lista está en [docs/05-Intel可行性评估.md](docs/05-Intel可行性评估.md), capítulo 8.

> **Metodología del proyecto**: todo aquello de lo que no estamos seguros se marca como "requiere documentación externa" y **nunca especulamos**. Esos espacios en blanco de la tabla son **deliberados, no omisiones**.

---

## Qué hizo este proyecto

Un análisis estático completo de `dlssnr_amd_pass1.dll` del lado AMD (un módulo proxy `version.dll` que contiene código de dispositivo HIP `amdgcn`), para responder a:

> **¿Se puede recompilar/portar DLSS NR de AMD HIP a Intel Arc (Xe / XMX)?**

### Resultados principales (todos reproducibles)

| Resultado | Contenido | Documento |
|---|---|---|
| **Forma del módulo** | 12 secciones; 17 exportaciones, **todas nombres de API de `version.dll`** (cada una un stub de salto `FF 25` de 16 bytes); superficie de importación de **194 entradas / 10 DLL**, de las cuales `amdhip64_7.dll` aporta **29** API de HIP | `docs/03` |
| **Código de dispositivo** | `.hip_fat` es un clang offload bundle: **9 bundles = 1 marcador de posición de host + 8 destinos de dispositivo**, todos `amdgcn-amd-amdhsa`; **34 kernels** por destino | `docs/03` |
| **Especificación de parámetros de kernel** | Para los 34 kernels: `kernarg_segment_size`, tamaños `by_value`, tablas `.args` completas, campos de recursos; **3 kernels de excepción** (`k_flag_wait`=16 / `k_align_probe`=8 / `k_flag_set`=12) | `docs/04` |
| **Emparejamiento de registro 34/34** | Dos tablas de punteros a función con **paso de 8 bytes** + **34 llamadas de registro emparejadas con las ranuras de la tabla 34/34** ⇒ "nombre de kernel ↔ envoltorio ↔ ranura" cerrado estáticamente | `docs/03` |
| **Contenedor de pesos descifrado** | `8B magic "DLSSNRW1"` + recuento de entradas `uint32` (153) + desplazamiento de fin de índice `uint32` (0x1629) + 153 descriptores de longitud variable + carga útil contigua (147,683,778 B); **tres identidades cierran a 0** | `docs/05` |
| **Viabilidad en Intel** | Clases de kernel **A=7 / B=20 / C=7**; adaptación de recursos (`group_segment_fixed_size` máximo **64,640 B**, **896 B** por debajo del límite de 64 KiB); el lado host necesita **29/194 = 14.9%** reemplazado; **hoja de ruta S0–S7 con 23 hitos** | `docs/05` |
| **Herramientas de análisis** | Tres herramientas genéricas de solo lectura: analizador de PE, extractor de metadatos msgpack de AMDGPU, escáner de bytes | `tools/` |
| **Metodología de colaboración** | Flujo de trabajo multiagente, puertas de calidad y cadena de aceptación, **24 reglas derivadas de incidentes reales** | `team-methodology/` |

### Conclusiones firmes (incluidas nuestras propias correcciones)

**Conservamos el rastro de correcciones**, incluidas las reversiones de nuestras propias conclusiones anteriores:

- ✅ **El emparejamiento de registro 34/34 es evidencia directa de bytes** (en su momento se escribió como "inferencia por eliminación").
- ✅ **Las mediciones de pesos refutan constantes del código fuente**: la estructura real de capas es **1×47 / 4×15 (23–29, 40–47) / 5×9 (30–38)**, lo que contradice el "cuello de botella uniformemente de 4 capas" del código fuente (**bloques inconsistentes: 10 = 30–39**); en caso de conflicto, **gana el archivo de datos**.
- ✅ **El delta de `descsz` se corrigió de 1,410 a 938** (un error aritmético), y hay **6 valores distintos** tras deduplicar.
- ✅ **La restricción "no hay código fuente de origen" quedó revocada**: el espacio de trabajo **sí** contiene un árbol de código fuente del lado del pass (aunque no isomorfo a la DLL); el "no existe" anterior fue un **falso negativo** causado por un alcance de búsqueda demasiado estrecho.
- ✅ **El límite superior del enum `71 block` queda indeterminado**: ese número aparece solo en transcripciones de documentación; no hay ningún inmediato correspondiente en la DLL.

> Una regla firme de nuestra metodología: **toda afirmación del tipo "X no existe" debe dar rango + patrón + número de coincidencias.** Por eso verás muchos registros reproducibles de "0 coincidencias" en la documentación — es deliberado.

---

## Estructura del repositorio

```
.
├── README.md                  Este archivo (inglés, versión de referencia)
├── README.zh-CN.md            简体中文
├── README.ja.md               日本語
├── README.ko.md               한국어
├── README.es.md               Español
├── README.fr.md               Français
├── LEGAL.md                   Aviso legal (naturaleza del proyecto, derechos, retirada)
├── EXTERNAL_BINARIES.md       Binarios de terceros (origen / tamaño / SHA256 / licencia / uso)
├── LICENSE                    MIT (obra original) + exclusión explícita de binarios de terceros
├── CONTRIBUTING.md            Guía de contribución (requisitos de evidencia)
├── .gitattributes             Configuración de Git LFS
├── .gitignore
├── docs/
│   ├── 01-项目背景.md            Objetivo del proyecto, objeto de análisis, tres restricciones del entorno
│   ├── 02-分析方法论.md          Cadena de métodos y disciplina de análisis
│   ├── 03-DLL结构分析.md         Forma del módulo, código de dispositivo, las dos tablas de punteros, registro
│   ├── 04-内核参数规格.md        Tablas completas de parámetros y recursos de los 34 kernels
│   ├── 05-Intel可行性评估.md     Clasificación / recursos / operadores / reemplazo en host / pesos / hoja de ruta / lista de comprobación
│   └── 06-未解缺口与限制.md      Límites honestos: qué no pudimos producir y por qué
├── tools/
│   ├── pe_parser.py         Análisis de PE32/PE32+ (tratamiento manual de .reloc y .pdata)
│   ├── msgpack_extract.py   Extracción de metadatos de kernel de AMDGPU
│   ├── byte_scanner.py      Escaneo genérico de patrones de bytes / histograma / entropía / cadenas
│   └── README.md
├── team-methodology/
│   ├── 01-多智能体协作流程.md
│   ├── 02-质量门禁与验收链.md
│   ├── 03-已确立的定规.md     24 reglas, cada una proveniente de un error real
│   └── 04-禁用措辞检查的校准.md
└── binaries/                 Binarios de terceros (Git LFS)
    ├── dlssnr_amd_pass1.dll
    ├── dlssnr_amd_pass2.dll
    ├── dlssnr_amd_pass3.dll
    ├── dlssnr_on_amd_weights.bin
    └── OptiScaler/
        └── OptiScaler.dll
```

> Nota: las tres DLL `pass1/2/3` son **idénticas byte a byte** (mismo SHA256). Esa es la estructura real del paquete de distribución, no tres etapas de procesamiento.

> **Nota sobre el idioma de la documentación**: los seis documentos de análisis de `docs/` y los cuatro documentos de metodología de `team-methodology/` están escritos actualmente en **chino**. Las traducciones al inglés son bienvenidas — véase [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Inicio rápido

```bash
git clone https://github.com/Paimonshen/dlss-nr-reverse-engineering.git
cd dlss-nr-reverse-engineering

# Binaries are tracked by Git LFS; pull real content after cloning (~186 MB)
git lfs install
git lfs pull
```

### Dependencias

```bash
pip install pefile msgpack    # Python 3.11+
```

### Reproducir los resultados principales

```bash
# 1) Module shape: 12 sections / 17 version.dll exports / 194 imports (10 DLLs)
python tools/pe_parser.py info binaries/dlssnr_amd_pass1.dll --limit 0

# 2) Relocations: 19 blocks, 2044 entries (DIR64 2040 + ABSOLUTE 4)
python tools/pe_parser.py reloc binaries/dlssnr_amd_pass1.dll

# 3) Exception table: 1167 entries
python tools/pe_parser.py pdata binaries/dlssnr_amd_pass1.dll --pdata-limit 0

# 4) 8 device targets x 34 kernels, with kernarg size and by_value args
python tools/msgpack_extract.py binaries/dlssnr_amd_pass1.dll --json out/kernels.json

# 5) Weight container magic (1 hit) and payload byte distribution (entropy 5.902444 bits/byte)
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --hex "44 4C 53 53 4E 52 57 31"
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --byte-histogram --range 0x1629:
```

Las tres herramientas son de **solo lectura** (no escriben nada salvo en rutas explícitas `--out` / `--json` / `--hex-out`). Véase [tools/README.md](tools/README.md).

---

## Tres restricciones del entorno (atención)

Toda conclusión está acotada por estas tres restricciones, y la documentación las señala a lo largo de todo el texto:

1. **Sin hardware AMD** ⇒ sin observación en tiempo de ejecución (la más crítica de las tres carencias).
2. **Sin desensamblador de AMDGPU** (`llvm-objdump` no disponible) ⇒ sin desensamblado del lado del dispositivo; las relaciones de llamada de símbolos como `swin_layer` no están probadas.
3. **Sin cadena de herramientas de Intel / hardware Xe** ⇒ todo lo relativo a capacidades concretas de Xe / SPIR-V / XMX está **marcado como "requiere documentación externa" y se deja sin conclusión**.

**Por lo tanto, el nivel de nuestras conclusiones es "nivel de bytes estático"**: lo que se puede dar, se da con evidencia de bytes; lo que no, se marca como "sin resolver" junto con una petición de documentación externa.

---

## Cómo contribuir

- **Cerrar los tres huecos** (véase "Se busca ayuda" arriba) — la contribución más valiosa.
- **Corregir una conclusión**: si una conclusión documentada discrepa de la evidencia de bytes, adjunta **archivo + desplazamiento + bytes en bruto + comando de reproducción**.
- **Aportar documentación externa** para los puntos marcados como "requiere documentación externa".
- **Mejorar las herramientas o la documentación.**

Véase [CONTRIBUTING.md](CONTRIBUTING.md). Este proyecto tiene estándares de evidencia altos (las negaciones universales deben dar rango + patrón + número de coincidencias), pero **a un PR con una conclusión correcta y evidencia insuficiente solo se le pedirá que añada evidencia, nunca se rechazará de plano**.

## Licencia y aspectos legales

- La **obra original** (documentación, scripts) está bajo la **Licencia MIT** — véase [LICENSE](LICENSE).
- Los **binarios de terceros** (en `binaries/`) **no** están cubiertos por esa licencia; los derechos de autor pertenecen a sus respectivos titulares. Los orígenes y los SHA256 están en [EXTERNAL_BINARIES.md](EXTERNAL_BINARIES.md).
- Esto es **investigación de interoperabilidad**. No contiene código de elusión de DRM ni binarios con derechos de autor de NVIDIA. Si un titular de derechos solicita la retirada, cumpliremos de inmediato — véase [LEGAL.md](LEGAL.md).

## Exención de responsabilidad

Esta es una investigación estática independiente, proporcionada **"tal cual", sin garantía de ningún tipo**. Los usuarios **asumen todo el riesgo y la responsabilidad legal** derivados de cualquier uso del contenido de este repositorio.
