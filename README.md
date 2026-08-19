# Baloto Stats

App estadística y generador de combinaciones para **Baloto** (Colombia), con la misma
arquitectura y diseño que [MiLoto](https://github.com/carloshb31/miloto): app 100% estática
(HTML/JS, sin backend), datos en `data.json` actualizados por un scraper en Python vía
GitHub Actions, y las selecciones/aprendizaje del usuario guardados en `localStorage`
del navegador.

**Diferencias con MiLoto** (todo lo demás es idéntico):
- Reglas del juego: **5 números (1–43) + 1 superbalota (1–16)**, no solo 5 números (1–39).
- Días de sorteo: **lunes, miércoles y sábado** (no lunes/martes/jueves/viernes).
- Fuente de datos: `baloto.com/resultados` (no `baloto.com/miloto/resultados`).
- Cada estrategia del generador ahora también elige una superbalota (con la misma lógica
  de pesos: caliente = más frecuente, fría = menos frecuente, etc.).
- `estadisticas.html` agrega una sección dedicada a la superbalota (mapa de calor 1–16
  y ranking de frecuencia).

## Archivos

```
baloto/
├── index.html          # Generador (5 estrategias), Mis selecciones, Ranking, mini-stats
├── estadisticas.html    # Página de estadísticas completa (heatmaps, tendencias, pares, etc.)
├── data.json             # Histórico de sorteos (actualizado automáticamente)
├── scraper.py            # Scraper de baloto.com/resultados -> data.json
├── requirements.txt
└── .github/workflows/actualizar.yml   # Corre el scraper lun/mié/sáb tras cada sorteo
```

## Uso local

```bash
pip install -r requirements.txt
python scraper.py          # trae/actualiza data.json
python -m http.server 8000 # sirve la app localmente
# abrir http://localhost:8000
```

## Publicar en GitHub Pages

```bash
git init && git add . && git commit -m "Baloto Stats: versión inicial"
git branch -M main
git remote add origin https://github.com/carloshb31/baloto.git
git push -u origin main
```

Luego, en **Settings → Pages**, selecciona la rama `main` y carpeta raíz (`/`).

## Nota

Proyecto personal con fines estadísticos y de entretenimiento. Los sorteos son
independientes entre sí; el histórico no predice resultados futuros.
P(5+1) = 1/15,401,568. Juega con responsabilidad.
