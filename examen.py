#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examen.py — Runner principal del simulacro de examen (modo terminal)
======================================================================
Carga automáticamente todos los temas desde /data/**/*.json — la MISMA
fuente de datos que usa la web (index.html + quiz.html). No hay que
mantener dos catálogos de preguntas por separado.

Para añadir un tema nuevo:
  1. Crea un archivo JSON en data/<asignatura>/<tema>.json (ver README.md
     para el esquema exacto, o usa scripts/convert_legacy_py.py si vienes
     de un archivo .py del formato antiguo).
  2. Ejecuta scripts/build_manifest.py (regenera data/manifest.json, que
     usa la web — el runner de terminal no lo necesita, pero conviene
     tenerlo actualizado).
  3. Listo — tanto examen.py como la web lo detectarán solos.

Esquema de cada archivo de tema (data/<asignatura>/<tema>.json):

    {
      "asignatura":       "Redes III",
      "asignatura_slug":  "redes-iii",
      "tema":             "Routing",
      "tema_id":           "redes3_tema1",
      "orden":            4,
      "test": [
        {
          "enunciado": "texto de la pregunta",
          "opciones": [
            {"texto": "opción A", "correcta": false},
            {"texto": "opción B", "correcta": true},
            {"texto": "opción C", "correcta": false}
          ],
          "explicacion": "opcional, se muestra en la web"
        }
      ],
      "redaccion": [
        {"titulo": "Título corto", "enunciado": "Enunciado completo.", "puntos": 15}
      ]
    }

Nota: el runner de terminal solo sabe hacer preguntas de una única
respuesta correcta (tipo test clásico). Si un archivo trae preguntas de
varias respuestas correctas o de emparejar (imagen/tabla) — pensadas
para la web — el runner las salta automáticamente y avisa por consola;
en la web sí funcionan.
"""

import os
import sys
import json
import random
import textwrap
from datetime import datetime

# ─────────────────────────────────────────────
#  COLORES ANSI
# ─────────────────────────────────────────────
V  = "\033[92m"   # verde
R  = "\033[91m"   # rojo
AM = "\033[93m"   # amarillo
CY = "\033[96m"   # cyan
BL = "\033[97m"   # blanco
N  = "\033[1m"    # negrita
GR = "\033[90m"   # gris
RE = "\033[0m"    # reset

# ─────────────────────────────────────────────
#  CARGA DINÁMICA DE TEMAS
# ─────────────────────────────────────────────

def cargar_temas():
    """
    Escanea la carpeta data/ (recursivamente) y carga todos los .json
    de tema (ignora manifest.json). Devuelve una lista de dicts con la
    misma forma que usaba el runner antiguo: {"meta", "test", "redaccion", "archivo"}.
    """
    carpeta = os.path.join(os.path.dirname(__file__), "data")
    temas_cargados = []

    if not os.path.isdir(carpeta):
        return temas_cargados

    rutas = []
    for dirpath, _dirnames, filenames in os.walk(carpeta):
        for fname in sorted(filenames):
            if fname.endswith(".json") and fname != "manifest.json":
                rutas.append(os.path.join(dirpath, fname))
    rutas.sort()

    for ruta in rutas:
        archivo = os.path.relpath(ruta, carpeta)
        try:
            with open(ruta, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"{R}Error cargando {archivo}: {e}{RE}")
            continue

        if data.get("encrypted"):
            print(f"{GR}({archivo}: protegido con contraseña — solo disponible en la web, se salta en terminal){RE}")
            continue

        if not all(k in data for k in ("asignatura", "tema", "test", "redaccion")):
            print(f"{AM}Aviso: {archivo} ignorado (faltan claves obligatorias){RE}")
            continue

        test_utilizable, saltadas = _filtrar_test_cli(data.get("test", []))
        if saltadas:
            print(f"{GR}({archivo}: {saltadas} pregunta(s) de tipo web-only omitidas en terminal){RE}")

        temas_cargados.append({
            "meta": {
                "id": data.get("orden", 0),
                "nombre": data.get("tema", archivo),
                "asignatura": data.get("asignatura", "Sin asignatura"),
            },
            "test": test_utilizable,
            "redaccion": data.get("redaccion", []),
            "archivo": archivo,
        })

    temas_cargados.sort(key=lambda t: (t["meta"].get("asignatura", ""), t["meta"].get("id", 0)))
    # reasignar ids únicos consecutivos para el menú (los "orden" pueden repetirse entre asignaturas)
    for i, t in enumerate(temas_cargados, 1):
        t["meta"]["id"] = i
    return temas_cargados


def _filtrar_test_cli(test_items):
    """
    El runner de terminal solo sabe hacer preguntas de una única respuesta
    correcta con letras a/b/c/d. Filtra fuera (con aviso) las preguntas de
    varias respuestas correctas o de tipo emparejar (pensadas para la web).
    Devuelve (lista_utilizable, num_saltadas).
    """
    utilizable = []
    saltadas = 0
    for p in test_items:
        if p.get("tipo") in ("matching_table", "matching_image"):
            saltadas += 1
            continue
        opciones = p.get("opciones", [])
        correctas = sum(1 for o in opciones if o.get("correcta"))
        if correctas != 1 or len(opciones) < 2:
            saltadas += 1
            continue
        utilizable.append({
            "enunciado": p["enunciado"],
            "opciones": [(o["texto"], bool(o["correcta"])) for o in opciones],
        })
    return utilizable, saltadas

# ─────────────────────────────────────────────
#  UTILIDADES DE TERMINAL
# ─────────────────────────────────────────────

def limpiar():
    os.system("clear" if os.name != "nt" else "cls")

def wrap(texto, ancho=70):
    return textwrap.fill(str(texto), width=ancho)

def titulo(texto):
    linea = "═" * 62
    print(f"\n{CY}{N}{linea}{RE}")
    print(f"{CY}{N}  {texto}{RE}")
    print(f"{CY}{N}{linea}{RE}\n")

def separador():
    print(f"{GR}{'─' * 62}{RE}")

def pedir_int(prompt, minimo, maximo):
    while True:
        try:
            valor = int(input(prompt).strip())
            if minimo <= valor <= maximo:
                return valor
            print(f"{R}Introduce un número entre {minimo} y {maximo}.{RE}")
        except ValueError:
            print(f"{R}Por favor introduce un número.{RE}")

def leer_multilinea():
    """Lee texto libre hasta que el usuario escribe '---' solo en una línea."""
    print(f"{GR}(Escribe tu respuesta. Cuando termines escribe '---' en una línea nueva){RE}\n")
    lineas = []
    while True:
        try:
            linea = input()
            if linea.strip() == "---":
                break
            lineas.append(linea)
        except EOFError:
            break
    return "\n".join(lineas)

# ─────────────────────────────────────────────
#  MENÚS DE CONFIGURACIÓN
# ─────────────────────────────────────────────

def menu_temas(temas_disponibles):
    """Permite al usuario elegir qué temas incluir en el examen."""
    titulo("Selección de temas")

    for t in temas_disponibles:
        meta = t["meta"]
        print(f"  {CY}{meta['id']}{RE}  {meta['nombre']}"
              f"  {GR}({len(t['test'])} test · {len(t['redaccion'])} redacción){RE}")

    ids = [str(t["meta"]["id"]) for t in temas_disponibles]
    print(f"\n  {CY}0{RE}  Todos los temas")
    print()

    while True:
        entrada = input(
            f"{AM}Elige tema(s) separados por coma, o 0 para todos "
            f"(ej: 1,3): {RE}"
        ).strip()

        if entrada == "0":
            return temas_disponibles

        seleccionados_ids = {x.strip() for x in entrada.split(",")}
        if seleccionados_ids.issubset(set(ids)):
            return [t for t in temas_disponibles
                    if str(t["meta"]["id"]) in seleccionados_ids]

        print(f"{R}IDs no válidos. Usa los números del menú.{RE}")

def menu_cantidad(temas_sel):
    """Pregunta cuántas preguntas de cada tipo quiere el usuario."""
    total_test = sum(len(t["test"]) for t in temas_sel)
    total_red  = sum(len(t["redaccion"]) for t in temas_sel)

    limpiar()
    titulo("Cantidad de preguntas")
    print(f"  Preguntas test disponibles:      {BL}{total_test}{RE}")
    print(f"  Preguntas redacción disponibles: {BL}{total_red}{RE}\n")

    num_test = pedir_int(
        f"{AM}¿Cuántas preguntas tipo test? (0-{total_test}): {RE}",
        0, total_test
    )
    num_red = pedir_int(
        f"{AM}¿Cuántas preguntas de redacción? (0-{total_red}): {RE}",
        0, total_red
    )

    if num_test == 0 and num_red == 0:
        print(f"{R}No has seleccionado ninguna pregunta. Saliendo.{RE}")
        sys.exit(0)

    return num_test, num_red

# ─────────────────────────────────────────────
#  LÓGICA DEL EXAMEN
# ─────────────────────────────────────────────

def hacer_test(preguntas, pts_por_pregunta):
    resultados = []
    total = len(preguntas)
    letras = ["a", "b", "c", "d"]

    for i, preg in enumerate(preguntas, 1):
        limpiar()
        titulo(f"TIPO TEST  —  {i} / {total}  [{preg['_tema_nombre']}]")

        print(f"{BL}{N}{wrap(preg['enunciado'])}{RE}\n")
        separador()

        # Mezclar opciones aleatoriamente
        opciones = list(preg["opciones"])
        random.shuffle(opciones)

        for j, (texto, _) in enumerate(opciones):
            print(f"  {CY}{letras[j]}{RE}) {wrap(texto, 66)}")

        print()
        while True:
            resp = input(f"{AM}Tu respuesta ({'/'.join(letras[:len(opciones)])}): {RE}").strip().lower()
            if resp in letras[:len(opciones)]:
                break
            print(f"{R}Opción no válida.{RE}")

        idx = letras.index(resp)
        texto_elegido, es_correcta = opciones[idx]
        correcta_texto = next(t for t, c in opciones if c)
        correcta_letra = letras[[t for t, c in opciones].index(correcta_texto)]

        if es_correcta:
            print(f"\n{V}{N}✓  Correcto{RE}  (+{pts_por_pregunta:.1f} pts)")
        else:
            print(f"\n{R}{N}✗  Incorrecto{RE}")
            print(f"   Correcta → {V}{correcta_letra}) {correcta_texto}{RE}")

        resultados.append({
            "tema":              preg["_tema_nombre"],
            "enunciado":         preg["enunciado"],
            "correcta":          es_correcta,
            "tu_respuesta":      texto_elegido,
            "respuesta_correcta": correcta_texto,
            "pts":               pts_por_pregunta if es_correcta else 0,
        })

        input(f"\n{GR}Pulsa Enter para continuar...{RE}")

    return resultados

def hacer_redaccion(preguntas):
    respuestas = []
    total = len(preguntas)

    for i, preg in enumerate(preguntas, 1):
        limpiar()
        titulo(f"REDACCIÓN  —  {i} / {total}  [{preg['_tema_nombre']}]")
        print(f"{N}{BL}{preg['titulo']}{RE}  {GR}({preg['puntos']} puntos){RE}\n")
        separador()
        print(f"{wrap(preg['enunciado'], 70)}\n")
        separador()
        print()

        texto = leer_multilinea()

        respuestas.append({
            "tema":       preg["_tema_nombre"],
            "titulo":     preg["titulo"],
            "enunciado":  preg["enunciado"],
            "puntos_max": preg["puntos"],
            "respuesta":  texto,
        })

        print(f"\n{V}✓  Respuesta guardada.{RE}")
        input(f"{GR}Pulsa Enter para continuar...{RE}")

    return respuestas

# ─────────────────────────────────────────────
#  RESULTADO FINAL
# ─────────────────────────────────────────────

def mostrar_resultado(resultados_test, respuestas_red, pts_test_max):
    limpiar()
    titulo("RESULTADO DEL EXAMEN")

    # ── Test ──
    correctas  = sum(1 for r in resultados_test if r["correcta"])
    total_test = len(resultados_test)
    pts_test   = sum(r["pts"] for r in resultados_test)

    if total_test > 0:
        print(f"{N}PARTE A — TIPO TEST{RE}")
        print(f"  Correctas : {V}{correctas}{RE} / {total_test}")
        print(f"  Puntos    : {V}{pts_test:.1f}{RE} / {pts_test_max:.1f}")
        separador()

        errores = [r for r in resultados_test if not r["correcta"]]
        if errores:
            print(f"\n{R}Preguntas falladas:{RE}")
            for e in errores:
                print(f"\n  {GR}[{e['tema']}]{RE} {wrap(e['enunciado'], 64)}")
                print(f"    Tu respuesta : {R}{e['tu_respuesta']}{RE}")
                print(f"    Correcta     : {V}{e['respuesta_correcta']}{RE}")
        else:
            print(f"\n{V}¡Todas las preguntas test correctas!{RE}")
        separador()

    # ── Redacción ──
    if respuestas_red:
        pts_red_max = sum(r["puntos_max"] for r in respuestas_red)
        print(f"\n{N}PARTE B — REDACCIÓN{RE}")
        print(f"  {AM}⚠  Pendiente de corrección manual  ({pts_red_max} puntos posibles){RE}\n")

        bloque = _generar_bloque(respuestas_red)
        separador()
        print(bloque)
        separador()

        print(f"\n{AM}Nota parcial (solo test) : {pts_test:.1f} / {pts_test_max:.1f}{RE}")
        print(f"{AM}Nota final = nota test + corrección de redacción{RE}")

    else:
        total_max = pts_test_max
        pct = (pts_test / total_max * 100) if total_max > 0 else 0
        color = V if pct >= 50 else R
        print(f"\n{N}NOTA FINAL: {color}{pts_test:.1f} / {total_max:.1f}  ({pct:.0f}%){RE}")

    print()

def _generar_bloque(respuestas):
    """Genera el bloque de texto para pegar al corrector."""
    sep = "=" * 62
    lineas = [
        sep,
        "BLOQUE PARA CORRECCIÓN — REDACCIÓN",
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sep,
    ]
    for i, r in enumerate(respuestas, 1):
        lineas += [
            f"\n[PREGUNTA {i} — {r['tema']} — {r['puntos_max']} puntos]",
            f"Título   : {r['titulo']}",
            f"Enunciado: {r['enunciado']}",
            f"\nRespuesta del alumno:\n{r['respuesta']}",
            "\n" + "─" * 62,
        ]
    lineas += [
        "\nPuntúa cada pregunta sobre su máximo.",
        "Nota global = puntuación test ya calculada + suma de redacción.",
    ]
    return "\n".join(lineas)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    limpiar()
    titulo("Simulacro de Examen — Runner Universal")

    # 1. Cargar temas
    temas = cargar_temas()
    if not temas:
        print(f"{R}No se encontraron temas en la carpeta /temas. Saliendo.{RE}")
        sys.exit(1)

    asignaturas = {t["meta"].get("asignatura", "Sin asignatura") for t in temas}
    print(f"  Asignatura(s) : {BL}{', '.join(sorted(asignaturas))}{RE}")
    print(f"  Temas cargados: {BL}{len(temas)}{RE}")
    print(f"  Total preguntas test     : {BL}{sum(len(t['test']) for t in temas)}{RE}")
    print(f"  Total preguntas redacción: {BL}{sum(len(t['redaccion']) for t in temas)}{RE}\n")
    input(f"{AM}Pulsa Enter para configurar el examen...{RE}")

    # 2. Selección de temas
    limpiar()
    temas_sel = menu_temas(temas)

    # 3. Cantidad de preguntas
    num_test, num_red = menu_cantidad(temas_sel)

    # 4. Calcular puntos
    pts_red_total  = num_red * 15
    pts_test_total = 100 - pts_red_total
    pts_por_preg   = (pts_test_total / num_test) if num_test > 0 else 0

    # 5. Resumen antes de empezar
    limpiar()
    titulo("Resumen del examen")
    nombres = ", ".join(t["meta"]["nombre"] for t in temas_sel)
    print(f"  Temas        : {BL}{nombres}{RE}")
    print(f"  Test         : {BL}{num_test} preguntas{RE}  ({pts_por_preg:.1f} pts cada una)")
    print(f"  Redacción    : {BL}{num_red} preguntas{RE}  (15 pts cada una)")
    print(f"  Total puntos : {BL}{num_test * pts_por_preg + num_red * 15:.0f}{RE}\n")
    input(f"{AM}Pulsa Enter para empezar...{RE}")

    # 6. Construir pool de preguntas (aplanado con metadato de tema)
    pool_test = []
    for t in temas_sel:
        for p in t["test"]:
            pool_test.append({**p, "_tema_nombre": t["meta"]["nombre"]})

    pool_red = []
    for t in temas_sel:
        for p in t["redaccion"]:
            pool_red.append({**p, "_tema_nombre": t["meta"]["nombre"]})

    preguntas_test_sel = random.sample(pool_test, num_test)
    preguntas_red_sel  = random.sample(pool_red,  num_red)

    # 7. Ejecutar examen
    resultados_test = hacer_test(preguntas_test_sel, pts_por_preg) if num_test > 0 else []
    respuestas_red  = hacer_redaccion(preguntas_red_sel)            if num_red  > 0 else []

    # 8. Resultado
    mostrar_resultado(resultados_test, respuestas_red, num_test * pts_por_preg)

if __name__ == "__main__":
    main()
