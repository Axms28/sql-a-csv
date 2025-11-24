from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import pandas as pd
import os
from zipfile import ZipFile
from analizar_sql import analizar_sql_doc

app = Flask(__name__)
app.secret_key = "secret_key"

# Guardar TODAS las tablas del archivo SQL
tablas_global = {}
columnas_guardadas = {}


@app.route("/", methods=["GET", "POST"])
def index():
    global tablas_global

    if request.method == "POST":
        file = request.files.get("sqlfile")

        if not file or file.filename == "":
            flash("Debes seleccionar un archivo .sql", "danger")
            return redirect(url_for("index"))

        content = file.read().decode("utf-8", errors="ignore")
        tablas_global = analizar_sql_doc(content)

        if not tablas_global:
            flash("No se encontraron tablas válidas con INSERTs en el archivo.", "warning")
            return redirect(url_for("index"))

        # Redirigir mostrando la primera tabla
        primera = list(tablas_global.keys())[0]
        return redirect(url_for("ver_tabla", nombre_tabla=primera))

    return render_template("index.html")


@app.route("/tabla/<nombre_tabla>")
def ver_tabla(nombre_tabla):
    global tablas_global, columnas_guardadas

    if nombre_tabla not in tablas_global:
        flash("La tabla no existe.", "danger")
        return redirect(url_for("index"))

    df = tablas_global[nombre_tabla]
    columnas = list(df.columns)

    # === Cargar columnas guardadas o usar todas ===
    if nombre_tabla not in columnas_guardadas:
        columnas_guardadas[nombre_tabla] = columnas.copy()

    columnas_checked = columnas_guardadas[nombre_tabla]

    return render_template(
        "tabla.html",
        tablas=list(tablas_global.keys()),
        tabla_actual=nombre_tabla,
        columnas=columnas,
        columnas_checked=columnas_checked,
        datos=df.to_dict(orient="records")
    )


@app.route("/export", methods=["POST"])
def export():
    global tablas_global, columnas_guardadas

    tabla = request.form.get("tabla")
    columnas = request.form.getlist("columnas")

    if tabla not in tablas_global:
        flash("Tabla inválida", "danger")
        return redirect(url_for("index"))

    # === Guardar columnas seleccionadas ===
    columnas_guardadas[tabla] = columnas

    df = tablas_global[tabla]

    if not columnas:
        flash("Selecciona al menos una columna.", "warning")
        return redirect(url_for("ver_tabla", nombre_tabla=tabla))

    df_export = df[columnas]
    export_path = f"{tabla}.xlsx"
    df_export.to_excel(export_path, index=False)

    return send_file(export_path, as_attachment=True, download_name=f"{tabla}.xlsx")


@app.route("/export_todo", methods=["POST"])
def export_todo():
    global tablas_global, columnas_guardadas

    tabla_actual = request.form.get("tabla")
    columnas_actual = request.form.getlist("columnas")

    # Guardar selección para esta tabla
    columnas_guardadas[tabla_actual] = columnas_actual

    archivos = []

    for nombre_tabla, df in tablas_global.items():
        # columnas: usar guardadas o todas si no hay guardadas
        columnas_usar = columnas_guardadas.get(nombre_tabla, list(df.columns))

        df_export = df[columnas_usar]

        filename = f"{nombre_tabla}.xlsx"
        df_export.to_excel(filename, index=False)
        archivos.append(filename)

    zip_filename = "todas_las_tablas.zip"

    with ZipFile(zip_filename, "w") as zipf:
        for archivo in archivos:
            zipf.write(archivo)

    # limpiar temporales
    for archivo in archivos:
        if os.path.exists(archivo):
            os.remove(archivo)

    return send_file(zip_filename, as_attachment=True)


@app.route("/guardar_columnas", methods=["POST"])
def guardar_columnas():
    global columnas_guardadas

    tabla = request.form.get("tabla")
    columnas = request.form.getlist("columnas[]") 

    columnas_guardadas[tabla] = columnas

    return "ok"



if __name__ == "__main__":
    app.run(debug=True)
