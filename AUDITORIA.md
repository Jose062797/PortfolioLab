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
| 6 | Coherencia de lo que se muestra | ✅ 2026-09-26 |
| 7 | Rediseño simple | ✅ 2026-09-27 |
| 8 | Auditoría de frontend y backend (dimensiones propias, ver Fase 8) | 🔄 pasos 1 a 4 hechos el 2026-10-08; falta el paso 5 (publicar) |

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

### Fase 6 (2026-09-26) — coherencia de lo que se muestra

**Motivo.** Antes de publicar el inicio nuevo, el usuario pidió revisar todo
"con mucho detalle", en especial figuras que no correspondieran a cómo la app
las genera de verdad. Se revisaron el inicio, las tres páginas, el PDF y el
README; un agente de solo lectura contrastó cada afirmación visible con el
código y encontró 33 puntos, que se verificaron uno por uno antes de tocar nada.

**Inicio: solo figuras reales.** La Fig. 1 ilustrativa (Plotly oscuro con nube
aleatoria y línea de mercado de capitales), las velas dibujadas en CSS y las
barras "esquemáticas" de paridad se veían como resultados de la app pero no lo
eran. Ahora el inicio dibuja con las mismas funciones que las herramientas
(`create_efficient_frontier_chart`, `create_price_chart`, `create_allocation_pie`)
sobre resultados del propio motor para cinco activos inventados, y la tabla de
paridad compara el motor con PyPortfolioOpt llamado directamente (diferencia 0).
Solo cambia la altura de cada gráfico. Afirmación retirada de la página
pública: "6 MIT reference cases" / "six scenarios from MIT course material".
El repositorio no lo documenta: la guía manual cita los notebooks del cookbook
y solo el escenario 5 lleva la etiqueta "Caso MIT" (según D1.2, reproduce el
portafolio de referencia del código original del profesor del MIT). Nombrar
al MIT en público requiere la redacción del usuario y una fuente; queda a su
decisión.

**Errores de cifras corregidos (con test cada uno):**
1. **Mapa de correlaciones con etiquetas cruzadas** (web y PDF) salvo que los
   tickers se escribieran en orden alfabético: la matriz llega en orden
   alfabético y se etiquetaba con el orden tecleado. Ahora se reordena y viaja
   con sus etiquetas (`covariance_tickers`). Verificado con datos reales contra
   un cálculo independiente.
2. **Historias desiguales = años sin riesgo.** El Ledoit-Wolf de PyPortfolioOpt
   convierte los retornos faltantes en ceros (`np.nan_to_num`); CLAUDE.md decía
   "borrado por pares", y era falso. Caso real: Min Variance con MSFT, AAPL,
   SNOW y KO (historia completa) ponía 50,4 % en SNOW, el más volátil. Decisión:
   estimar sobre las fechas en que todos los activos tienen precio; ahora da
   71,6 % en KO y 1,0 % en SNOW. Arregla también la mezcla cripto + acciones
   (fines de semana). Paridad intacta: con historias completas la entrada es la
   misma que en el cookbook, y un test exige igualdad con PyPortfolioOpt sobre
   las filas completas. La página avisa cuando la ventana se acorta.
3. **El PDF hacía otro backtest** que la web (rellenaba con 0, contaba fines de
   semana): mismas corridas daban otros periodos y cifras. Ahora ambos usan
   `prepare_backtest_prices` y coinciden exactamente.
4. **PDF de Markowitz con texto de Black-Litterman** (metodología, "BL
   Portfolio", limitaciones). Ahora el texto sigue al modelo y al objetivo.
5. **"$nan" como precio en el PDF** con cripto (última fila en fin de semana).
6. **Rendimientos "totales" en Stocks** que eran de precio; el gráfico usaba
   cierres ajustados por dividendos mientras la franja de retornos no. Ahora
   todo son cierres cotizados (ajustados solo por splits), como Yahoo.
7. **"$" fijo en Stocks** para acciones europeas, japonesas e índices: la moneda
   se muestra una vez junto al precio; los estados financieros en su moneda.
8. **Trimestres "Q3 FY25" inventados**: ahora "Sep 2025" (mes de cierre).
9. **Barras de 0 % para activos sin view**, "Max Supply" que en realidad era
   el suministro total, anotación del backtest que mezclaba dos puntos de
   partida, colores del mapa de correlaciones opuestos entre web y PDF.

**Textos corregidos:** backtest descrito como "in-sample" (pesos estimados con la
misma historia, rebalanceo diario, sin costos); "recommended portfolio" y
valoraciones ("mejor gestión del riesgo") eliminadas del PDF; ayuda de los
límites de las views (±1 desviación estándar), "at most" en el objetivo de
riesgo, consejo de datos insuficientes al revés, ejemplo de solapamiento
(VOO/IVV en vez de un ETF con sus componentes), nota de Black-Litterman sin
views, privacidad (Google Fonts, registros de la plataforma; estadísticas de
Streamlit desactivadas), README (número de tests, enlace roto al cookbook,
"professional-grade", "live pricing"), aviso de moneda para tickers no
estadounidenses. La contracción de Ledoit-Wolf lleva las correlaciones hacia
cero (no "hacia su promedio"): se comprobó y se corrigió el texto.

**Verificación.** Suite 114 → 128 tests. Mutaciones de los arreglos nuevos:
9/9 detectadas (una solo después de reforzar su test: el PDF mostraba "N/A" en
vez del precio y el test solo buscaba "$nan"). En la app real: corrida
Markowitz MSFT/AAPL/SNOW/KO con todas las pestañas, Stocks con SAP.DE, ^GSPC y
BTC-USD, y los PDF de ambos modelos leídos página por página.

**Después de publicar (`1147c0e`).** La verificación en producción encontró
dos cosas más. (1) La cifra de tests publicada decía 127: el último test se
añadió después de fijarla (corregido a 129). (2) Una corrida real falló con
"No price data found for: AAPL" y funcionó al segundo clic: Yahoo, limitando
pedidos desde los servidores compartidos, a veces devuelve vacía la columna de
un símbolo real, y la app lo trataba como símbolo inexistente, sin reintentar.
Ahora la columna vacía se reintenta como cualquier otra falla de descarga (3
intentos) y el mensaje nombra las dos causas posibles; un test cubre el caso
transitorio y verifica los 3 intentos (sin reintento, fallan 2 tests).

**Guía manual re-ejecutada con la ventana común (2026-09-26, `fa06a10`,
datos en vivo).** Los 6 escenarios cumplen lo que la guía pide: Min Variance
con la menor volatilidad y sobre su marcador, Max Sharpe con el mayor Sharpe,
el techo de 20 % respetado, el piso de 10 % cumplido, KO en 0 % y AMZN/BAC
como mayores pesos en el escenario 5, posterior = prior sin views. Dos
precisiones incorporadas a la guía: en el escenario 5 el posterior de BAC bajó
levemente pese a su view de 30 % (rango ancho, arrastrado por las demás views
vía correlaciones; los otros 9 se movieron hacia su view, antes eran 10/10), y
en el escenario 6 los pesos no son los de capitalización (ver el punto 1 de
abajo). La guía trae ahora una tabla con los resultados de ese día.

**Después (`f8a6f41`, publicado en `71e354c`).** Un portafolio que incluía SPY
rompía ambos backtests (web y PDF): `prepare_backtest_prices`, añadido en
`1147c0e`, sumaba la columna del benchmark aunque SPY ya fuera un activo, y la
tabla llevaba SPY dos veces ("Unable to coerce to Series"). Ahora la toma una
vez; un test corre SPY, AGG, GLD por los dos backtests (sin el arreglo, falla).
Verificado en producción el 2026-09-27 tras el reinicio: SPY, AGG, GLD con
Markowitz muestra el backtest completo.

**Pendiente de decisión del usuario:**
- Black-Litterman calcula el prior y la aversión al riesgo con tasa libre 0 %
  (defaults de PyPortfolioOpt, como el cookbook) pero optimiza con 3 %: sin
  views, los pesos se alejan de los de mercado. Se corrigió el texto que decía
  lo contrario; cambiar el modelo exige actualizar la paridad.
- Un portafolio solo de cripto anualiza con 252 días aunque cotiza 365.
- Portafolios en otras monedas: solo se avisa; no hay conversión.

### Fase 7 (2026-09-27) — rediseño: más simple y más claro

**Motivo.** Con el inicio nuevo publicado, el usuario encontró el aspecto
"inusual y no tan amigable", con demasiada complejidad, y la sección
Verification (la tabla de paridad con PyPortfolioOpt) "claramente de más,
nunca vi una página poner algo así". Tras revisar herramientas parecidas eligió:
inicio simple con ejemplos, objetivos en lenguaje simple, menos avisos y notas,
y un estilo más claro en todas las páginas. Pidió instalar y usar la skill
ui-ux-pro-max (github.com/nextlevelbuilder/ui-ux-pro-max-skill, licencia MIT)
para guiar el diseño. Se instaló para todos sus proyectos en
`C:\Users\jose_\.claude\skills\ui-ux-pro-max` (solo este equipo), copiando la
carpeta de la skill en el commit `823b0a1` tras revisar sus scripts: solo
biblioteca estándar, sin red, escriben archivos solo con `--persist`.

**Qué se tomó de la skill.** Sus búsquedas de sistema de diseño para una
herramienta financiera coincidieron en el estilo "Minimalism & Swiss Style"; de
tres consultas se descartó lo que no calzaba (fondos oscuros, tipografía
manuscrita, patrón de ventas corporativas) y se tomó el patrón "Product Demo +
Features" (portada y luego el producto mostrado con ejemplos). Reglas aplicadas:
sin emojis como íconos, foco visible con teclado, objetivos táctiles de 44 px,
`prefers-reduced-motion`, contraste 4,5:1, etiquetas en tipo oración, una sola
acción principal, texto de ayuda bajo campos complejos, divulgación progresiva
(caja de notas), cifras tabulares, dona solo hasta 6 porciones (barras después).

**Cambios.**
1. **Inicio**: portada clara (titular, dos botones, una línea de datos), tres
   portafolios de ejemplo que abren Portfolio con el formulario lleno
   (`?example=<clave>`; se aplica una vez y no ejecuta solo), las dos
   herramientas con sus gráficos de ejemplo y "How it works" en tres pasos. Se
   quitaron la Fig. 1, las cifras del proyecto, la banda de verificación y
   `TEST_COUNT`. About conserva una pregunta frecuente sobre cómo se verifican
   los números.
2. **Ejemplos elegidos con datos reales** (todos Markowitz, porque
   Black-Litterman necesita capitalizaciones y Yahoo las limita en la nube):
   Big Tech con mejor retorno por riesgo, acciones de dividendos con menor
   riesgo, y acciones/bonos/oro con límite de riesgo de 10 %. En este último,
   con CAPM el oro quedaba en 0,9 % (beta casi nula); con media histórica,
   consejo que la propia página da para bonos y materias primas, el reparto
   es 36/35/29.
3. **Objetivos en lenguaje simple** ("Lowest risk", "Best return for the
   risk", ...) con `format_func`: los valores internos no cambian. El detalle y
   el PDF muestran también el nombre técnico. Límites y views se escriben en
   porcentaje.
4. **Menos avisos**: sin cajas para el formulario vacío, el conteo de tickers,
   cada view agregada, el éxito de la corrida ni la explicación de Markowitz;
   las notas de resultados (solapamiento, historia común más corta, fines de
   semana) van en una sola caja plegada que solo aparece si hay algo que decir.
   Las pestañas perdieron su encabezado repetido y los textos largos se
   acortaron.
5. **Estilo**: tokens claros, azul como único acento, Inter también para las
   cifras (DM Mono eliminada), pestañas como control segmentado, métricas sin
   mayúsculas ni animación, emojis retirados de Stocks y de los avisos.

**Errores encontrados al verificar en la app real.** (a) Los títulos salían
gris pizarra: Streamlit pone `color: inherit` a los encabezados de markdown;
arreglado con `!important`. (b) En Detalles, dos `$` en el mismo markdown se
leían como fórmula LaTeX y mostraban "**Assets:**" crudo; ahora se escapan.
(c) A unos 820 px la etiqueta "Expected return" se cortaba ("Expected re…",
el detalle cosmético 9 de ESTADO): ahora las etiquetas pasan a dos líneas y,
entre 641 y 1100 px, todas reservan ese espacio para que las cifras queden a
la misma altura. Ninguno de los tres lo veían los tests.

**Verificación.** Suite 130 → 136 tests (enlaces de ejemplo, porcentajes que
llegan como fracciones al motor, objetivo en palabras con su meta, caja de
notas, dona/barras). Paridad y regresión congelada intactas: el motor no se
tocó. Mutaciones del rediseño: 8/8 detectadas. En la app local, escritorio
(1440 px) y celular (375 px) sin scroll horizontal; los tres ejemplos corren
con datos reales (cifras en la guía, escenario 7).

**En producción (`b6d88e9`, 2026-09-27, tras el reinicio del usuario).**
Entre el push y el reinicio el inicio mostró `ImportError` (la página nueva
importa `goal_text`, que el proceso viejo no tenía cargado): se esperaba y lo
resolvió el reinicio. Después se revisó:
- Inicio en 1440 y 375 px: portada, tres ejemplos, dos herramientas con sus
  gráficos, pasos, pie con el aviso; títulos azul marino, logo servido como PNG
  real (bytes, no solo el 200), nada del diseño anterior, sin scroll horizontal.
- Los tres enlaces de ejemplo desde la dirección real (la app dentro del
  iframe): cada uno llena el formulario (tickers, modelo, objetivo, límite y
  estimador), la barra de direcciones queda en `/Portfolio` sin el parámetro y
  nada corre solo. Al presionar Run, Big Tech 17,35 % / 23,09 % / 0,621,
  dividendos 7,70 % / 16,78 % / 0,280 y acciones/bonos/oro 8,47 % / 10,00 % /
  0,547: lo mismo que en local, con asignación exacta (ecos) en la nube.
- Todas las pestañas: dona con etiquetas, frontera con "Your portfolio",
  backtest con su tabla, correlaciones, Detalles con los montos en dólares
  (sin fórmulas LaTeX) y el objetivo en palabras; botón del PDF presente (el
  informe se generó sin error) y caja de notas con la historia común.
- Black-Litterman con views escritas en %: AAPL 12/8/16, MSFT y GOOGL 15/10/20
  llegaron al motor como 0,12 y 0,15 (barras de "Your Views"), el posterior se
  movió hacia cada view y Yahoo entregó las capitalizaciones esta vez.
- Stocks: estado vacío, símbolo inválido, VOO (ETF), AAPL (tres pestañas) y
  BTC-USD (cripto), sin emojis. About: pestañas y las cuatro preguntas.
- Menú desde la dirección real: About abre en `/About` sin anidarse; Atrás
  vuelve al inicio.
- La guía manual se repitió con el código nuevo: escenarios 1 a 6 idénticos a
  la referencia del día anterior. Los PDF de los escenarios 3 y 5 se leyeron
  página por página: portada, resumen, metodología y detalle nombran el
  objetivo en palabras con su nombre técnico.

**Ajuste pedido por el usuario al verificar.** Los botones de la portada
estaban al revés del orden de las herramientas ("investigar primero y calcular
el portafolio después"): ahora "Explore a stock" va a la izquierda y "Build a
portfolio", el principal, a la derecha; un test lo fija y detecta el orden
viejo.

**Decisiones finales del usuario (2026-09-27).** Portfolio abre con Markowitz
(no necesita capitalizaciones, que Yahoo limita en la nube); la pregunta
frecuente sobre la verificación se queda; y el PDF, como la web, dibuja barras
con más de seis activos (una torta de 13 porciones no se leía). Tests: 138.

**Test inestable hallado en la última corrida.** `TestViewsInPercent`, nuevo en
el rediseño, anulaba `time.sleep` en todo el proceso para saltarse las pausas
entre consultas de capitalización. AppTest espera la página con
`time.sleep(0.001)` en un bucle: con la anulación, ese bucle giraba sin pausa y
dejaba sin tiempo al hilo de la página. El test pasó por suerte en las
corridas del rediseño y en CI, y después se agotó a los 180 s (310 s en total;
la misma lógica tarda 2 s fuera de AppTest). Ahora solo se saltan las pausas
largas del motor: el test tarda 3,8 s, sigue detectando las views sin dividir
por 100, y la suite completa bajó de 150-270 s a 88 s.

### Fase 8 (2026-10-08) — auditoría de frontend y backend

**Motivo.** El usuario pidió auditar la página periódicamente, en cinco pasos:
(1) definir dimensiones, (2) planificar, (3) analizar hallazgos y planificar
cómo abordarlos, (4) corregir, verificar y documentar, (5) publicar. Punto de
partida: `main` = `e06d8e1`, 140 tests, producción verificada el 2026-10-03.
Desde la auditoría anterior cambiaron el rediseño (Fase 7), el PDF que se arma
al hacer clic (en otro hilo) y el objetivo de servir a muchos usuarios.

#### Paso 1 — dimensiones (aprobadas por el usuario el 2026-10-08)

Frontend (lo que se ve y se usa):

| # | Dimensión | Está bien cuando |
|---|---|---|
| F1 | Exactitud de lo mostrado (4 páginas, PDF, README, About) | Todo coincide con lo que el código calcula; web y PDF dicen lo mismo |
| F2 | Usabilidad y flujo (vacío, cargando, error, éxito; ejemplos) | Se entiende sin instrucciones; cada error dice cómo seguir |
| F3 | Accesibilidad (contraste, teclado y foco, nombres, gráficos, zoom 200 %) | WCAG 2.2 AA en lo que Streamlit permite controlar |
| F4 | Pantallas y navegadores (375-1440 px; descarga del PDF) | Sin scroll horizontal ni cortes; el PDF baja en todos |
| F5 | Consistencia visual (tokens, tipografía, PDF, selectores de Streamlit) | Las 4 páginas son una sola app; ningún estilo se cayó en silencio |
| F6 | Rendimiento percibido (despertar, primera carga, corrida, recarga) | Tiempos medidos, sin esperas evitables |
| F7 | Comportamiento en producción (iframe `/~/+/`, enlaces, estáticos, service worker) | Producción se comporta igual que local |

Backend (lo que calcula y sostiene la app):

| # | Dimensión | Está bien cuando |
|---|---|---|
| B1 | Correctitud matemática (paridad, congelados, convenciones) | Idéntico a la referencia; decisiones abiertas documentadas |
| B2 | Datos y resiliencia ante Yahoo | Ninguna falla de Yahoo da cifras erradas, solo mensajes claros |
| B3 | Manejo de errores (incluido el hilo del PDF diferido) | Nunca un traceback al usuario; el registro permite diagnosticar |
| B4 | Varios usuarios a la vez (memoria, cachés, matplotlib en hilos) | Sesiones simultáneas no se mezclan, no se caen ni agotan memoria |
| B5 | Seguridad (entradas, `?example=`, HTML sin escapar, dependencias, secretos) | Sin vía de inyección; dependencias sin avisos abiertos |
| B6 | Dependencias y plataforma (versiones, desusos, Python 3.12/3.14) | Nada vence pronto; actualizaciones por el ritual |
| B7 | Calidad de los tests (cobertura, mutaciones, lentos o inestables) | Lo importante tiene un test que fallaría si se rompe |
| B8 | Mantenibilidad del código (código muerto, duplicación, tamaño) | Un cambio típico toca pocos archivos; sin código huérfano |

Transversales: **T1** documentación y orden (CLAUDE, ESTADO, AUDITORIA, guía,
README coherentes con el código; carpeta sin sobrantes) y **T2** operación (CI,
publicación y reinicio, salud, cómo se detecta una caída).

Prioridad: más atención a F3 y B4 (nunca auditadas formalmente), F1, F2 y F5
(cambiaron con el rediseño), F7 y B3 (PDF en otro hilo). B1 y B6 van livianas:
las protegen la paridad y el ritual de dependencias.

#### Paso 2 — plan

**Reglas mientras dure la auditoría.**
1. No se cambia código: solo se lee, se mide y se anota. Los arreglos son el
   paso 4, después de priorizar con el usuario en el paso 3.
2. Cada hallazgo lleva evidencia reproducible (archivo:línea, medición,
   captura o salida) y se verifica antes de anotarlo. En la Fase 6 un agente
   propuso 33 puntos y se revisaron uno por uno; se repite ese criterio.
3. Scripts temporales en el scratchpad de la sesión, nunca en el proyecto.
4. Producción solo se observa: las pruebas de carga van en local (la nube es
   un recurso compartido y Yahoo limita sus IP).
5. Consultas a Yahoo moderadas: las corridas necesarias, no barridos.
6. Lo que es decisión del usuario (modelo, alcance, costos) se anota como
   decisión, no como hallazgo.

**Severidad.** 🔴 Crítico: cifra errada mostrada, caída del servicio o
vulnerabilidad explotable. 🟠 Alto: falla un flujo principal, barrera de
accesibilidad que impide usar algo, o riesgo probable con varios usuarios.
🟡 Medio: confunde o degrada sin impedir; deuda con fecha de vencimiento.
🟢 Bajo: cosmético, orden, redacción.

**Formato de cada hallazgo.** ID `<dimensión>-NN` (p. ej. `F3-02`), severidad,
evidencia, propuesta y estado: ⬜ abierto · ✅ corregido · ⏸ decisión del
usuario · ➖ descartado (con el motivo).

**Etapa 0 — línea base.** Árbol limpio y sincronizado; suite completa con
`--durations=15`; CI del último commit; salud de producción y versión de
Streamlit (`/api/v2/app/status`). Herramientas (el usuario aprobó el plan,
su instalación y axe-core el 2026-10-08; quiere que sirvan también a proyectos
futuros): `ruff` 0.16.10 y `vulture` 2.16 en un entorno compartido fuera de
Dropbox, `C:\Users\jose_\tools\audit-env`; `coverage` 7.16.2 en
`C:\Users\jose_\portfoliolab-env` (corre con las librerías del proyecto; no se
agregó a `requirements-dev.txt`); axe-core 4.12.1 desde cdnjs con hash de
integridad. Guía: `C:\Users\jose_\tools\LEEME-herramientas-auditoria.md`.

**Etapa 1 — backend, revisión estática (B1, B3, B5, B6, B7, B8).**
- B1: paridad y congelados en verde; las decisiones abiertas (tasa 0 % frente
  a 3 % en Black-Litterman, cripto con 252 días, monedas) dicen lo mismo en
  CLAUDE, About, la guía y esta auditoría. La guía manual no se repite entera:
  el motor no cambió desde el 2026-09-27.
- B3: cada `except` y cada `raise` hasta el mensaje que ve el usuario; qué
  pasa si `build_report_pdf` falla dentro del hilo de la descarga.
- B5: cada `unsafe_allow_html` y qué datos entran en él; `?example=` con
  valores inválidos; allowlist de tickers; patrones de claves en el historial
  de git; dependencias contra OSV (procedimiento de CLAUDE.md);
  `.streamlit/config.toml` (XSRF, CORS, estadísticas).
- B6: `pip list --outdated` (solo lectura); avisos de desuso en el registro
  de Streamlit; notas de versión de Streamlit posteriores a 1.59 que toquen
  lo que usa el CSS.
- B7: cobertura de líneas por módulo; mutaciones del PDF diferido (que la
  página lo arme en cada recarga, que `build_report_pdf` no agregue el
  backtest); tests de más de 5 s; suite corrida 3 veces para detectar
  inestables.
- B8: código muerto (vulture), errores simples y estilo (ruff), funciones y
  archivos muy largos, números fuera de `core/constants.py`, `print` o
  `except:` sin tipo.

**Etapa 2 — backend, pruebas dinámicas en local (B2, B4).**
- B2: corridas reales difíciles: 20 tickers, rango máximo, un activo recién
  listado, cripto con acciones, un ETF de bonos, un símbolo inexistente y
  Black-Litterman (capitalizaciones). Ninguna falla puede dar cifras sin aviso.
- B4: servidor local con varias sesiones simultáneas: memoria del proceso por
  sesión, tiempos con varias corridas a la vez, dos PDF armados al mismo
  tiempo (`core/pdf_shared.py` usa el estado global de `pyplot`, por ejemplo
  `plt.tight_layout()`: comprobar que cada PDF salga con sus propios
  gráficos), cachés de Stocks compartidas. Límites de recursos de Community
  Cloud según su documentación oficial.

**Etapa 3 — frontend en la app local (F1 a F6).**
- F1: las 4 páginas y un PDF por modelo, cada texto y cifra contra el código
  (un agente de solo lectura propone y cada punto se verifica); README y
  About contra el código actual.
- F2: primera visita → ejemplo → Run → pestañas → PDF; formulario con errores
  (1 ticker, 21, símbolo inválido, forex con Black-Litterman, fechas
  invertidas); Run presionado dos veces; Stocks con símbolo inválido, ETF,
  cripto e índice. Lista de reglas UX de la skill ui-ux-pro-max.
- F3: árbol de accesibilidad de cada página (nombres de botones, enlaces y
  campos); recorrido con Tab y foco visible; contraste calculado sobre los
  colores reales; alternativa textual de los gráficos; zoom 200 % (640 px);
  `prefers-reduced-motion`. Opcional, con OK del usuario: axe-core desde
  cdnjs, solo en la sesión local.
- F4: 375, 768, 1024 y 1440 px midiendo scroll horizontal y cortes; descarga
  del PDF en Chrome real (Claude in Chrome). Firefox y Safari no están al
  alcance de las herramientas: lista corta para que el usuario pruebe en su
  celular, si quiere.
- F5: tokens de `utils/styles.py` contra los estilos calculados; cada
  selector del MAINTENANCE MAP sigue encontrando elementos; tipografía y
  espaciado iguales entre páginas; el PDF con la misma paleta.
- F6: tiempos de carga de cada página, de cada ejemplo, de una recarga de
  resultados y del PDF; peso transferido.

**Etapa 4 — producción (F7, F6, T2).** Desde la dirección real (no
`/~/+/`): navegación, enlaces de ejemplo, Atrás; estáticos con bytes y tipo
reales; qué guarda el service worker y si podría servir una versión vieja
tras un push; título de pestaña; tiempos de despertar y primera carga; un PDF
interceptado sin guardar. T2: cómo se enteraría hoy el usuario de una caída y
el procedimiento de publicación y reinicio.

**Etapa 5 — consolidación (T1).** Documentos contra el código y entre sí,
carpeta sin sobrantes, `.gitignore`. Tabla única de hallazgos por severidad,
con una propuesta para cada uno: es la entrada del paso 3.

**Entregables.** Los hallazgos en esta sección; `ESTADO.md` al día al cerrar
cada etapa (por si la sesión se corta o el usuario cambia de equipo); un
resumen para el usuario al terminar la auditoría, antes de corregir nada.

#### Resultados de la etapa 0 — línea base (2026-10-08, LAPTOP-6N608GJL)

- **Incidente previo**: 23 copias en conflicto de Dropbox y 3 imágenes ya
  borradas del repo, subidas el 2026-10-07 por el otro equipo
  (DESKTOP-G2518C4) desde una foto vieja de la carpeta. Ninguna con trabajo
  nuevo (cada una rastreada en el historial de git); a la Papelera con OK del
  usuario. Nada dentro de `.git`; `git fsck` limpio. Detalle en CLAUDE.md
  ("Multi-machine setup"). Si no se hubiera visto, pytest habría corrido
  también la copia vieja de dos archivos de tests.
- **Git**: `main` = `origin/main` = `e06d8e1`; archivos versionados iguales a
  HEAD (solo cambia esta auditoría).
- **CI**: verde en `e06d8e1` (Python 3.12 y 3.14).
- **Suite**: 140 aprobados. Tardó 755 s porque corrió con medición de
  cobertura y con el procesador ocupado por otro proyecto del usuario (una
  simulación con 11 procesos); no sirve como medida de tiempo (lo normal son
  75-90 s). Los tests más lentos son los de AppTest y los que arman una
  optimización completa. 50 avisos de dos tipos: el `UserWarning` de
  PyPortfolioOpt al combinar `max_sharpe` con L2 (esperado, como en el
  cookbook) y un `PendingDeprecationWarning` de seaborn (`cmap.set_bad`) al
  dibujar el mapa de correlaciones del PDF → revisar en B6.
- **Cobertura de líneas**: 71 % en total. Bajas: `pages/1_Stocks.py` 16 %,
  `core/data_provider.py` 57 %, `utils/session_manager.py` 62 %,
  `utils/visualizations.py` 63 %. Altas: Portfolio 90 %, `pdf_generator` 89 %,
  inicio y About 100 % → revisar en B7.
- **Producción**: `/api/v2/app/status` devuelve `"status":12` con Streamlit
  1.59.2 y el endpoint de salud responde 400: la app estaba dormida. Se
  revisa en la etapa 4.
- **Pendiente para las etapas con tiempos (B4, F6)**: medir con el equipo
  libre.

#### Resultados de la etapa 1 — backend, revisión estática (2026-10-08)

Método: ruff y vulture sobre el código; `pip list --outdated`; dependencias
contra OSV; notas de versión de Streamlit 1.60-1.65 y límites de Community
Cloud (documentación oficial); dos agentes de solo lectura (manejo de errores
y seguridad) cuyos puntos se verificaron en el código antes de anotarlos;
mutaciones del PDF diferido en una copia del proyecto en el scratchpad; una
prueba de hilos de los gráficos del PDF (también en la copia). Ningún archivo
del proyecto se modificó.

**B1 — correctitud: sin hallazgos.** Paridad y congelados en verde (dentro de
los 140). Las decisiones abiertas (tasa 0 % frente a 3 % en Black-Litterman,
pesos que no son los de mercado) dicen lo mismo en About, la guía y CLAUDE.md.

| ID | Sev. | Hallazgo (verificado salvo que diga otra cosa) | Propuesta |
|---|---|---|---|
| B3-01 | 🟠 | Stocks: si falla la descarga del periodo elegido (1D, 5D, All…), `except Exception: pass` (`pages/1_Stocks.py:737`) deja los datos diarios de 1 año y los dibuja bajo la etiqueta del periodo nuevo, sin aviso ni registro. Pasa cuando Yahoo limita la segunda consulta | Avisar y no dibujar datos de otro periodo; registrar |
| B3-02 | 🟡 | Portfolio: una corrida que falla muestra el error y, debajo, los resultados completos de la corrida anterior (métricas, pestañas, PDF) (`pages/2_Portfolio.py:443-494`) | Borrar el resultado anterior o rotularlo "corrida anterior" |
| B3-03 | 🟡 | Mensajes crudos de PyPortfolioOpt al usuario: "The minimum volatility is 0.153. Please use a higher target_volatility" (fracción y nombre interno, el formulario usa %), una tupla de Python cuando falla el solver, y el titular "con un límite o una meta" también en objetivos sin meta (`2_Portfolio.py:486-487`) | Traducir en el motor a mensajes en % con el mínimo o máximo posible |
| B3-04 | 🟡 | Errores inesperados se registran sin traceback y llegan crudos al usuario ("The optimization failed: 'SPY'…") (`utils/optimizer_wrapper.py:395-405`) | `logger.exception` y mensaje genérico para errores no previstos |
| B3-05 | 🟡 | Falla la descarga de SPY → `ValueError` → rama genérica que pide "revisar tus datos" (los datos están bien) (`core/opt_engine.py:156`) | `DataDownloadError` con mensaje de reintento |
| B3-06 | 🟡 | El backtest del PDF exige 100 filas y el de la web 20: con 20-99 días comunes el PDF omite en silencio la página de rendimiento histórico, pero la portada sigue mostrando "Backtest Period" (`core/backtest.py:183`, `utils/visualizations.py:799`) | Una sola constante y una línea en el PDF si falta |
| B3-08 | 🟡 | Stocks: fallas de Yahoo en `.info` y en estados financieros se tragan y quedan en caché como "sin datos" (5-10 min; financieros hasta ~70 min); el tipo de activo cae a EQUITY y el texto dice "not available for this asset" (`core/data_provider.py:197-262, 357-403`) | No cachear fallas totales; distinguir "no se pudo cargar" de "no existe" |
| B3-10 | 🟡 | Errores del formulario que no bloquean Run: fechas invertidas (corre con toda la historia) y views con Low ≥ High (la view se descarta) (`2_Portfolio.py:174-177, 294-297`) | Incluirlos en `disabled` del botón |
| B3-07 | 🟢 | Si el PDF diferido falla, Streamlit muestra 5 s "Failed to generate file for download" bajo el botón, sin siguiente paso (leído en el código de Streamlit; se confirma en la etapa 3) | Secciones del PDF tolerantes a fallas y nota de reintento |
| B3-09 | 🟢 | Stocks: símbolo inválido y caída de red dan el mismo mensaje, con el texto crudo de la excepción (`1_Stocks.py:602-607`) | Mensaje con las dos causas; registrar |
| B3-12 | 🟢 | El PDF omite en silencio páginas cuyo gráfico o backtest falló; errores registrados sin traceback | Línea de reemplazo en el PDF |
| B3-13 | 🟢 | Web: errores del backtest y de correlaciones con texto crudo; si `prices_clean` no se puede leer, se descargan otros datos en silencio (`visualizations.py:902-912`) | Registrar y quitar la descarga de respaldo |
| B3-14 | 🟢 | `except: pass` sin registro en el aviso de solapamiento, la franja de retornos, ^GSPC y financieros de Stocks | `logger.warning(..., exc_info=True)` |
| B3-15/16/17 | 🟢 | Frontera de todo o nada sin decir por qué; presupuesto que no alcanza ni una acción sin explicación; mensaje de datos insuficientes que supone un rango de fechas | Textos específicos |
| B3-18 | 🟢 | Objetivo desconocido cae en `max_sharpe` con tasa 0 % (no se alcanza desde la UI) | Lanzar `OptimizationError` |
| B3-19 | 🟢 | `logging.basicConfig` solo en el inicio: si el proceso arranca por una subpágina, los registros INFO se pierden | Configurar en un módulo común |
| B3-11 | ⬜ | Sin verificar: un activo cuya historia termina antes recorta la ventana de todos sin aviso. Se prueba en la etapa 2 | — |
| B4-01 | 🟡 | Dos PDF armados a la vez dibujan sus gráficos con otro tamaño y composición: `pdf_shared` usa el estado global de `pyplot` (`plt.tight_layout()`) y el PDF ahora se arma en hilos. Prueba: el mismo gráfico dos veces seguidas da bytes idénticos; 96 de 96 armados en 8 hilos salieron distintos. En las muestras revisadas los datos eran correctos; cambiaba el tamaño | `fig.tight_layout()` / API orientada a objetos |
| B5-10 | 🟡 | urllib3 2.7.0 (llega con `requests`) tiene 3 avisos publicados el 2026-09-30, dos de severidad alta, corregidos en 2.8.0. Explotarlos exige un servidor malicioso o comprometido | Fijar `urllib3>=2.8.0` como se hizo con GitPython |
| B5-01 | 🟡 | Textos de Yahoo (nombre, sector, industria, familia del fondo, moneda) entran sin escapar al HTML de Stocks (`1_Stocks.py:623-676`); `_fmt_safe` devuelve el valor crudo si no puede formatearlo. Requiere controlar un campo de Yahoo | `html.escape` y moneda validada `^[A-Z]{3}$` |
| B5-03 | 🟢 | `client.showErrorDetails` no está fijado: por defecto "full", cualquier excepción no capturada muestra el traceback al visitante; los formateadores de Stocks pueden fallar con tipos inesperados de Yahoo | `showErrorDetails = "type"` o `"none"` |
| B5-02 | 🟢 | `server.enableCORS = false`: Streamlit avisa que lo cambia a `true` por XSRF, pero en 1.59.2 solo avisa (`config.py:2949-2965`); se acepta cualquier origen. Producción se mira en la etapa 4 | Quitar la línea y comprobar que la app conecta |
| B5-04 | 🟢 | Service worker y manifest sin efecto útil: alcance `…/app/static/`, guarda `/` (el shell de la plataforma), `start_url` da 404 | Quitarlos o corregirlos |
| B5-05 | 🟢 | `utils/ssl_fix.py`: en Linux (la nube) copia el bundle de certificados a una ruta relativa dentro del repo; nunca lo refresca; falla en silencio. Ya no hace falta (la carpeta no tiene acentos) | Aplicarlo solo si la ruta de certifi no es ASCII |
| B5-06/07/08/09 | 🟢 | Cachés de Stocks sin `max_entries` y en dos capas; texto del propio usuario en markdown (solo en su sesión); PyPortfolioOpt por tag de git sin hash y acciones de CI por versión mayor; `.gitignore` sin `.env` | Ajustes menores |
| B6-01 | 🟡 | Streamlit 1.59.2 → 1.65.0 disponible. Cambios que nos tocan: 1.63 ya no reparte controles en varias líneas dentro de `st.columns`; 1.60 rechaza mensajes de iframes inyectados (PWA); 1.64-1.65 cambian `at.expander` y `at.query_params` de AppTest | Tarea propia con el ritual de dependencias y el mapa de selectores |
| B6-02 | 🟢 | Otras versiones nuevas: yfinance 1.7.0, plotly 7.1.0 (mayor), pandas 3.0.6, numpy 2.5.3, cvxpy 1.9.3, fpdf2 2.8.9, matplotlib 3.11.2, scikit-learn 1.9.1, GitPython 3.2.0 | Decidir junto con B6-01 |
| B6-03 | 🟢 | `PendingDeprecationWarning` de seaborn (`cmap.set_bad`) en el mapa del PDF: viene de seaborn, no de nuestro código | Solo observar |
| B7-01 | 🟡 | Cobertura: `pages/1_Stocks.py` 16 % (sin test que dibuje un símbolo real; ahí viven B3-01 y B5-01), `core/data_provider.py` 57 % | Tests AppTest de Stocks con Yahoo simulado |
| B7-02 | ✅ | Mutaciones del PDF diferido: 2 de 2 detectadas (armarlo en cada recarga; no agregar el backtest) | — |
| B7-03 | ✅ | Suite corrida 3 veces seguidas: 140/140 en las tres (104 s, 76 s y 74 s); sin tests inestables | — |
| B8-01 | 🟢 | Código muerto confirmado (ningún uso, ni en tests): `download_and_run_backtest`, 4 propiedades de `BacktestResult`, `create_prior_chart`/`create_posterior_chart`, `_fmt_div_yield`, `_render_metric_card`, `create_risk_return_scatter`, `create_allocation_table`, `create_metrics_card_html`, 8 funciones de `session_manager`, `MAX_VIEW_THRESHOLD`, `HISTORICAL_PERIOD_YEARS` | Borrar |
| B8-02 | 🟢 | 14 imports sin uso (10 en la app, 4 en tests), variables desempaquetadas sin uso, docstrings viejos (`core/__init__.py` nombra `core.opt`, que no existe; `pdf_shared` dice "Black-Litterman Portfolio Reports"), un `if` cuyas dos ramas dan lo mismo (`pdf_shared.py:229-230`) | Limpiar |
| B8-03 | 🟢 | `datetime.now()` sin zona horaria: en la nube el servidor usa UTC (fechas por defecto, inicio de 5D, hora del PDF) | Evaluar; impacto mínimo |

#### Resultados de la etapa 2 — backend en marcha, local (2026-10-08)

Método: 8 corridas reales contra Yahoo con el wrapper de la app (script en el
scratchpad); la app local con tres sesiones a la vez (los tres ejemplos del
inicio) y dos PDF pedidos al mismo tiempo, interceptados sin guardar archivos.
El procesador seguía ocupado por la simulación del usuario: los tiempos son
indicativos, no medidas.

**Lo que salió bien (B2).** Símbolo inexistente (ZZZZZQ): 3 intentos y un
mensaje claro que nombra las dos causas posibles. Activo joven (RDDT), cripto
con acciones y oro, ETF de bonos: corren y activan sus notas (historia común
más corta, fines de semana). Black-Litterman obtuvo las capitalizaciones. 20
tickers con toda la historia: correcto, 12 activos con peso. Las tres sesiones
simultáneas no se mezclaron: cada pestaña mostró su ejemplo con las cifras de
la guía (17,35 % / 23,07 %; 7,71 % / 16,78 %; 8,38 % / 10,00 %). Los dos PDF
simultáneos: 200, `application/pdf`, unos 2 s cada uno, sin error.

| ID | Sev. | Hallazgo | Propuesta |
|---|---|---|---|
| B2-01 | 🟠 | **Ventanas cortas = contracción total sin aviso.** Con un rango de ~3 meses (63 días) la contracción de Ledoit-Wolf llega a 1,0: la covarianza queda como identidad escalada, "Lowest risk" reparte 33,3/33,3/33,3 y el mapa de correlaciones muestra todo en 0 (se dibuja desde la matriz contraída). Medido con AAPL, MSFT y KO: contracción 1,0 con 63 días, 0,30 con 250, 0,11 con 751. El mínimo permitido hoy es 20 días. Es correcto según el modelo, pero se muestra como un resultado sin explicar | Avisar cuando la contracción sea alta (o la ventana corta) y/o subir el mínimo; decisión del usuario |
| B3-06 | 🟡 | Confirmado en vivo: con ese rango corto el PDF sale sin backtest (`historical_data` vacío) mientras la web lo muestra | (ya listado) |
| B3-03 | 🟡 | Confirmado en vivo: límite de riesgo de 2 % con AAPL, MSFT y NVDA → "The minimum volatility is 0.287. Please use a higher target_volatility" | (ya listado) |
| B4-02 | 🟡 | Memoria: una corrida de 20 tickers con toda la historia asigna en su pico unos 86 MB (tracemalloc) y su resultado pesa 1,2 MB serializado en la sesión. El servidor local pasó de 170 a 325 MB de memoria en uso con tres corridas chicas a la vez. Community Cloud garantiza 690 MB y permite hasta 2,7 GB (su documentación, cifras "a febrero de 2024", sujetas a cambio): unas 6-8 corridas grandes simultáneas se acercan al mínimo garantizado | Considerar limitar el historial por defecto (p. ej. 10 años) o guardar menos en la sesión; decisión con B2-01 |
| B3-23 | 🟢 | Al abrir un ejemplo con límite de riesgo, Streamlit registra "The widget with key `target_volatility_pct` was created with a default value but also had its value set via the Session State API" (solo en el registro; la página no lo muestra) | No pasar `value=` cuando la clave ya está en la sesión |
| B3-11 | ⬜ | No se pudo probar en vivo (no hay un símbolo real cuya historia termine antes); queda como test unitario en el paso 4 si se decide | — |

#### Resultados de la etapa 3 — frontend en la app local (2026-10-08)

Método: axe-core 4.12.1 (reglas WCAG 2.0/2.1/2.2 A y AA, más
"best-practice") en el inicio, Portfolio con resultados, Stocks con AAPL y las
tres pestañas de About; recorrido con Tab midiendo el foco; anchos de 320, 375,
768, 1024 y 1440 px midiendo desbordes y alineación; selectores del MAINTENANCE
MAP contra el DOM real; peso de la página. Los tiempos locales no se midieron
(procesador ocupado); los de producción están en la etapa 4.

**Lo que salió bien.** WCAG 2.2 AA según axe: 0 violaciones en el inicio,
Portfolio con resultados y About; 1 en Stocks (F3-03). Hay reglas de foco
visible y `prefers-reduced-motion`. Sin scroll horizontal de página entre 320 y
1440 px (incluye el reflujo a 320 px que pide WCAG). Las cinco métricas quedan a
la misma altura entre 768 y 1440 px y apiladas en el celular. En el celular las
pestañas muestran una flecha y las tablas tienen su propio scroll. Todos los
selectores vigentes del MAINTENANCE MAP encuentran sus elementos en 1.59.

| ID | Sev. | Hallazgo | Propuesta |
|---|---|---|---|
| F3-01 | 🟡 | La primera parada del Tab en todas las páginas es el iframe invisible del PWA (16×1 px, `tabindex=0`, título "st.iframe"): un paso vacío para teclado y lectores de pantalla | Quitar el PWA (B5-04) o sacarlo del orden de foco |
| F3-02 | 🟡 | El anillo de foco es casi invisible: contorno azul al 35 % más sombra al 50 % (`--color-accent-ring`), unos 2:1 contra blanco; el mínimo usual para indicadores de foco es 3:1 | Contorno sólido `#2E6FC7` (4,99:1) |
| F3-03 | 🟡 | Stocks, franja de retornos: región con scroll horizontal que no se puede enfocar con teclado (axe "serious", WCAG 2.1.1) y con la barra oculta (`scrollbar-width: none`) | Que quepa sin scroll (dos filas en celular) o hacerla enfocable y visible |
| F4-01 | 🟡 | Esa misma franja a 375 px: las cifras chocan ("+30.02%+23.82%+30.4") y 5Y y All quedan fuera de la pantalla sin señal | Rejilla de 4×2 en pantallas angostas |
| F2-01 | 🟡 | Tickers solo se separan por comas: "AAPL MSFT" se lee como un símbolo y aparece "Enter at least 2 tickers." (`2_Portfolio.py:137`) | Separar también por espacios y punto y coma |
| F2-02 | 🟢 | Símbolos duplicados o mal escritos se detectan recién al presionar Run, con el mensaje genérico "The optimization failed: Duplicate tickers found…" | Avisar bajo el campo y bloquear Run |
| F3-04 | 🟢 | Buenas prácticas de axe: sin landmark `main` (estructura de Streamlit), saltos de nivel de encabezado (sección Report, About), contenido fuera de landmarks | Ajustar niveles de encabezado; lo demás es de Streamlit |
| F3-05 | 🟢 | Los gráficos de Plotly no tienen alternativa textual; en parte la cubren las tablas (asignación, detalles) y las métricas del backtest | Una línea de resumen bajo cada gráfico, si se quiere |
| F4-02 | 🟢 | En el celular sobra espacio vacío alrededor de la dona; el enlace "Source on GitHub" del pie mide 22 px de alto (la regla del rediseño pide 44 px táctiles) | Ajustar alturas |
| F5-01 | 🟢 | Cuatro selectores del MAINTENANCE MAP ya no encuentran nada en 1.59 (`stSidebar`, `collapsedControl`, `stToolbar`, `stSidebarNav`): CSS sin efecto | Quitar o anotar |

**F1 — exactitud de lo mostrado** (un agente de solo lectura contrastó cada
texto con el código; los puntos marcados se verificaron a mano). Lo que está
bien: etiquetas y ayudas de objetivos, views y ajustes avanzados; métricas,
caja de notas, pestañas y sus leyendas; unidades de Stocks; el inicio (las
cifras 9,46 % / 14,00 % / 0,461 coinciden con `assets/example_portfolio.json`);
About; el README (140 tests = 133 funciones + 7 casos parametrizados) y los
números repetidos en textos, que coinciden con `core/constants.py`.

| ID | Sev. | Hallazgo | Propuesta |
|---|---|---|---|
| F1-02 | ⏸ | Decisión abierta desde la Fase 6, ahora con su efecto medido en texto: un portafolio solo de cripto (≈365 filas por año) se anualiza con 252, así que la volatilidad sale ~17 % baja (×√(252/365)) y un límite de riesgo de 20 % admite ~24 % real; el backtest, sin fines de semana, no coincide con la tarjeta. Nada lo avisa | Decidir: `frequency=365` en ese caso (rompe paridad con el cookbook en ese caso) o una nota |
| F1-01 | 🟡 | Verificado. El PDF redondea la meta a entero (`pdf_shared.py:268-269`, `:.0%`): un límite de 12,5 % se lee "at most 12%", y una meta de 7,5 % "at least 8%"; el detalle del mismo PDF y la web dicen 12.5% | Formato `:g` como `goal_text` |
| F1-03 | 🟡 | Verificado. Privacidad: el registro INFO "Allocated %d positions, $%.2f invested, $%.2f remaining" (`opt_engine.py:525-526`) deja el presupuesto en los registros de la plataforma, contra la intención del comentario de la línea 489; también quedan tickers en mensajes de error y reintentos. About y el README dicen que la app no guarda entradas | Bajar a DEBUG o quitar montos; o precisar el texto |
| F1-04 | 🟡 | Verificado. Stocks "5D": el gráfico parte 5 días corridos atrás (`1_Stocks.py:704`, casi siempre 4 días hábiles) y la franja de retornos usa una semana (`:168`, 5 días hábiles): mismo rótulo, distintos lapsos | Partir 7 días atrás o tomar las últimas 5 sesiones |
| F1-05 | 🟡 | Verificado. Precios bajo un centavo (p. ej. SHIB-USD) se muestran 0.00 en Stocks, en el detalle de asignación y en el PDF (formato `.2f`) | Dígitos significativos si el precio < 1 |
| F1-06 | 🟢 | La leyenda de Correlation dice "the shrunk covariance matrix the optimizer uses"; con views de Black-Litterman el optimizador usa la del posterior y el mapa muestra la del prior (el PDF lo dice bien) | Usar la frase del PDF |
| F1-07 | 🟢 | Con gamma 0, el PDF de Black-Litterman igual describe "an L2 penalty (gamma = 0.0)" | Rama "sin penalización" como en Markowitz |
| F1-08 | 🟢 | El aviso de activos no accionarios culpa a CAPM y a Black-Litterman aunque se use Markowitz con media histórica | Ajustar el texto según el caso |
| F1-09 | ⏸ | Ligado a la decisión de la tasa 0 % / 3 %: Detalles y PDF muestran "Risk-free rate: 3%" en Black-Litterman, pero el prior usa 0 % | Precisarlo en el texto mientras no se decida |
| F1-10 | 🟢 | "Price data (dates with a price for every asset…)": en Black-Litterman la aversión al riesgo usa toda la historia de SPY | Una cláusula más |
| F1-11 | ⬜ | Sin verificar: "Shares are bought at each asset's close on {fecha}" podría ser el precio intradía si se corre con el mercado abierto | Probar en horario de mercado |
| F1-12 | 🟢 | La nota del método greedy dice que el solver exacto "no estaba disponible"; también corre cuando el exacto falla o no encuentra nada | "could not be used" |
| F1-13/14/15 | 🟢 | "Forward Dividend & Yield" puede mostrar el rendimiento pasado; volúmenes bajo 1 M con decimales; fechas de Stocks en la zona horaria del servidor | Ajustes menores |
| F1-16/17/18 | 🟢 | Web y PDF nombran distinto lo mismo (Budget / Portfolio Value / Total Value, Low/High / Lower/Upper…); el PDF dice "returned X%" para retornos anualizados; Sortino, Calmar, caída máxima, prior/posterior, Ledoit-Wolf y CAPM se muestran sin definición en el glosario | Un solo vocabulario; "a year"; ampliar el glosario |

#### Resultados de la etapa 4 — producción (2026-10-08, `e06d8e1`)

Lo que salió bien: la app estaba dormida y respondió `ok` unos 62 s después
de despertarla; desde la dirección real el enlace de ejemplo Big Tech llenó
el formulario (~6 s), Run tardó 14 s y dio 17,36 % / 23,07 % / 0,622, como en
local; el PDF salió en 2,4 s (200, `application/pdf`, 257 KB, interceptado sin
guardar); el logo carga como imagen real (526×200); About abre en `/About`
sin anidar marcos. CORS: con un origen ajeno, el endpoint de salud de
producción no devuelve `Access-Control-Allow-Origin` (en local sí: `*`), así
que B5-02 no se nota en producción.

| ID | Sev. | Hallazgo | Propuesta |
|---|---|---|---|
| F6-01 | 🟡 | La primera visita al inicio descarga ~7,8 MB sin comprimir (81 pedidos); 4,6 MB son el paquete de Plotly, que se carga solo para los dos gráficos de ejemplo. Streamlit 1.59 deja los estáticos sin gzip a propósito (`starlette_app.py:224-229`); quedan en caché un año (`immutable`). Pesa sobre todo en celulares | Decisión: imágenes estáticas generadas con las mismas funciones (es "figura real") o dejarlo |
| B5-04 | 🟢 | Confirmado en producción: el service worker está activo con alcance `/~/+/app/static/` y no controla la página (`controller` vacío) | (ya listado) |
| F7-01 | 🟢 | La pestaña del navegador queda sin título en producción aun navegando dentro de la app (la app fija "About · PortfolioLab" en su marco). El 2026-09-26 la navegación interna sí lo mostraba: cambió del lado de la plataforma | Solo documentar |
| T2-01 | 🟡 | Operación: nada avisa si la app se cae o un push la deja con `ImportError` hasta el reinicio; la app duerme tras 12 h sin tráfico (documentación) y el primer visitante espera ~1 min. Hoy solo se nota entrando | Procedimiento: revisar salud después de cada push; opcional, un monitor externo gratuito (decisión del usuario) |

#### Etapa 5 — consolidación (entrada del paso 3)

**T1 — documentación y orden.** Carpeta limpia (solo cambia este archivo; lo
ignorado es lo de siempre). CLAUDE.md, README y About coinciden con el código
en lo revisado; los textos viejos están en B8-02 (docstrings) y F1-03
(privacidad).

**Totales.** 0 🔴 · 2 🟠 · 24 🟡 · unos 40 🟢 (contando por separado los que
comparten fila) · 2 ⏸ (decisiones ya abiertas) · 2 ⬜ sin verificar (B3-11,
F1-11). Ningún hallazgo toca la paridad ni los snapshots congelados:
el motor coincide con PyPortfolioOpt.

**Los dos 🟠.** B3-01 (Stocks dibuja datos de otro periodo si Yahoo falla) y
B2-01 (ventanas cortas: contracción total, pesos iguales y correlaciones en 0
sin aviso).

**Agrupación propuesta para el paso 3** (cada paquete es un cambio coherente
con sus tests):

| Paquete | Hallazgos |
|---|---|
| A. Errores y mensajes | B3-01, B3-02, B3-03, B3-04, B3-05, B3-08, B3-09, B3-10, B3-12 a B3-19, F2-01, F2-02, F1-12 |
| B. PDF | B3-06, B3-07, B4-01, F1-01, F1-07, F1-16, F1-17 |
| C. Stocks: franja y formatos | F3-03, F4-01, F1-04, F1-05, F1-13, F1-14, F1-15 |
| D. Accesibilidad y PWA | F3-01, F3-02, B5-04, F3-04, F3-05, F4-02, F5-01 |
| E. Seguridad y dependencias | B5-10 (urllib3), B5-01, B5-03, B5-02, B5-05, B5-06 a B5-09 |
| F. Privacidad y textos | F1-03, F1-06, F1-08, F1-10, F1-18 |
| G. Limpieza de código | B8-01, B8-02, B8-03, B3-23 |
| H. Tests | B7-01 y un test por cada arreglo |

**Decisiones para el usuario:** B2-01 (cómo tratar ventanas cortas), F1-02
(cripto con 365 días), F1-09 (tasa 0 % / 3 % en Black-Litterman, ya abierta),
F6-01 (imágenes estáticas en el inicio), B4-02 (limitar la historia por
defecto), B6-01 (actualizar Streamlit ahora o aparte), T2-01 (monitor externo),
B5-04 (quitar el PWA).

#### Paso 3 — decisiones y plan de arreglos (aprobado por el usuario el 2026-10-08)

**Decisiones del usuario** (aceptó las recomendaciones tal cual):

| # | Decisión | Por qué |
|---|---|---|
| B2-01 | Avisar (caja de notas y PDF) cuando la contracción de Ledoit-Wolf sea alta (≥ 0,5), explicando que con pocos datos el modelo supone riesgos iguales y correlaciones cercanas a 0. El mínimo de 20 días no cambia | No cambia cifras ni paridad, y enseña cómo se comporta el modelo; subir el mínimo bloquearía pruebas legítimas |
| F1-02 | Anualizar con 365 cuando todos los activos cotizan todos los días (detectado en los datos, ~365 filas por año); las mezclas siguen con 252 | La tarjeta dice "anual" y la cifra estaba ~17 % baja; `frequency` es un parámetro de PyPortfolioOpt, así que el motor sigue igual a la librería llamada con ese valor |
| F1-09 | El modelo no cambia (decisión del 2026-09-27); solo se corrige el texto: "3% (optimizer); 0% in the market-implied prior" | El texto decía 3 % sin más |
| F6-01 | Dejar Plotly en el inicio por ahora | Las imágenes exigirían kaleido (con Chrome) y un paso de regeneración; abrir cualquier herramienta descarga Plotly igual; la espera mayor es despertar la app. Se retoma si hay quejas en celular |
| B4-02 | Sin cambios | Alcanza para el tráfico actual; se revisa si crece |
| B6-01 | Actualizar Streamlit como tarea aparte, después de publicar estos arreglos | Separar causas si algo se ve distinto; el pin de urllib3 sí va ahora |
| B5-04 | Quitar el PWA (`sw.js`, `manifest.json`, la inyección) | No funciona dentro del marco de Streamlit Cloud y su iframe es la primera parada del Tab (F3-01). Los service workers ya registrados son inofensivos (solo cubren la carpeta estática, red primero) |
| T2-01 | Procedimiento después de cada push en CLAUDE.md, sin monitor externo | Un monitor daría falsas alarmas cada vez que la app duerme (12 h sin visitas) |

**Orden de trabajo** (un commit por paquete, en `main` local; se publica en el
paso 5 con permiso; después hará falta reiniciar la app porque se tocan
`utils/` y `core/`):

1. **E. Seguridad y dependencias**: fijar `urllib3>=2.8.0` (B5-10); escapar
   los textos de Yahoo y validar la moneda (B5-01, incl. `_fmt_safe`);
   `client.showErrorDetails = "type"` y formateadores de Stocks que no se caen
   (B5-03); quitar `enableCORS = false` y comprobar que la app conecta (B5-02);
   `ssl_fix` solo si la ruta de certifi no es ASCII, con registro (B5-05);
   `max_entries` en las cachés de Stocks (B5-06); escapar el texto propio del
   usuario en markdown (B5-07); `.gitignore` con `.env` (B5-09).
2. **D. Accesibilidad y PWA**: quitar el PWA (B5-04, F3-01); anillo de foco
   sólido `#2E6FC7` (F3-02); niveles de encabezado (F3-04); objetivo táctil
   del pie (F4-02); selectores muertos del MAINTENANCE MAP (F5-01).
3. **A. Errores y mensajes** (incluye el 🟠 B3-01): Stocks no dibuja datos de
   otro periodo; el resultado anterior se borra al fallar; mensajes del motor
   en % con el mínimo o máximo posible; errores inesperados con traceback en
   el registro y mensaje genérico; SPY como `DataDownloadError`; fallas de
   Yahoo en Stocks que no se guardan en caché como "sin datos"; fechas y views
   inválidas bloquean Run; tickers separados también por espacios; duplicados
   avisados antes de Run; `logging` configurado en un módulo común; y los 🟢
   B3-09, B3-12 a B3-19, B3-23, F1-12.
4. **C. Stocks**: franja de retornos sin choques ni scroll oculto (F3-03,
   F4-01); 5D de 5 sesiones (F1-04); precios bajo un centavo (F1-05);
   rótulo del rendimiento por dividendo, volúmenes sin decimales (F1-13,
   F1-14).
5. **B. PDF**: una sola constante de filas mínimas para el backtest y una línea
   cuando falta (B3-06, B3-12); gráficos con la API orientada a objetos de
   matplotlib (B4-01); meta con `:g` (F1-01); gamma 0 en Black-Litterman
   (F1-07); vocabulario igual a la web (F1-16); "a year" en el análisis
   comparativo (F1-17); secciones que toleran fallas (B3-07).
6. **Decisiones de modelo y textos (F)**: aviso de contracción (B2-01);
   cripto con 365 (F1-02); texto de la tasa (F1-09); privacidad del registro
   (F1-03); leyenda de correlaciones (F1-06); aviso de no acciones (F1-08);
   ventana de Black-Litterman (F1-10); glosario ampliado con Sortino, Calmar,
   caída máxima, prior/posterior, Ledoit-Wolf y CAPM (F1-18); nota si un activo
   deja de cotizar antes (B3-11, con test).
7. **G. Limpieza**: código muerto (B8-01), imports y docstrings (B8-02).
8. **H. Tests**: cada arreglo lleva un test que falla sin él (se comprueba
   deshaciendo el arreglo, como en las fases anteriores); tests AppTest de Stocks
   con Yahoo simulado (B7-01).
9. **Documentos**: CLAUDE.md (decisiones, procedimiento después de cada push,
   T2-01), README si cambia algo público, la guía manual si cambia alguna cifra
   de referencia, y esta auditoría.

**Descartados, con motivo:** B8-03 y F1-15 (zona horaria: en la nube el
servidor usa UTC, que es lo correcto; impacto mínimo); F3-05 (texto alternativo
de Plotly: lo cubren en parte las tablas y métricas; se reevalúa con la
actualización de Streamlit); el landmark `main` de F3-04 (lo arma Streamlit);
B5-08 (fijar acciones de CI por hash es desproporcionado para este repo; el
tag de PyPortfolioOpt se deja como está, ya documentado); B6-02 y B6-03 (van con
la actualización de Streamlit); F7-01 (lo causa la plataforma; solo se
documenta). F1-11 (¿precio intradía?) se verifica corriendo con el mercado de
EE. UU. abierto antes de decidir.

#### Paso 4 — avance

| Paquete | Commit | Tests | Verificación |
|---|---|---|---|
| E. Seguridad y dependencias | `2c18752` | 140 → 149; 9 mutaciones detectadas (9/9) | App local: SAP.DE muestra nombre, sector y EUR; la app conecta sin CORS abierto y la salud ya no devuelve `Access-Control-Allow-Origin: *`; el aviso de CORS desapareció del registro |
| A. Errores y mensajes | `2ad7d12` | 153 → 173; 18/18 | App local: límite de riesgo de 1 % tras una corrida buena muestra "The risk limit of 1% is below the lowest risk these assets allow (5.2%)…", sin métricas ni PDF de la corrida anterior; el registro ya no trae el aviso del widget; Stocks con MSFT y 5D sin avisos. El test de casos borde atrapó un error propio (el patrón tomaba el punto final de "0.167.") |
| Contraste (verificación final) | `61735ee` | 209 → 212; 3/3 | axe, ya sin las violaciones anteriores, mostró tres de contraste que antes no reportaba: leyendas `st.caption` (Streamlit las dibuja con opacidad 0,6: 3,3:1), el enlace activo del menú (4,3:1) y las ganancias en verde de Stocks (3,1:1). Corregidas: 0 violaciones WCAG 2.2 AA en Inicio, Stocks (3 pestañas con AAPL), Portfolio (5 pestañas con resultados) y About |
| G. Limpieza | `effdd6b` | 214 → 209 (6 tests de código borrado, 1 nuevo) | vulture al 60 % ya solo da falsos positivos; ruff (pyflakes) pasa. De paso, el backtest del PDF tenía la misma descarga silenciosa que la web (B3-13): quitada. `session_manager` guardaba hasta 10 copias del resultado por visitante sin leerlas (memoria, B4-02): quitado |
| F. Decisiones de modelo y textos | `c186b2f` | 202 → 214; 15/15 (un test se reforzó: "Lowest risk" no mira el retorno esperado, así que no veía la anualización de la media histórica) | Datos reales: BTC + ETH con 365 días; AAPL, MSFT y KO con 3 meses dan contracción 1,00 (nota visible) y con toda la historia 0,01. Paridad y congelados intactos; la guía manual no tiene escenarios con cripto, así que sus cifras no cambian |
| B. PDF | `5354ae6` | 191 → 202; 14/14 (un test se reforzó: el fixture solo pasaba por una de las tres redacciones de la comparación) | Dos informes con datos reales leídos página por página (Markowitz con límite de 12,5 %, Black-Litterman con gamma 0 y una view): vocabulario de la web, meta "of 12.5%", "a year", tabla Low/High. Ajuste al leerlos: la portada decía "Price Data"/"Backtest Period" en mayúsculas, distinto del desglose |
| C. Stocks | `d3a3aff` | 173 → 191; 8/8 | App local a 375 px: la franja en 4×2 sin cortes; a 1440 px una fila de 8. SHIB-USD muestra 0.000005290 y sus rangos con dígitos. Hallazgos nuevos al verificar: "All +265132.05%" se partía en el celular (ahora "+265,132%") y SHIB-USD mostraba "All +inf%" porque Yahoo trae 217 cierres en 0 al inicio (ahora se ignoran). Cobertura de `pages/1_Stocks.py`: 16 % → 78 % (B7-01) |
| D. Accesibilidad y PWA | `aa3bccb` | 149 → 153; 5/5 | axe-core en Portfolio con resultados (3 pestañas) y About: 0 violaciones WCAG y sin `heading-order`; sin iframes; los encabezados conservan 24 px. Hallazgo nuevo al verificar: el panel de pestañas y `section[data-testid="stMain"]` (la primera parada del Tab, de Streamlit) tomaban el foco sin mostrarlo; ahora llevan el anillo |

**Verificación final del paso 4 (2026-10-08).** Suite: 212 aprobados; paridad
y congelados sin tocar. Casos reales de la etapa 2 repetidos: el rango corto
ahora trae backtest en el PDF y el límite imposible responde en porcentaje
("lowest risk these assets allow (28.7%)"); los demás, con las mismas cifras.
Dos PDF reales (Markowitz con límite de 12,5 %, Black-Litterman con gamma 0 y
una view) leídos página por página. axe: 0 violaciones WCAG 2.2 AA en las
cuatro páginas; sin scroll horizontal a 320 px. La guía manual suma el
escenario 8 (los avisos nuevos); sus cifras de referencia no cambian: el
motor solo cambió para portafolios que cotizan todos los días, y la guía no
tiene ninguno.

**Estado de los hallazgos tras el paso 4.** Corregidos (✅): el 🟠 B3-01 y
B2-01 (como aviso, por decisión del usuario); B3-02 a B3-19, B3-23 (B3-11
con una nota y su test, sin caso real con que probarlo en vivo); B4-01, B4-02 (en lo que cabía: sin historial de resultados en la
sesión); B5-01 a B5-07, B5-09, B5-10; B7-01 (Stocks 16 % → 78 % de
cobertura); B8-01, B8-02; F1-01 a F1-10, F1-12 a F1-14, F1-16 a F1-18; F2-01,
F2-02; F3-01 a F3-03 y la parte de encabezados de F3-04; F4-01, F4-02;
F5-01 (anotados, se conservan como resguardo); T2-01 (procedimiento en
CLAUDE.md). Decisión del usuario (⏸): F1-09 se aclara en el texto; alinear
las tasas sigue abierto. Pendiente de verificar (⬜): F1-11 (precio intradía
con el mercado abierto; esta corrida fue con el mercado cerrado). Descartados
(➖) con su motivo en el paso 3: B5-08, B6-02, B6-03, B8-03, F1-15, F3-05, el
landmark de F3-04, F6-01 (decisión), F7-01. Aparte: la actualización de
Streamlit (B6-01), por decisión del usuario.

**Verificación al cerrar el paso 4:** suite completa (paridad y congelados sin
tocar; el fixture sintético no debe activar la regla de 365 días); los casos
reales de la etapa 2 otra vez; axe-core y anchos de 320 a 1440 px en la app
local; un PDF por modelo leído página por página; los escenarios de la guía
manual si el motor cambió en algo que los toque.

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

Actualización 2026-09-26 (Fase 6): coherencia de lo que se muestra (inicio,
herramientas, PDF, README) y estimación sobre la ventana común. Suite:
110 → 129 tests; publicado y verificado en producción en `fa06a10`. Quedan
tres decisiones de modelo para el usuario (ver Fase 6).

Actualización 2026-09-27 (Fase 7): rediseño más simple y claro, guiado por la
skill ui-ux-pro-max. Suite: 130 → 137 tests (136 del rediseño y 1 del orden de
los botones de la portada). Publicado en `b6d88e9` y verificado en producción,
incluida la guía manual repetida con cifras idénticas.
