# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

from typing import final
import mysql.connector
from mysql.connector.errors import Error

# Atualizar Registro no Banco de Dados

def conectar():
    try:
        global con
        con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")
    except Error as erro:
        print("Erro de conexão: ", erro)

def consulta(idProd):
    try:
        conectar()
        consulta_sql = "select * from tbl_produtos where IdProduto = " + idProd
        cursor = con.cursor()
        cursor.execute(consulta_sql)
        linhas = cursor.fetchall()
        
        for linha in linhas:
            print("Id:", linha[0], "| Produto:", linha[1], "| Preço:", linha[2])
    except Error as erro:
        print("Falha ao consultar a tabela: {}".format(erro))
    finally:
        if(con.is_connected()):
            cursor.close()
            con.close()

def atualiza(declaracao):
    try:
        conectar()
        altera_preco = declaracao
        cursor = con.cursor()
        cursor.execute(altera_preco)
        con.commit()
        print("Preço alterado com Sucesso!")
    except Error as erro:
        print("Falha ao inserir dados na Tabela: {}".format(erro))
    finally:
        if(con.is_connected()):
            cursor.close()
            con.close()

if __name__=="__main__":
    
    print("Atualizar preço de Produtos no Banco de dados")
    print("Entre com os dados conforme solicitado:")
    
    print("\n Digite o código do produto a alterar:")
    idProd = input("Id do Produto: ")
    
    consulta(idProd)
    
    print("\n Entre com o novo Preço do Produto:")
    precoProd = input("Preço: ")
    
    declaracao = """UPDATE tbl_produtos
    SET Preco = """ + precoProd + """
    WHERE IdProduto = """ + idProd
        
    # Atualiza registro no Banco de Dados
    
    atualiza(declaracao)
    
    verifica = input("\n Deseja consultar a atualização? s=sim | n=não")
    if (verifica == "s"):
        consulta(idProd)
    else:
        print("Até Logo!")
        
