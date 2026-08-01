#!/usr/bin/env python3
"""
Scraper de resultados históricos de Baloto (baloto.com/resultados).
A diferencia de MiLoto, esta página SÍ se puede leer con HTML estático
(no requiere renderizado JS), por lo que usamos requests + BeautifulSoup.

Reglas del juego: 5 números principales (1-43) + 1 superbalota (1-16).

Guarda/actualiza data/historico.csv con columnas:
sorteo, fecha, n1, n2, n3, n4, n5, superbalota
"""
import csv
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://baloto.com/resultados"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "historico.csv")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

FIELDNAMES = ["sorteo", "fecha", "n1", "n2", "n3", "n4", "n5", "superbalota"]


def parse_fecha(texto):
    m = re.match(r"(\d{1,2}) de (\w+) de (\d{4})", texto.strip(), re.IGNORECASE)
    if not m:
        return None
    dia, mes_txt, anio = m.groups()
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return None
    return datetime(int(anio), mes, int(dia)).strftime("%Y-%m-%d")


def fetch_page(page: int):
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_page(html: str):
    """Devuelve lista de dicts solo para sorteos de BALOTO (ignora Revancha)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")
    results = []
    for row in rows:
        link = row.select_one('a[href*="resultados-baloto/"]')
        if not link:
            continue  # es revancha, colorloto u otra fila

        m = re.search(r"resultados-baloto/(\d+)", link["href"])
        sorteo = int(m.group(1)) if m else None

        row_text = row.get_text(" ", strip=True)

        fecha_match = re.search(r"\d{1,2} de \w+ de \d{4}", row_text)
        fecha = parse_fecha(fecha_match.group(0)) if fecha_match else None

        nums_match = re.search(
            r"(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})",
            row_text,
        )
        if not (sorteo and fecha and nums_match):
            continue

        n = [int(x) for x in nums_match.groups()]
        results.append({
            "sorteo": sorteo,
            "fecha": fecha,
            "n1": n[0], "n2": n[1], "n3": n[2], "n4": n[3], "n5": n[4],
            "superbalota": n[5],
        })
    return results


def get_last_page():
    html = fetch_page(1)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"Página \d+ de (\d+)", text)
    return int(m.group(1)) if m else 1


def load_existing():
    if not os.path.exists(DATA_PATH):
        return {}
    existing = {}
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[int(row["sorteo"])] = {
                "sorteo": int(row["sorteo"]),
                "fecha": row["fecha"],
                "n1": int(row["n1"]), "n2": int(row["n2"]), "n3": int(row["n3"]),
                "n4": int(row["n4"]), "n5": int(row["n5"]),
                "superbalota": int(row["superbalota"]),
            }
    return existing


def save_all(records):
    records = sorted(records, key=lambda r: r["sorteo"])
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def main(max_pages=None, full=False):
    existing = load_existing()
    print(f"Registros existentes: {len(existing)}")

    last_page = get_last_page()
    print(f"Total de páginas en el sitio: {last_page}")

    pages_to_scan = last_page if full else min(3, last_page)
    if max_pages:
        pages_to_scan = min(pages_to_scan, max_pages)

    all_records = dict(existing)
    new_count = 0

    for page in range(1, pages_to_scan + 1):
        html = fetch_page(page)
        parsed = parse_page(html)
        for rec in parsed:
            if rec["sorteo"] not in all_records:
                new_count += 1
            all_records[rec["sorteo"]] = rec
        print(f"  página {page}/{pages_to_scan} procesada ({len(parsed)} sorteos)")
        time.sleep(0.5)

    save_all(list(all_records.values()))
    print(f"Nuevos sorteos agregados: {new_count}")
    print(f"Total en histórico: {len(all_records)}")


if __name__ == "__main__":
    full = "--full" in sys.argv
    main(full=full)
