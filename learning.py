#!/usr/bin/env python3
"""
Sistema de aprendizaje: evalúa las combinaciones generadas previamente
contra los resultados reales de los sorteos ya jugados, y lleva un
historial de desempeño por estrategia (data/desempeno_estrategias.json).

Se ejecuta después de cada actualización del histórico:
  1. Busca combinaciones generadas antes de la fecha de un sorteo.
  2. Calcula aciertos (números + superbalota) contra el resultado real.
  3. Acumula estadísticas de desempeño por estrategia.
"""
import csv
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HIST_PATH = os.path.join(DATA_DIR, "historico.csv")
COMBOS_PATH = os.path.join(DATA_DIR, "combinaciones_generadas.json")
LOG_PATH = os.path.join(DATA_DIR, "combinaciones_log.json")  # histórico acumulado de generaciones
PERF_PATH = os.path.join(DATA_DIR, "desempeno_estrategias.json")


def load_historico():
    with open(HIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({
                "sorteo": int(r["sorteo"]),
                "fecha": r["fecha"],
                "numeros": set([int(r["n1"]), int(r["n2"]), int(r["n3"]),
                                int(r["n4"]), int(r["n5"])]),
                "superbalota": int(r["superbalota"]),
            })
    return sorted(rows, key=lambda r: r["fecha"])


def append_to_log(nueva_generacion):
    """Guarda cada tanda de combinaciones generadas en un log acumulado,
    para poder evaluarlas más adelante contra sorteos futuros."""
    log = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as f:
            log = json.load(f)
    log.append(nueva_generacion)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def evaluar_combinacion(combo, sorteo_real):
    aciertos_numeros = len(set(combo["numeros"]) & sorteo_real["numeros"])
    acierto_sb = combo["superbalota"] == sorteo_real["superbalota"]
    return aciertos_numeros, acierto_sb


def categoria_premio(aciertos_numeros, acierto_sb):
    if aciertos_numeros == 5 and acierto_sb:
        return "acumulado"
    if aciertos_numeros == 5:
        return "5_aciertos"
    if aciertos_numeros == 4 and acierto_sb:
        return "4_mas_sb"
    if aciertos_numeros == 4:
        return "4_aciertos"
    if aciertos_numeros == 3 and acierto_sb:
        return "3_mas_sb"
    if aciertos_numeros == 3:
        return "3_aciertos"
    if aciertos_numeros == 2 and acierto_sb:
        return "2_mas_sb"
    if acierto_sb:
        return "solo_sb"
    return "sin_premio"


def evaluar_todo():
    historico = load_historico()
    if not os.path.exists(LOG_PATH):
        print("No hay historial de combinaciones generadas todavía.")
        return

    with open(LOG_PATH, encoding="utf-8") as f:
        log = json.load(f)

    desempeno = {}  # estrategia -> {"evaluadas": n, "aciertos_prom": x, "categorias": {...}}

    for generacion in log:
        fecha_generacion = generacion["generado"][:10]
        for combo in generacion["combinaciones"]:
            for sorteo in historico:
                if sorteo["fecha"] <= fecha_generacion:
                    continue  # solo evaluar contra sorteos posteriores a la generación
                aciertos_n, acierto_sb = evaluar_combinacion(combo, sorteo)
                cat = categoria_premio(aciertos_n, acierto_sb)

                est = combo["estrategia"]
                d = desempeno.setdefault(est, {
                    "evaluaciones": 0,
                    "total_aciertos_numeros": 0,
                    "aciertos_superbalota": 0,
                    "categorias": {},
                })
                d["evaluaciones"] += 1
                d["total_aciertos_numeros"] += aciertos_n
                if acierto_sb:
                    d["aciertos_superbalota"] += 1
                d["categorias"][cat] = d["categorias"].get(cat, 0) + 1

    for est, d in desempeno.items():
        if d["evaluaciones"]:
            d["promedio_aciertos_numeros"] = round(
                d["total_aciertos_numeros"] / d["evaluaciones"], 3
            )

    resultado = {
        "actualizado": datetime.now().isoformat() + "Z",
        "desempeno_por_estrategia": desempeno,
    }

    with open(PERF_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Evaluación completa -> {PERF_PATH}")
    for est, d in desempeno.items():
        print(f"  {est}: {d['evaluaciones']} evaluaciones, "
              f"promedio aciertos {d.get('promedio_aciertos_numeros', 0)}")

    return resultado


if __name__ == "__main__":
    if os.path.exists(COMBOS_PATH):
        with open(COMBOS_PATH, encoding="utf-8") as f:
            generacion_actual = json.load(f)
        append_to_log(generacion_actual)
        print("Combinaciones actuales agregadas al log de aprendizaje.")
    evaluar_todo()
