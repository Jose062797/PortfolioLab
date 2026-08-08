# Plan de Auditoría — PortfolioLab

> Creado: 2026-07-16. Documento de trabajo para perfeccionar el proyecto.
> Estado de cada ítem: ⬜ pendiente · 🔄 en curso · ✅ cumplido · ❌ hallazgo abierto

## Dimensión 1: Correctitud matemática y financiera 🔴

La razón de ser del proyecto. La verificación "bit-idéntica" con PyPortfolioOpt
se hizo bajo un stack anterior (pandas 2.x, numpy 1.x, Python 3.12) y debe
re-validarse bajo el stack actual (pandas 3, numpy 2.5, Python 3.14).

- ✅ D1.1 Paridad con PyPortfolioOpt puro en los 6 caminos de optimización
  (Min Variance, Max Sharpe, Target Risk, Target Return, BL con views, L2 reg),
  como suite de regresión permanente (`tests/test_parity.py`, 10 tests).
- ✅ D1.2 Reproducir el portafolio de referencia (GUIA_TESTEO_MANUAL, código
  original del profesor del MIT) y confirmar resultados equivalentes.
- ✅ D1.3 Verificar convenciones financieras: anualización √252, Sharpe ex-ante
  vs ex-post con rf=3% consistente, Omega con sigma=(upper-lower)/2,
  correlación derivada de covarianza.
- ✅ D1.4 Casos borde numéricos: todos los retornos bajo el rf, covarianza casi
  singular, historiales de distinto largo, targets infactibles
  (`tests/test_edge_cases.py`, 6 tests).

## Dimensión 2: Calidad y resiliencia de datos (yfinance) 🔴

- ✅ D2.1 Ticker inexistente / deslistado a mitad de rango / historiales desiguales.
- ✅ D2.2 Fallback de market cap a $1e9: ya no existe — el motor lanza
  `DataDownloadError` sin fallback silencioso (mejor que lo planeado).
- ✅ D2.3 Confirmar precios ajustados (splits/dividendos) en todos los caminos.
- ✅ D2.4 Validación del formato yfinance 1.5.x (salto desde 0.2.x sin revisión).

## Dimensión 3: Compatibilidad y deuda de dependencias 🟠

- ✅ D3.1 URGENTE: migrar `st.components.v1.html` → `st.iframe` (eliminación
  anunciada para después del 2026-06-01 — fecha ya vencida).
- ✅ D3.2 Pinning exacto en requirements.txt + política de actualización
  deliberada. (Decidido e implementado 2026-07-16: versiones exactas
  verificadas por la suite; ritual de actualización documentado en el
  propio requirements.txt.)
- ✅ D3.3 Test de humo de PyPortfolioOpt 1.5.6 sobre pandas 3 — cubierto de
  sobra por la suite de paridad (D1.1), que ejercita todos los caminos de
  pypfopt sobre el stack actual.

## Dimensión 4: Calidad del testing 🟠

- ✅ D4.1 Tests para módulos sin cobertura: pdf_generator/pdf_shared,
  visualizations, session_manager (+ run_optimization end-to-end).
- ✅ D4.2 Auditoría de calidad de tests existentes (verificación por mutación
  de 5 puntos clave del motor — las 5 detectadas tras cerrar 1 brecha).
- ✅ D4.3 Tests de regresión con valores numéricos congelados (seed fijo,
  `tests/test_regression_frozen.py`).
- ✅ D4.4 Cobertura de la capa `pages/` con `streamlit.testing.v1.AppTest`
  (2026-07-20, ver "Fase 5" abajo). Era la única capa sin red de seguridad.

## Dimensión 5: Robustez y manejo de errores 🟡

- ✅ D5.1 Todo error termina en mensaje claro en la UI (nunca traceback).
- ✅ D5.2 Fallbacks comunicados al usuario, no solo al log.
- ✅ D5.3 Entradas absurdas en tickers rechazadas con gracia.

## Dimensión 6: Rendimiento y UX 🟡

- ✅ D6.1 Decisión consciente sobre caching (st.cache_data con TTL vs frescura).
- ✅ D6.2 Peso del home (~1.5 MB de imágenes base64 inline); objetivo < 3s en frío.
- ✅ D6.3 Responsividad móvil del CSS de styles.py.

## Dimensión 7: Seguridad 🟡

- ✅ D7.1 Auditar todos los `unsafe_allow_html` (ninguna entrada de usuario → HTML).
- ✅ D7.2 `pip-audit` de dependencias.
- ✅ D7.3 Sin secretos en historial de git; secrets.toml fuera del repo.

## Dimensión 8: Mantenibilidad y documentación 🟢

- ✅ D8.1 Evaluar partición de styles.py y documentar selectores de Streamlit atacados.
- ✅ D8.2 Docstrings y CLAUDE.md 100% consistentes con la realidad.
- ✅ D8.3 Disclaimer educativo visible en web y PDF.

## Fases

| Fase | Ítems | Estado |
|------|-------|--------|
| 1 | D3.1 + Dimensión 1 completa | ✅ 2026-07-16 |
| 2 | Dimensiones 2 y 4 | ✅ 2026-07-16 |
| 3 | Dimensiones 5, 6 y 7 | ✅ 2026-07-16 |
| 4 | Dimensión 8 + re-verificación final | ✅ 2026-07-16 |
| 5 | D4.4 — capa `pages/` con AppTest | ✅ 2026-07-20 |

## Registro de hallazgos

### Fase 1 (2026-07-16)

**D3.1 — Migración st.iframe (resuelto).** Un solo uso en
`utils/styles.py::inject_pwa_support`. Detalle de API: `st.iframe` exige
dimensiones positivas (0 era válido en `components.html`) → se usa 1×1 px.
Verificado en navegador: el script PWA sigue inyectando manifest,
theme-color y apple-touch-icon en el documento padre.

**D1.1 — Paridad (verificada).** El motor produce salida idéntica a
PyPortfolioOpt crudo bajo el stack actual (Python 3.14, pandas 3.0.3,
numpy 2.5.1): pesos exactamente iguales (`clean_weights`), métricas con
rtol 1e-12, posterior y covarianza BL idénticos (`assert_series_equal` /
`assert_frame_equal` estrictos). La afirmación de CLAUDE.md vuelve a
tener respaldo ejecutable.

**D1.2 — Caso MIT (verificado, 11/11).** Los 6 escenarios de la guía se
ejecutaron con datos reales de mercado. Escenario 5 (BL con 10 views):
el posterior se movió hacia la view en 10/10 tickers, KO terminó con
peso 0.00% (view negativa) y AMZN/BAC fueron los 2 mayores pesos —
exactamente la estructura que la guía exige. Min Variance tuvo la menor
vol (12.48%), Max Sharpe el mayor Sharpe (0.644), target risk respetó
20.00%, target return entregó 10.41% ≥ 10%.

**D1.3 — Convenciones (verificadas).** √252 vía constante única;
Sharpe ex-post canónico (media/desv. de excesos diarios × √252, rf/252);
retorno anualizado geométrico (CAGR); Omega σ=(upper−lower)/2;
correlación = cov / outer(σ,σ). *Observación menor (no error):* el
Sortino promedia los cuadrados solo sobre los días negativos; la
convención Sortino–van der Meer divide por N total. Ambas son usadas en
la industria; documentado por si se quiere alinear en el futuro.

**D1.4 — Casos borde (cubiertos).** Retornos todos bajo el rf → 
`OptimizationError` tipado (no crash) en Max Sharpe, y Min Variance sigue
funcionando; targets infactibles (return > max, vol < min) → error tipado;
covarianza casi singular (activos 99.99% colineales) → optimiza sin
explotar; ticker con historial más corto (NaN head) → sin NaN en mu/S
y optimización válida.

**Datos colaterales observados (para Fase 2):** "Sin rango" descarga el
historial completo (16.241 días ≈ 64 años para el universo de 15 tickers)
— relevante para D2/D6 (volumen de descarga y ventana de covarianza).

### Fase 2 (2026-07-16)

**D2.1 — HALLAZGO CORREGIDO (el más importante de la fase).** Un ticker
inexistente o deslistado pasaba la validación de la UI, llegaba de
yfinance como columna 100% NaN y producía `mu = NaN` → el usuario veía
errores crípticos de solver ("Problem data contains NaN or Inf") y un
resultado vacío. Fix en `download_data`: detecta columnas todo-NaN y
lanza `DataDownloadError` nombrando el ticker; los errores de datos
deterministas ya no se reintentan (antes se reintentaba 3 veces algo
irreparable). Verificado end-to-end con datos reales y cubierto con
tests offline mockeados.

**D2.2 — Ya resuelto en el código.** El fallback silencioso a $1e9
documentado en CLAUDE.md ya no existe: `download_market_caps` lanza
`DataDownloadError` tras reintentos (correcto — un market cap inventado
corrompe los priors de BL). CLAUDE.md actualizado.

**D2.3 — Precios ajustados confirmados.** yfinance 1.5.1 usa
`auto_adjust=True` por defecto; verificado empíricamente (AAPL
2020-01-02: raw 75.09 vs ajustado 72.33). Todos los caminos usan `Close`
del download por defecto → ajustado por splits/dividendos.

**D2.4 — Formato yfinance 1.5.x validado.** Las sondas empíricas y los
6 escenarios de la guía funcionaron sin incidencias sobre el salto
0.2.x → 1.5.1. Dato: Yahoo ya NO entrega historial de tickers
deslistados (ATVI devuelve vacío) — un deslistado se comporta igual que
un inexistente, y el fix de D2.1 cubre ambos.

**D4.1 — Cobertura nueva (12 tests).** `tests/test_report_outputs.py`:
run_optimization end-to-end (contrato del result dict + contrato de
error), pdf_generator (bytes %PDF válidos desde el pipeline real),
visualizations (diagonal de correlación = 1, pie de allocation,
frontera eficiente, gráfico histórico) y session_manager (roundtrips).

**D4.2 — Verificación por mutación: 5/5 detectadas.** Mutaciones
probadas: omega /2→/4, max_sharpe sin rf, √252→√365, min_volatility→
max_sharpe, ledoit_wolf→sample_cov. La primera pasada reveló que
√252→√365 NO era detectada (los tests de backtest no fijaban el factor
de anualización) — brecha cerrada con
`test_annualization_factor_exact` (valores a mano, rel 1e-12).

**D4.3 — Valores congelados.** `tests/test_regression_frozen.py`
fija pesos exactos y métricas (rel 1e-9) de Min Variance y BL-con-view
sobre el fixture seed-42, bajo el stack verificado por paridad. Si una
actualización de dependencias cambia los números silenciosamente, estos
tests lo delatan.

### Fase 3 (2026-07-16)

**D7.1 — Vector XSS endurecido.** De los 34 `unsafe_allow_html`, los
únicos con entrada de usuario interpolada son los que renderizan el
ticker (1_Stocks línea ~800, tablas de 2_Portfolio). Explotabilidad
real baja (el render exige descarga exitosa → símbolo Yahoo válido; los
`st.error` escapan HTML), pero se aplicó defensa en profundidad:
allowlist de formato `[A-Z0-9.\-^=]{1,15}` en `validate_inputs` y en la
entrada de Stocks. Beneficio lateral: un typo se rechaza al instante
sin ir a la red. Verificado en navegador con `FAKE<>!!` y `BAD!TICKER`;
símbolos exóticos reales (BRK-B, BF.B, ^GSPC, BTC-USD, EURUSD=X)
cubiertos por test.

**D7.2 — pip-audit: sin vulnerabilidades conocidas** (2026-07-16).
Nota operativa: pip-audit necesita `PYTHONUTF8=1` en esta máquina (la
"ó" de la ruta rompe su detección de pip).

**D7.3 — Sin secretos.** Historial de git limpio de patrones de
credenciales; `secrets.toml` no está trackeado.

**D5.1/D5.3 — Verificado en navegador.** Ticker inválido en Stocks →
warning inmediato y escapado; en Portfolio → mensaje del validador
nombrando el símbolo. Los errores de datos/optimización ya tenían
mensajes categorizados en la UI (líneas 429-435 de 2_Portfolio).

**D5.2 — Fallback greedy ahora visible.** `calculate_allocation`
devuelve el método usado (`lp`/`greedy`); el result dict lo incluye
(`allocation_method`) y la pestaña Allocation muestra un caption cuando
se usó greedy (antes solo quedaba en el log del servidor).

**D6.2 — HALLAZGO CORREGIDO: home 2.09 MB → 0.11 MB de DOM (−95%).**
Las 3 imágenes grandes (hero + 2 thumbnails) iban inline como base64 y
viajaban por el websocket en cada rerun. Ahora se sirven desde
`/app/static/` (enableStaticServing ya estaba activo para la PWA) con
caché del navegador. Verificado: 200 OK en las 3, layout intacto.
El logo del navbar (53 KB) sigue en base64 — compartido por todas las
páginas vía styles.py, impacto menor.

**D6.3 — Móvil OK.** Sin overflow horizontal en home ni Portfolio a
375px; las tarjetas del home se apilan verticalmente; el hero se adapta.

**D6.1 — Decisión de caching (documentada, no implementada).** El
optimizador descarga datos frescos en cada corrida por diseño (fidelidad
al notebook y datos al día para decisiones) — se mantiene. Mejora
opcional futura: `st.cache_data(ttl=300)` en la página Stocks
(exploración rápida de varios tickers re-descarga todo al volver a uno
ya visto); no aplica al optimizador.

**Observación colateral (Fase 4):** los screenshots del navegador hacen
timeout en todas las páginas — probablemente animaciones CSS infinitas
(`bl-animate`) mantienen el renderer ocupado. No afecta usuarios, pero
dificulta tooling; candidato a `animation-iteration-count` finita o
`prefers-reduced-motion`.

### Fase 4 (2026-07-16) — cierre

**D8.3 — Disclaimer web agregado.** El PDF ya tenía página completa de
disclaimers, pero la web no tenía ninguno. El footer global ahora
incluye "For educational and informational purposes only — not
investment advice" en todas las páginas. Verificado en navegador.

**D8.1 — styles.py: documentado, no particionado.** Se agregó un
"maintenance map" al docstring con el inventario exacto de selectores
internos de Streamlit que el CSS sobreescribe (los únicos puntos que se
rompen con actualizaciones de Streamlit — auditar tras cada bump).
Decisión razonada: NO partir el módulo; el riesgo vive en esos
selectores, no en el tamaño del archivo, y partirlo agregaría problemas
de orden de inyección entre CSS crítico y compartido.

**D8.2 — Docs consistentes.** CLAUDE.md actualizado: árbol con los 8
archivos de test y AUDITORIA.md, firma nueva de calculate_allocation
(3-tupla con método), allowlist de tickers, imágenes desde /app/static,
disclaimer. Cero referencias restantes a web/, CLI, DEFAULT_MARKET_CAP
o components.html.

**Corrección de la observación colateral:** las animaciones bl-animate
son finitas (fadeInUp 0.5s, una pasada) — la hipótesis de animaciones
infinitas era incorrecta. El timeout de screenshots persiste con el DOM
liviano; es un artefacto de la herramienta de captura frente al
websocket persistente de Streamlit / service worker PWA, sin impacto en
usuarios. Sin acción.

**Re-verificación final:** 68/68 tests; recorrido completo en
navegador: home (disclaimer, imágenes estáticas 200 OK), Stocks con
BTC-USD (allowlist no rompió símbolos exóticos), Portfolio con 4
tickers (optimización exitosa, caption greedy visible, PDF generado).

### Fase 5 (2026-07-20) — capa `pages/`

**D4.4 — Cobertura de la UI (27 tests nuevos, 75 → 102).** La capa `pages/`
era la única sin tests automatizados. Se cubrió con
`streamlit.testing.v1.AppTest`, que ejecuta el script de la página **en el
mismo proceso**: los parches de yfinance de `conftest.py` aplican tal cual, así
que los tests nuevos son offline y deterministas como el resto de la suite
(+26s de suite, total ~38s).

Archivos: `tests/test_pages_portfolio.py` (19) y `tests/test_pages_smoke.py`
(8), más la fixture aditiva `mock_yfinance_extended` en `conftest.py` (universo
ampliado con el par casi-duplicado VOO/IVV). Las fixtures existentes no se
tocaron.

**El selector de estimador quedó verificado (cierra el pendiente de Fase 4).**
La observación de que los selectbox de Streamlit "resisten la automatización"
era cierta **solo para el navegador**: AppTest sí les fija valor y el valor
llega al servidor. El test no se conforma con eso — corre la optimización dos
veces (CAPM vs. media histórica) con objetivo **Max Sharpe** y exige que los
pesos difieran. Max Sharpe es deliberado: Min Variance ignora `mu` por completo
y no distinguiría un estimador del otro.

**Hallazgo del proceso: la primera versión de la fixture no discriminaba.**
Con 3 activos, la correlación VOO/IVV con shrinkage quedaba en 0.971 — sobre
el umbral de 0.95. Es decir, el test del aviso de solapamiento habría pasado
igual si alguien revertía el detector a la covarianza almacenada (justo la
trampa documentada en Fase 3). Recalibrada a 5 activos: 0.9996 empírica vs
0.926 con shrinkage, reproduciendo la brecha real (0.9997 vs 0.949). La
propiedad se asserta explícitamente en
`test_fixture_discriminates_empirical_from_shrunk_correlation`, para que un
futuro cambio de fixture que colapse la brecha falle en vez de debilitar la
suite en silencio.

**Verificación por mutación: 4/4 detectadas.** Mutaciones aplicadas sobre
`pages/2_Portfolio.py`: (1) elección de estimador ignorada, (2) bloqueo BL+forex
sin deshabilitar el botón Run, (3) detector de solapamiento leyendo la
covarianza con shrinkage, (4) caption del método greedy suprimido.

**Decisión: el caption greedy se testea por cableado, no por entorno.** El
camino real `lp`/`greedy` depende de si `ecos` está instalado (sí en CI 3.12,
no en local por falta de wheel cp314) — asertarlo directamente sería flaky. Los
tests fijan `allocation_method` en `session_state` y verifican que el caption
aparece y desaparece, que es la responsabilidad de la capa `pages/`.

**Nota de API aprendida:** el contenido de `st.info`/`st.success` NO aparece en
`at.markdown` (falló primero el test de la página About). Y `st.cache_data` es
global al proceso, no por sesión: los tests de la página Stocks lo limpian con
una fixture autouse para no volverse dependientes del orden.

## Estado final

Las 4 fases completadas el 2026-07-16. Suite: 35 → 69 tests.
Fixes de código: st.iframe, rechazo de tickers sin datos, allowlist de
símbolos, método de allocation visible, imágenes estáticas (−95% DOM),
disclaimer web.

Los 3 ítems abiertos se decidieron e implementaron el mismo día:
1. **Pinning exacto** en requirements.txt con las versiones verificadas
   por la suite + ritual de actualización documentado (D3.2).
2. **Cache TTL en Stocks** (D6.1): `st.cache_data` con TTL 300s (60s
   para intradía, 600s para financials trimestrales) SOLO en la página
   de exploración; el optimizador sigue descargando fresco por diseño.
   Verificado: un rerun completo de la página no genera descargas.
3. **Sortino → convención Sortino–van der Meer** (desviación downside
   sobre N total): valores comparables con la industria; guardado con
   test de valores a mano que además rechaza la convención anterior.

Deuda restante (menor, sin plan): logo del navbar en base64 (~70 KB).

Actualización 2026-07-20 (Fase 5): la capa `pages/` ya tiene cobertura
automatizada (D4.4). Suite: 35 → 102 tests.
