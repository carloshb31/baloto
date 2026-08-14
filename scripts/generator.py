#!/usr/bin/env python3
"""
Generador de combinaciones para Baloto (5 números 1-43 + superbalota 1-16).

Estrategia única: "números que más aparecen" calculada POR DÍA DE SORTEO.
Baloto sortea lunes, miércoles y sábado, y cada día se analiza por separado:
para cada día se toman solo los sorteos históricos que cayeron en ese día
de la semana, se calcula la frecuencia de cada número y de la superbalota,
y se arma una combinación con los 5 números y la superbalota más frecuentes
para ESE día específico.

Salida: una combinación para "lunes", una para "miercoles" y una para "sabado".
"""
import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HIST_PATH = os.path.join(DATA_DIR, "historico.csv")
COMBOS_PATH = os.path.join(DATA_DIR, "combinaciones_generadas.json")

N_MIN, N_MAX = 1, 43
SB_MIN, SB_MAX = 1, 16

# Python weekday(): lunes=0, martes=1, miércoles=2, ... domingo=6
DIAS_SORTEO = {0: "lunes", 2: "miercoles", 5: "sabado"}


def load_historico():
    with open(HIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            fecha = datetime.strptime(r["fecha"], "%Y-%m-%d")
            rows.append({
                "sorteo": int(r["sorteo"]),
                "fecha": r["fecha"],
                "dia_semana": fecha.weekday(),
                "numeros": [int(r["n1"]), int(r["n2"]), int(r["n3"]),
                            int(r["n4"]), int(r["n5"])],
                "superbalota": int(r["superbalota"]),
            })
    return rows


def frecuencia_por_dia(rows, dia_semana):
    """Frecuencia de números y superbalota solo entre sorteos de un día específico."""
    sorteos_del_dia = [r for r in rows if r["dia_semana"] == dia_semana]
    freq_numeros = Counter()
    freq_sb = Counter()
    for r in sorteos_del_dia:
        freq_numeros.update(r["numeros"])
        freq_sb[r["superbalota"]] += 1
    return freq_numeros, freq_sb, len(sorteos_del_dia)


def generar_combinacion_dia(rows, dia_semana, nombre_dia):
    freq_numeros, freq_sb, total_sorteos_dia = frecuencia_por_dia(rows, dia_semana)

    if total_sorteos_dia == 0 or not freq_numeros:
        # sin datos suficientes para ese día todavía: no se puede calcular frecuencia real
        return None

    top_numeros = [n for n, _ in freq_numeros.most_common(5)]
    # si aún no hay 5 números distintos con datos, completar con los siguientes más frecuentes
    if len(top_numeros) < 5:
        faltantes = [n for n in range(N_MIN, N_MAX + 1) if n not in top_numeros]
        top_numeros += faltantes[: 5 - len(top_numeros)]
    top_numeros = sorted(top_numeros[:5])

    if freq_sb:
        top_sb = freq_sb.most_common(1)[0][0]
    else:
        top_sb = None

    return {
        "estrategia": nombre_dia,
        "numeros": top_numeros,
        "superbalota": top_sb,
        "basado_en_sorteos_de_ese_dia": total_sorteos_dia,
    }


def generar_combinaciones():
    rows = load_historico()

    resultado = {
        "generado": datetime.now().isoformat() + "Z",
        "basado_en_sorteos": len(rows),
        "estrategia": "numeros_mas_frecuentes_por_dia_de_sorteo",
        "combinaciones": [],
    }

    for dia_semana, nombre_dia in DIAS_SORTEO.items():
        combo = generar_combinacion_dia(rows, dia_semana, nombre_dia)
        if combo:
            resultado["combinaciones"].append(combo)

    with open(COMBOS_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de combinaciones Baloto")
    parser.parse_args()  # sin argumentos por ahora; se deja por compatibilidad con el workflow

    resultado = generar_combinaciones()
    if not resultado["combinaciones"]:
        print("No hay suficientes sorteos históricos por día todavía.")
    for c in resultado["combinaciones"]:
        nums = "-".join(f"{n:02d}" for n in c["numeros"])
        sb = f"{c['superbalota']:02d}" if c["superbalota"] is not None else "--"
        print(f"[{c['estrategia']:>9}] {nums}  SB: {sb}  "
              f"(basado en {c['basado_en_sorteos_de_ese_dia']} sorteos de ese día)")
