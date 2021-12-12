# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import sqlite3

def crianovodb():
    # Abre conexao com o Banco de Dados
    conn = sqlite3.connect ('dbUersGBD.db')
    cursor = conn.cursor()

    # Cria variáveis globais
    print("Digite as informações abaixo para serem inseridas no BD:")
    dbnome = input("Nome: ")
    dbemail = input("E-Mail: ")
    dblogin = input("Login: ")
    dbsenha = input("Senha: ")
    dbstatus = input("Status (A)tivo / (I)nativo: ")
    if dbstatus.upper == 'A': # Testa status para transformar o valor em Boolean
        dbstatus = True
    else:
        print("Você digitou: ", dbstatus)
        dbstatus = False

    dbadministrador = input("Administrador? (S/N): ")
    if dbadministrador.upper == 'S': # Testa adminstrador para transformar o valor em Boolean
        dbadministrador = True
    else:
        print("Você digitou: ", dbadministrador)
        dbadministrador = False


    if (dbnome == "" or dbemail == "" or dblogin == "" or dbsenha == ""):
        print("Preencha todas os campos!")
    else:
        cursor.execute("""
        INSERT INTO usuarios(nome, email, login, senha, status, administrador) VALUES (?, ?, ?, ?, ?, ?)
        """, (dbnome, dbemail, dblogin, dbsenha, dbstatus, dbadministrador))
        conn.commit()
        print("Sucessful Account Created")
        cursor.fetchone()
        
