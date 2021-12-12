# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import sqlite3


def vertodosregdb():
    # Abre conexao com o Banco de Dados
    conn = sqlite3.connect ('dbUersGBD.db')
    cursor = conn.cursor()


    cursor.execute("""
    SELECT * from usuarios;
    """)
    for linha in cursor.fetchall():
        print(linha)

    print("Sucessful Show Itens")
    conn.close()