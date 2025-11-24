import re
import pandas as pd


def analizar_sql_doc(sql_text: str):
    # REGEX que captura cada INSERT INTO ... VALUES (...);
    patron = r"INSERT INTO\s+`?(.*?)`?\s*\((.*?)\)\s*VALUES\s*(.*?);"
    inserts = re.findall(patron, sql_text, flags=re.DOTALL | re.IGNORECASE)

    if not inserts:
        return {}

    tablas = {}

    patron_fila = re.compile(r"\((.*?)\)", re.DOTALL)

    for tabla, columnas_raw, values_raw in inserts:
        columnas = [c.strip().replace("`", "") for c in columnas_raw.split(",")]
        filas = []

        grupos = patron_fila.findall(values_raw)

        for grupo in grupos:
            valores = parse_value_group(grupo)

            # Rellenar o recortar si faltan/sobran columnas
            while len(valores) < len(columnas):
                valores.append(None)
            valores = valores[:len(columnas)]

            filas.append(valores)

        df = pd.DataFrame(filas, columns=columnas)

        # Agregar o concatenar si la tabla ya apareció antes
        if tabla in tablas:
            tablas[tabla] = pd.concat([tablas[tabla], df], ignore_index=True)
        else:
            tablas[tabla] = df

    return tablas


def parse_value_group(grupo):
    valores = []
    actual = ""
    dentro_string = False
    escape = False

    for char in grupo:
        if escape:
            actual += char
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char == "'" and not dentro_string:
            dentro_string = True
            continue
        elif char == "'" and dentro_string:
            dentro_string = False
            valores.append(actual)
            actual = ""
            continue

        if char == "," and not dentro_string:
            val = actual.strip()
            if val.upper() == "NULL":
                valores.append(None)
            elif val != "":
                valores.append(val)
            actual = ""
            continue

        actual += char

    val = actual.strip()
    if dentro_string:
        valores.append(actual)
    else:
        if val.upper() == "NULL":
            valores.append(None)
        elif val != "":
            valores.append(val)

    return valores
