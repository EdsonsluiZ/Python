# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import mysql.connector

try:
    # Criar conexão ao banco de dados
    con = mysql.connector.connect(host="192.168.1.75", database="Teste_1", user="root", password="toor")

    # Declaração SQL
    criar_tabela_SQL = """CREATE TABLE tbl_produtos (
                            IdProduto int(11) NOT NULL,
                            NomeProduto varchar(70) NOT NULL,
                            Preco float NOT NULL,
                            Quantidade tinyint NOT NULL,
                            PRIMARY KEY (IdProduto)) """
                            
    # Criar cursor e executar SQL no banco de dados
    cursor = con.cursor()
    cursor.execute (criar_tabela_SQL)
    print("Tabela de Produtos Criada com Sucesso!")
except mysql.connector.Error as erro:
    print("Falha ao criar tabela no MySQL: {}".format(erro))
finally:
    if (con.is_connected()):
        cursor.close()
        con.close()
        print("Conexão ao MySQL finalizada!")
        print ("\n Próxima Aula: Inserção de Registros na Tabela criada")