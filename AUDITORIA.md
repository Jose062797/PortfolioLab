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
