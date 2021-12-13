# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import mysql.connector
from mysql.connector.errors import Error

try:
    # Criar conexão ao banco de dados
    con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")

    consulta_sql = "select * from tbl_produtos"
    cursor = con.cursor()
    cursor.execute(consulta_sql)
    linhas = cursor.fetchall()
    print("Número total de registros retornados: ", cursor.rowcount)
    
    print("\n Mostrando os produtos cadastrados")
    for linha in linhas:
        print("Id:", linha[0])
        print("Nome:", linha[1])
        print("Preco:", linha[2], "\n")
except Error as e:
    print("Erro ao acessar tabela MySQL", e)
finally:
    if (con.is_connected()):
        con.close()
        cursor.close()
        print("Conexão ao MySQL Finalizada!")
        
