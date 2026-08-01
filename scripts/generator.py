#!/usr/bin/env python3
"""
Generador de combinaciones para Baloto (5 números 1-43 + superbalota 1-16),
basado en distintas estrategias estadísticas.

Estrategias:
  - caliente:    prioriza números más frecuentes históricamente
  - frio:        prioriza números más atrasados (que no salen hace más tiempo)
  - equilibrado: mezcla calientes + fríos + aleatorios, respetando distribución
                 típica de pares/impares y rango de suma
  - aleatorio:   selección puramente aleatoria (control/baseline)
"""
import argparse
import json
import os
import random
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STATS_PATH = os.path.join(DATA_DIR, "estadisticas.json")
COMBOS_PATH = os.path.join(DATA_DIR, "combinaciones_generadas.json")

N_MIN, N_MAX = 1, 43
SB_MIN, SB_MAX = 1, 16


def load_stats():
    with open(STATS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _pick_superbalota(stats, estrategia, rng):
    freq_sb = {int(k): v for k, v in stats["frecuencias"]["superbalota"].items()}
    if estrategia == "caliente":
        candidatos = stats["superbalota_caliente"] or list(freq_sb.keys())
    elif estrategia == "frio":
        candidatos = stats["superbalota_fria"] or list(freq_sb.keys())
    else:
        candidatos = list(range(SB_MIN, SB_MAX + 1))
    return rng.choice(candidatos)


def generar_caliente(stats, rng):
    calientes = stats["numeros_calientes"][:15]
    pool = calientes if len(calientes) >= 5 else list(range(N_MIN, N_MAX + 1))
    numeros = sorted(rng.sample(pool, 5))
    sb = _pick_superbalota(stats, "caliente", rng)
    return numeros, sb


def generar_frio(stats, rng):
    frios = stats["numeros_frios"][:15]
    pool = frios if len(frios) >= 5 else list(range(N_MIN, N_MAX + 1))
    numeros = sorted(rng.sample(pool, 5))
    sb = _pick_superbalota(stats, "frio", rng)
    return numeros, sb


def generar_equilibrado(stats, rng, intentos=200):
    """Combina calientes + fríos, y ajusta a un patrón típico de
    pares/impares y una suma dentro del rango histórico observado."""
    calientes = set(stats["numeros_calientes"][:12])
    frios = set(stats["numeros_frios"][:12])
    resto = set(range(N_MIN, N_MAX + 1)) - calientes - frios

    suma_info = stats.get("sumas", {})
    suma_min = suma_info.get("min", 50)
    suma_max = suma_info.get("max", 170)

    mejor = None
    for _ in range(intentos):
        numeros = set()
        numeros |= set(rng.sample(sorted(calientes), min(2, len(calientes))))
        numeros |= set(rng.sample(sorted(frios), min(2, len(frios))))
        while len(numeros) < 5:
            numeros.add(rng.choice(sorted(resto | calientes | frios)))
        numeros = sorted(numeros)[:5]
        while len(numeros) < 5:
            extra = rng.randint(N_MIN, N_MAX)
            if extra not in numeros:
                numeros.append(extra)
        numeros = sorted(numeros)

        pares = sum(1 for n in numeros if n % 2 == 0)
        suma = sum(numeros)
        # patrón deseado: 2 o 3 pares, y suma dentro del rango histórico
        if pares in (2, 3) and suma_min <= suma <= suma_max:
            mejor = numeros
            break
        if mejor is None:
            mejor = numeros

    sb = _pick_superbalota(stats, "equilibrado", rng)
    return mejor, sb


def generar_aleatorio(stats, rng):
    numeros = sorted(rng.sample(range(N_MIN, N_MAX + 1), 5))
    sb = rng.randint(SB_MIN, SB_MAX)
    return numeros, sb


ESTRATEGIAS = {
    "caliente": generar_caliente,
    "frio": generar_frio,
    "equilibrado": generar_equilibrado,
    "aleatorio": generar_aleatorio,
}


def generar_combinaciones(n_por_estrategia=3, seed=None):
    stats = load_stats()
    rng = random.Random(seed)

    resultado = {
        "generado": datetime.now().isoformat() + "Z",
        "basado_en_sorteos": stats["total_sorteos"],
        "combinaciones": [],
    }

    for nombre, funcion in ESTRATEGIAS.items():
        for _ in range(n_por_estrategia):
            numeros, sb = funcion(stats, rng)
            resultado["combinaciones"].append({
                "estrategia": nombre,
                "numeros": numeros,
                "superbalota": sb,
            })

    with open(COMBOS_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de combinaciones Baloto")
    parser.add_argument("--n", type=int, default=3, help="Combinaciones por estrategia")
    parser.add_argument("--seed", type=int, default=None, help="Semilla aleatoria")
    args = parser.parse_args()

    resultado = generar_combinaciones(n_por_estrategia=args.n, seed=args.seed)
    for c in resultado["combinaciones"]:
        nums = "-".join(f"{n:02d}" for n in c["numeros"])
        print(f"[{c['estrategia']:>11}] {nums}  SB: {c['superbalota']:02d}")
