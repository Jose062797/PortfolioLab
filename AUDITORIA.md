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

- ⬜ D2.1 Ticker inexistente / deslistado a mitad de rango / historiales desiguales.
- ⬜ D2.2 Fallback de market cap a $1e9: hacerlo visible en la UI (hoy es silencioso
  y distorsiona los priors de Black-Litterman).
- ⬜ D2.3 Confirmar precios ajustados (splits/dividendos) en todos los caminos.
- ⬜ D2.4 Validación del formato yfinance 1.5.x (salto desde 0.2.x sin revisión).

## Dimensión 3: Compatibilidad y deuda de dependencias 🟠

- ✅ D3.1 URGENTE: migrar `st.components.v1.html` → `st.iframe` (eliminación
  anunciada para después del 2026-06-01 — fecha ya vencida).
- ⬜ D3.2 Pinning exacto en requirements.txt + política de actualización deliberada.
- ⬜ D3.3 Test de humo de PyPortfolioOpt 1.5.6 sobre pandas 3.

## Dimensión 4: Calidad del testing 🟠

- ⬜ D4.1 Tests para módulos sin cobertura: pdf_generator/pdf_shared,
  visualizations, session_manager.
- ⬜ D4.2 Auditoría de calidad de tests existentes (verificación por mutación
  de 4-5 puntos clave del motor).
- ⬜ D4.3 Tests de regresión con valores numéricos congelados (seed fijo).

## Dimensión 5: Robustez y manejo de errores 🟡

- ⬜ D5.1 Todo error termina en mensaje claro en la UI (nunca traceback).
- ⬜ D5.2 Fallbacks comunicados al usuario, no solo al log.
- ⬜ D5.3 Entradas absurdas en tickers rechazadas con gracia.

## Dimensión 6: Rendimiento y UX 🟡

- ⬜ D6.1 Decisión consciente sobre caching (st.cache_data con TTL vs frescura).
- ⬜ D6.2 Peso del home (~1.5 MB de imágenes base64 inline); objetivo < 3s en frío.
- ⬜ D6.3 Responsividad móvil del CSS de styles.py.

## Dimensión 7: Seguridad 🟡

- ⬜ D7.1 Auditar todos los `unsafe_allow_html` (ninguna entrada de usuario → HTML).
- ⬜ D7.2 `pip-audit` de dependencias.
- ⬜ D7.3 Sin secretos en historial de git; secrets.toml fuera del repo.

## Dimensión 8: Mantenibilidad y documentación 🟢

- ⬜ D8.1 Evaluar partición de styles.py y documentar selectores de Streamlit atacados.
- ⬜ D8.2 Docstrings y CLAUDE.md 100% consistentes con la realidad.
- ⬜ D8.3 Disclaimer educativo visible en web y PDF.

## Fases

| Fase | Ítems | Estado |
|------|-------|--------|
| 1 | D3.1 + Dimensión 1 completa | ✅ 2026-07-16 |
| 2 | Dimensiones 2 y 4 | ⬜ |
| 3 | Dimensiones 5, 6 y 7 | ⬜ |
| 4 | Dimensión 8 + re-verificación final | ⬜ |

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
