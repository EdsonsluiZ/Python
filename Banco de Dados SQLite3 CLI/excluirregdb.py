# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import sqlite3

def excluirregistro():
    # Abre conexao com o Banco de Dados
    conn = sqlite3.connect ('dbUersGBD.db')
    cursor = conn.cursor()

    # Lista registros para escolher o excluído
    cursor.execute("""
    SELECT * from usuarios;
    """)
    for linha in cursor.fetchall():
        print(linha)

    print("")
    print("Digite o ID que deverá ser excluído do BD:")
    dbregistro = input("ID Registro: ")
    
    if (dbregistro == ""):
        print("Preencha o campo!")
    else:
        cursor.execute("DELETE FROM usuarios where idusuario=(?)", (dbregistro,))
        conn.commit()
        print("Sucessful Account Deleted")
        cursor.fetchall()
        conn.close() 
        
