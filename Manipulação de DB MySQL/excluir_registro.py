# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

from typing import final
import mysql.connector
from mysql.connector.errors import Error

# Excluir Registro no Banco de Dados

def conectar():
    try:
        global con
        con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")
    except Error as erro:
        print("Erro de conexão: ", erro)

def consulta():
    try:
        conectar()
        consulta_sql = "select * from tbl_produtos"
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

def excluir():
    try:
        conectar()
        exclui_registro = "DELETE FROM tbl_produtos WHERE IdProduto = " + idProd
        cursor = con.cursor()
        cursor.execute(exclui_registro)
        con.commit()
        print("Registro excluído com Sucesso!")
    except Error as erro:
        print("Falha ao excluir dados na Tabela: {}".format(erro))
    finally:
        if(con.is_connected()):
            cursor.close()
            con.close()

def excluir_reg():
    print("Excluir Produtos no Banco de dados")
    print("Entre com os dados conforme solicitado:")
    
    consulta()
    
    print("\n Digite o código do produto a ser Excluído:")
    global idProd
    idProd = input("Id do Produto: ")

    
if __name__=="__main__":

    excluir_reg()
    excluir()    
            
    continua = input("\n Deseja excluir outro Registro? s=sim | n=não")
    if (continua == "s"):
        excluir_reg()
        excluir()
    else:
        print("Até Logo!")