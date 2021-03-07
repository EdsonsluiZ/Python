# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


# Abaixo a definição de variáveis Globais e Locais

x = 10 # Difinindo uma variável Global

def main(args):
    imprime_global_inicial()
    modifica_global()
    imprime_local()
    imprime_global()

    return 0

def imprime_global_inicial():
    print("Inicialmente o Valor Gobal é: ", x)

def modifica_global():
    global x
    x = 120

def imprime_local():
    x = 5 # Está é uma variável local
    print("Valor Local: ", x)

def imprime_global():
    print("Valor Gobal: ", x)


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))



# import app_data
# versao = app_data.__version__
# aplicacao = app_data.__application__
#  Podemos ler ou escrever sobre estas variáveis:
# app_data.__version__= "0.2"