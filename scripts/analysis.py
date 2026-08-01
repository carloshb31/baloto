#!/usr/bin/env python3
"""
Análisis estadístico del histórico de Baloto.
Genera data/estadisticas.json con frecuencias, atrasos, pares/impares,
sumas, y otros indicadores usados por el generador y el dashboard.
"""
import csv
import json
import os
from collections import Counter
from datetime import datetime
from itertools import combinations

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HIST_PATH = os.path.join(DATA_DIR, "historico.csv")
STATS_PATH = os.path.join(DATA_DIR, "estadisticas.json")

N_MIN, N_MAX = 1, 43
SB_MIN, SB_MAX = 1, 16


def load_historico():
    with open(HIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({
                "sorteo": int(r["sorteo"]),
                "fecha": r["fecha"],
                "numeros": sorted([int(r["n1"]), int(r["n2"]), int(r["n3"]),
                                    int(r["n4"]), int(r["n5"])]),
                "superbalota": int(r["superbalota"]),
            })
    return sorted(rows, key=lambda r: r["sorteo"])


def frecuencias(rows):
    freq = Counter()
    freq_sb = Counter()
    for r in rows:
        freq.update(r["numeros"])
        freq_sb[r["superbalota"]] += 1
    principales = {n: freq.get(n, 0) for n in range(N_MIN, N_MAX + 1)}
    superbalota = {n: freq_sb.get(n, 0) for n in range(SB_MIN, SB_MAX + 1)}
    return principales, superbalota


def atrasos(rows):
    """Sorteos desde la última aparición de cada número (0 = salió en el último)."""
    total = len(rows)
    ultima_pos = {}
    for idx, r in enumerate(rows):
        for n in r["numeros"]:
            ultima_pos[n] = idx
    ultima_pos_sb = {}
    for idx, r in enumerate(rows):
        ultima_pos_sb[r["superbalota"]] = idx

    atraso_principales = {}
    for n in range(N_MIN, N_MAX + 1):
        if n in ultima_pos:
            atraso_principales[n] = (total - 1) - ultima_pos[n]
        else:
            atraso_principales[n] = total  # nunca ha salido

    atraso_sb = {}
    for n in range(SB_MIN, SB_MAX + 1):
        if n in ultima_pos_sb:
            atraso_sb[n] = (total - 1) - ultima_pos_sb[n]
        else:
            atraso_sb[n] = total

    return atraso_principales, atraso_sb


def pares_impares(rows):
    dist = Counter()
    for r in rows:
        pares = sum(1 for n in r["numeros"] if n % 2 == 0)
        dist[f"{pares}pares_{5-pares}impares"] += 1
    return dict(dist)


def sumas(rows):
    valores = [sum(r["numeros"]) for r in rows]
    if not valores:
        return {}
    return {
        "min": min(valores),
        "max": max(valores),
        "promedio": round(sum(valores) / len(valores), 2),
        "distribucion": sorted(valores),
    }


def pares_numeros_frecuentes(rows, top=15):
    """Pares de números que más se repiten juntos en un mismo sorteo."""
    pair_counter = Counter()
    for r in rows:
        for a, b in combinations(r["numeros"], 2):
            pair_counter[f"{a}-{b}"] += 1
    return [{"par": k, "veces": v} for k, v in pair_counter.most_common(top)]


def numeros_calientes_frios(freq_principales, top=10):
    ordenado = sorted(freq_principales.items(), key=lambda x: x[1], reverse=True)
    calientes = [n for n, _ in ordenado[:top]]
    frios = [n for n, _ in ordenado[-top:]]
    return calientes, frios


def build_stats():
    rows = load_historico()
    if not rows:
        raise SystemExit("No hay datos históricos en data/historico.csv")

    freq_principales, freq_sb = frecuencias(rows)
    atraso_principales, atraso_sb = atrasos(rows)
    calientes, frios = numeros_calientes_frios(freq_principales)
    calientes_sb, frios_sb = numeros_calientes_frios(freq_sb, top=5)

    stats = {
        "actualizado": datetime.now().isoformat() + "Z",
        "total_sorteos": len(rows),
        "rango_fechas": {
            "desde": rows[0]["fecha"],
            "hasta": rows[-1]["fecha"],
        },
        "frecuencias": {
            "principales": freq_principales,
            "superbalota": freq_sb,
        },
        "atrasos": {
            "principales": atraso_principales,
            "superbalota": atraso_sb,
        },
        "numeros_calientes": calientes,
        "numeros_frios": frios,
        "superbalota_caliente": calientes_sb,
        "superbalota_fria": frios_sb,
        "pares_impares": pares_impares(rows),
        "sumas": sumas(rows),
        "pares_frecuentes": pares_numeros_frecuentes(rows),
        "ultimo_sorteo": {
            "sorteo": rows[-1]["sorteo"],
            "fecha": rows[-1]["fecha"],
            "numeros": rows[-1]["numeros"],
            "superbalota": rows[-1]["superbalota"],
        },
    }

    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Estadísticas generadas con {len(rows)} sorteos -> {STATS_PATH}")
    return stats


if __name__ == "__main__":
    build_stats()
