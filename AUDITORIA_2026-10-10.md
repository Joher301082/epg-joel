# Auditoría de cobertura EPG: 10 de octubre de 2026

## Datos comprobados

- Inventario original conservado: **6066** entradas (archivo de conciliación).
- Entradas del inventario que consume actualmente el generador: **6202** según `coverage.json` del 10-10-2026 a las 05:09, hora de Venezuela. Diferencia sin conciliar: **+136**.
- Original: **5423** entradas sin `tvg-id` y **15** sin nombre; **223** filas tienen nombre repetido dentro de su grupo.
- Reporte actual: **3125** entradas mapeadas a fuentes, **3077** sin mapa; **2923** identificadores distintos mapeados, pero solo **1629** identificadores con alguna programación. **68541** filas de programación reportadas.
- No se puede calcular el número exacto de las 6066 señales originales que tienen guía correcta: falta cotejo fila a fila y verificación de señal, variante y horario. **Mapeado no significa verificado**.

## Grupos y riesgos concretos

- **CBS (REGIONALES): 114** entradas originales. La afiliada local debe coincidir con ciudad y distintivo, por ejemplo WIAT (Birmingham) frente a KPHO (Phoenix). No usar una EPG genérica de CBS para todas.
- **NBC: 50** entradas y **FOX NEWS: 100** entradas originales. Los grupos contienen afiliadas regionales identificadas por distintivos como WFLA, KSDK, WBRC y KSWB; no son feeds intercambiables.
- **NFL/NCAAF: 188** y **VIX+/DAZN: 119** entradas originales. Muchos nombres incluyen eventos y fechas de septiembre; no son horarios futuros comprobados y no deben convertirse automáticamente en EPG.
- Faltantes reportados por el generador: adultos 403, EX-JU 339, NFL/NCAAF 188, Francia 168, Alemania 165, España 161, EE. UU. cine/entretenimiento 155, Rumania 142, Portugal 133 y Países Bajos 125. Son **entradas sin mapa**, no canales verificados como ausentes de todas las fuentes.

## Fuentes y controles

- Fuente de catálogo usada: `iptv-org/epg` (ficheros `*.channels.xml`); en el generador figuran también como prioridades `gatotv.com`, `mi.tv`, `epgshare01.online`, `tv.movistar.co` y otras. Su aparición en el código **no prueba** que una señal concreta esté verificada.
- El generador actual pide **30 días** y corta a 30 días, pese al nombre `EPG_Joel_36h.xml` y a `window_hours: 36` del informe anterior. Debe corregirse la discrepancia antes de publicar una nueva versión.
- El flujo `.github/workflows/update-epg.yml` contiene una validación que **bloquea intencionalmente la publicación** hasta contar con comprobación individual. La última ejecución de cambio de código falló por ese bloqueo; la EPG pública existente no debe considerarse recién verificada.
- Se añadió `audit_epg.py` para revisar localmente estructura XMLTV, canales con programación, duplicados, fechas, discrepancias de recuentos y conciliación de inventario. Se probó con un XMLTV sintético; **no se ejecutó sobre el XML completo de 35 MB** en esta revisión.

## Pendiente

1. Obtener el inventario vigente de 6202 entradas y reconciliarlo fila a fila con las 6066 originales.
2. Verificar las variantes locales por distintivo, país y señal, especialmente CBS, NBC y FOX.
3. Confirmar en fuente pública cada programación antes de añadirla. No deducir títulos ni horas a partir del nombre de eventos.
4. Corregir el horizonte real de la guía, comprobar duplicados y ejecutar auditoría del XML publicado.
5. Mantener el bloqueo de publicación hasta que los controles sean verificables.
