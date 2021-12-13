# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import mysql.connector
from mysql.connector.errors import Error

#Inserir Registros
print("Rotina para cadsatro de produtos no Banco de Dados!")
print("Entre com os dados conforme solicitado!")

idProd = input("ID do Produto: ")
nomeProd = input("Nome do Produto: ")
precoProd = input("Preço: ")
quantProd = input("Quantidade: ")

dados = idProd + ',\'' + nomeProd + '\',' + precoProd + ',' + quantProd +')'
declaracao = """INSERT INTO tbl_produtos
                                (IdProduto, NomeProduto, Preco, Quantidade)
                            VALUES ("""

sql = declaracao + dados

try:
    # Criar conexão ao banco de dados
    con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")

    inserir_produtos = sql
                            
    cursor = con.cursor()
    cursor.execute(inserir_produtos)
    con.commit()
    print(cursor.rowcount, "Registros inseridos da tabela!")
    cursor.close()
except Error as e:
    print("Erro ao acessar tabela MySQL", e)
finally:
    if (con.is_connected()):
        con.close()
        cursor.close()
        print("Conexão ao MySQL Finalizada!")    
