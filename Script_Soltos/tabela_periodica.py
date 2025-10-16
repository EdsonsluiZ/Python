# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import periodictable

Atomic_No = int(input("Entre o número Atômico: "))

element = periodictable.elements[Atomic_No]

print("Nome: ", element.name)
print("Simbolo: ", element.symbol)
print("Massa Atômica: ", element.mass)
print("Densidade: ", element.density)


