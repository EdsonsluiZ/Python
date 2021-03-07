# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


# Abaixo a definição de variáveis Globais e Locais

x = 10 # Difinindo uma variável Global

def main(args):
    imprime_local()
    imprime_global()

    return 0

def imprime_local():
    x = 5 # Está é uma variável local
    print("Valor Local: ", x)

def imprime_global():
    print("Valor Gobal: ", x)


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
    