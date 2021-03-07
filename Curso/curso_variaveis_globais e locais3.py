# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


# Abaixo a definição de variáveis Globais e Locais

import curso_app_data

versao = curso_app_data.__version__ # Le Informação no arquivo e alimenta variável global
aplicacao = curso_app_data.__application__ # Le Informação no arquivo e alimenta variável global
x = 10 # Difinindo uma variável Global

def main(args):
    imprime_global_inicial()
    modifica_global()
    imprime_local()
    imprime_global()

    return 0

def imprime_global_inicial():
    import curso_app_data
    versao = curso_app_data.__version__
    aplicacao = curso_app_data.__application__
    print("Inicialmente o Valor Gobal é: ", x)
    print("A Versão do Sistema é: ", versao)
    print("Aplicação: ", aplicacao)

def modifica_global():
    global versao
    global x
    x = 120
    versao = curso_app_data.__version__= "2.0"


def imprime_local():
    x = 5 # Está é uma variável local
    print("Valor Local: ", x)

def imprime_global():
    print("Valor Gobal: ", x)
    print("Versão: ", versao)


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
