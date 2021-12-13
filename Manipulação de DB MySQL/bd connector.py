# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import mysql.connector

con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")

if con.is_connected():
    db_info = con.get_server_info()
    print("Conectado ao Servidor MySQL versão ", db_info)
    cursor = con.cursor()
    cursor.execute("select database();")
    linha = cursor.fetchone()
    print("Conectado ao Banco de Dados ",linha)

if con.is_connected():
    cursor.close()
    con.close()
    print("Conexão ao MySQL foi encerrada!")

