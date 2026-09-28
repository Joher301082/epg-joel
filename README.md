# epg-joel

EPG personalizada para la lista IPTV original.

## URL fija de la guía

Cuando termine correctamente la primera ejecución:

`https://raw.githubusercontent.com/Joher301082/epg-joel/main/EPG_Joel_36h.xml`

## Qué hace

- Revisa toda la televisión en vivo de la lista IPTV.
- Excluye películas y series VOD.
- Usa `iptv-org/epg` como índice y motor de fuentes.
- No confía ciegamente en los `tvg-id` del proveedor.
- Prioriza coincidencias por país/feed.
- Genera solo las próximas 36 horas.
- Convierte horarios a `America/Caracas` (UTC-4).
- Se ejecuta cada 6 horas.
- Publica `coverage.json` con la cobertura obtenida.

## Seguridad

La URL privada de la lista IPTV no se guarda en el repositorio.
Debe configurarse como secreto de GitHub Actions con el nombre:

`IPTV_M3U_URL`
