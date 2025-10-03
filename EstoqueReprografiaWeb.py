from flask import Flask, render_template, request, redirect, send_file, flash
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "estoque_secret"

DB_FILE = "estoque.db"

# ---------- Banco de dados ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        codigo TEXT PRIMARY KEY,
        nome TEXT,
        unidade TEXT,
        quantidade INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        nome TEXT,
        tipo TEXT,
        quantidade INTEGER,
        datahora TEXT
    )
    """)
    conn.commit()
    conn.close()

def registrar_movimentacao(codigo, nome, tipo, quantidade):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO movimentacoes (codigo, nome, tipo, quantidade, datahora) VALUES (?, ?, ?, ?, ?)",
                   (codigo, nome, tipo, quantidade, agora))
    conn.commit()
    conn.close()

def consultar_estoque(termo=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if termo.strip() == "":
        cursor.execute("SELECT * FROM estoque")
    else:
        cursor.execute("SELECT * FROM estoque WHERE codigo LIKE ? OR nome LIKE ?", (f"%{termo}%", f"%{termo}%"))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ---------- Rotas ----------
@app.route("/", methods=["GET", "POST"])
def index():
    termo = request.form.get("consulta") if request.method == "POST" else ""
    estoque = consultar_estoque(termo)
    produtos = [
        "Capa Plástica PVC Fumê A4 – 100 un",
        "Capa Plástica PVC Preta A4 (210x297 mm) – 100 un",
        "Espiral Plástico Preto 7 mm – 100 un",
        "Espiral Plástico Preto 9 mm – 100 un",
        "Espiral Plástico Preto 14 mm – 100 un",
        "Espiral Plástico Preto 17 mm – 100 un",
        "Espiral Plástico Preto 20 mm – 100 un",
        "Espiral Plástico Preto 23 mm – 60 un",
        "Espiral Plástico Preto 33 mm – 27 un",
        "Plástico para Plastificação A4 – 0,01 mm – 100 un",
        "Plástico para Plastificação A3 – 0,01 mm – 100 un"
    ]
    unidades = ["Unidade", "Saco", "Pacote"]
    return render_template("index.html", estoque=estoque, produtos=produtos, unidades=unidades)

@app.route("/entrada", methods=["POST"])
def entrada():
    codigo = request.form["codigo"]
    nome = request.form["nome"]
    unidade = request.form["unidade"]
    try:
        quantidade = int(request.form["quantidade"])
    except ValueError:
        flash("Quantidade deve ser um número", "error")
        return redirect("/")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM estoque WHERE codigo=?", (codigo,))
    item = cursor.fetchone()
    if item:
        nova_qtd = item[3] + quantidade
        cursor.execute("UPDATE estoque SET quantidade=? WHERE codigo=?", (nova_qtd, codigo))
    else:
        cursor.execute("INSERT INTO estoque VALUES (?, ?, ?, ?)", (codigo, nome, unidade, quantidade))
    conn.commit()
    conn.close()
    
    registrar_movimentacao(codigo, nome, "Entrada", quantidade)
    flash(f"Item {nome} armazenado com sucesso!", "success")
    return redirect("/")

@app.route("/saida", methods=["POST"])
def saida():
    codigo = request.form["codigo"]
    try:
        quantidade = int(request.form["quantidade"])
    except ValueError:
        flash("Quantidade deve ser um número", "error")
        return redirect("/")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM estoque WHERE codigo=?", (codigo,))
    item = cursor.fetchone()
    if not item:
        flash("Item não encontrado no estoque", "error")
        conn.close()
        return redirect("/")
    if item[3] < quantidade:
        flash("Quantidade insuficiente no estoque", "error")
        conn.close()
        return redirect("/")

    nova_qtd = item[3] - quantidade
    cursor.execute("UPDATE estoque SET quantidade=? WHERE codigo=?", (nova_qtd, codigo))
    conn.commit()
    conn.close()

    registrar_movimentacao(codigo, item[1], "Saída", quantidade)
    flash(f"Saída de {quantidade} do item {item[1]} registrada!", "success")
    return redirect("/")

@app.route("/limpar/<codigo>")
def limpar(codigo):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM estoque WHERE codigo=?", (codigo,))
    item = cursor.fetchone()
    if not item:
        flash("Item não encontrado", "error")
        conn.close()
        return redirect("/")
    cursor.execute("DELETE FROM estoque WHERE codigo=?", (codigo,))
    conn.commit()
    conn.close()
    registrar_movimentacao(codigo, item[1], "Remoção", 0)
    flash(f"Item {item[1]} removido do estoque!", "success")
    return redirect("/")

@app.route("/exportar")
def exportar():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM estoque")
    dados_estoque = cursor.fetchall()
    df_estoque = pd.DataFrame(dados_estoque, columns=["Código", "Nome", "Unidade", "Quantidade"])

    cursor.execute("SELECT codigo, nome, tipo, quantidade, datahora FROM movimentacoes ORDER BY id DESC")
    dados_mov = cursor.fetchall()
    df_mov = pd.DataFrame(dados_mov, columns=["Código", "Nome", "Tipo", "Quantidade", "Data/Hora"])

    caminho = "estoque_export.xlsx"
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df_estoque.to_excel(writer, sheet_name="Estoque", index=False)
        df_mov.to_excel(writer, sheet_name="Movimentações", index=False)
    
    conn.close()
    return send_file(caminho, as_attachment=True)

# ---------- Inicialização ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
