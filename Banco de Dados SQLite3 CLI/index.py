# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


import sqlite3 # Importar módulo de estrutura de Banco de Dados SQLite3
import criarregdb # Importa o módulo de criação de Banco
import verregdb # Importa o Módulo de visualização da tabela
import excluirregdb # Importa o módulo de Exclusão de Registros
import time


escolha1 = ""

while escolha1 != "4":
    print("Gerenciamento de Banco de Dados - dbUersGBD.db")
    print("")
    print("(1) Criar novo Registro no Banco de Dados")
    print("(2) Ver Registros do Banco de Dados")
    print("(3) Deletar Registro no Banco de Dados")
    print("(4) Sair do Programa")
    escolha1 = input("Escolha um Número: ")
    if escolha1 != "1" and escolha1 != "2" and escolha1 != "3" and escolha1 != "4":
        print("Escolha um Número correto!!!")
        time.sleep(1)
    elif escolha1 == "1":
        print("Você escolheu Criar novo Registro no Banco de Dados")
        time.sleep(1)
        criarregdb.crianovodb()
    elif escolha1 == "2":
        print("Você escolheu Ver todos os Registros do Banco de Dados")
        time.sleep(1)
        verregdb.vertodosregdb()
    elif escolha1 == "3":
        print("Você escolheu Deletar um Registro do Banco de Dados")
        time.sleep(1)
        excluirregdb.excluirregistro()
    else:
        print("Voce escolheu encerrar o Programa!")
        time.sleep(1)
        quit()
