#!/usr/bin/env python3
"""
Baloto Stats Scraper
Extrae resultados históricos de https://baloto.com/resultados y los guarda
en data.json con la MISMA estructura que usa la app (heredada de MiLoto):

{
  "sorteos": [ {"id": 1, "fecha": "2026-07-20", "nums": [3,22,23,25,37], "sb": 1}, ... ],
  "updated": "2026-08-14 10:00:00",
  "total": N
}

Reglas de Baloto: 5 números principales (1-43) + 1 superbalota (1-16).

Nota: baloto.com/resultados incluye también sorteos del formato ANTERIOR
(6 números del 1 al 45, sin superbalota, vigente hasta ~2022). Este scraper
valida el rango de cada resultado y descarta automáticamente cualquier fila
que no cumpla el formato actual (5 números 1-43 + superbalota 1-16), así
que el histórico completo se puede escanear sin riesgo de mezclar formatos.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://baloto.com/resultados"
REQUEST_DELAY_SECONDS = 1.0  # pausa entre páginas para no saturar el sitio

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-CO,es;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

DATA_FILE = Path('data.json')


def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {'sorteos': [], 'updated': '', 'total': 0}


def parse_date(text):
    m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', text, re.IGNORECASE)
    if not m:
        return None
    day = int(m.group(1))
    month = MESES.get(m.group(2).lower())
    year = int(m.group(3))
    if not month:
        return None
    return f'{year}-{month:02d}-{day:02d}'


def fetch_page(page):
    url = BASE_URL if page == 1 else f'{BASE_URL}?page={page}'
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def get_last_page(first_page_html):
    soup = BeautifulSoup(first_page_html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    m = re.search(r'Página \d+ de (\d+)', text)
    return int(m.group(1)) if m else 1


def parse_page(html):
    """Devuelve resultados SOLO de sorteos de BALOTO en formato actual
    (5 números 1-43 + superbalota 1-16). Descarta Revancha/ColorLoto y
    cualquier fila del formato anterior (6 números 1-45)."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for row in soup.select('table tr'):
        link = row.select_one('a[href*="resultados-baloto/"]')
        if not link:
            continue
        row_text = row.get_text(' ', strip=True)

        fecha_match = re.search(r'\d{1,2} de \w+ de \d{4}', row_text)
        fecha = parse_date(fecha_match.group(0)) if fecha_match else None

        nums_match = re.search(
            r'(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})',
            row_text,
        )
        if not (fecha and nums_match):
            continue

        n = [int(x) for x in nums_match.groups()]
        principales = sorted(n[:5])
        superbalota = n[5]

        # Filtra automáticamente sorteos del formato anterior (1-45, sin superbalota real)
        if len(principales) == 5 and all(1 <= x <= 43 for x in principales) and 1 <= superbalota <= 16:
            results.append({'fecha': fecha, 'nums': principales, 'sb': superbalota})

    return results


def main():
    print('=== Baloto Stats Scraper ===')

    data = load_existing()
    existing_dates = {s['fecha'] for s in data['sorteos']}
    print(f'Sorteos existentes: {len(existing_dates)}')

    first_html = fetch_page(1)
    last_page = get_last_page(first_html)
    print(f'Total de páginas en el sitio: {last_page}')

    # Incremental: si ya hay datos, solo revisamos las primeras páginas
    # (sorteos recientes). Si data.json está vacío, recorre todo el sitio
    # (los sorteos del formato antiguo se descartan solos al validar rangos).
    pages_to_scan = last_page if not existing_dates else min(3, last_page)

    new_results = []
    empty_streak = 0
    for page in range(1, pages_to_scan + 1):
        html = first_html if page == 1 else fetch_page(page)
        page_results = parse_page(html)
        print(f'Página {page}/{pages_to_scan}: {len(page_results)} resultados válidos (formato actual)')

        for result in page_results:
            if result['fecha'] not in existing_dates:
                new_results.append(result)
                existing_dates.add(result['fecha'])
                print(f"  NUEVO: {result['fecha']} -> {result['nums']} SB:{result['sb']}")

        # Si llevamos varias páginas seguidas sin resultados válidos, es
        # probable que ya entramos al territorio del formato antiguo (1-45);
        # seguimos igual hasta el final por si hay huecos, solo informamos.
        empty_streak = empty_streak + 1 if not page_results else 0
        if empty_streak == 5:
            print('  (Aviso: 5 páginas seguidas sin sorteos en formato actual, '
                  'probablemente ya se llegó al histórico del formato anterior 1-45)')

        if page < pages_to_scan:
            time.sleep(REQUEST_DELAY_SECONDS)

    if new_results:
        data['sorteos'].extend(new_results)
        data['sorteos'].sort(key=lambda x: x['fecha'])
        for idx, item in enumerate(data['sorteos'], start=1):
            item['id'] = idx

    data['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['total'] = len(data['sorteos'])

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'Total sorteos: {data["total"]}')
    print('Proceso finalizado.')


if __name__ == '__main__':
    main()
