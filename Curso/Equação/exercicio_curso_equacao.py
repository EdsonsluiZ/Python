# -*- coding: utf-8 -*-

# a2 + bx + c
# (-b +- sqtr(b2-4ac))/2

import math

a = float(input("Digita o valor de a: "))
b = float(input("Digite o valor de b: "))
c = float(input("Digite o valor de c: "))

delta = (b**2) - (4*a*c)
raiz_delta = float(math.sqrt (delta))

x1 = (-b + raiz_delta)/(2*a)
x2 = (-b - raiz_delta)/(2*a)

print ("x1 = %d") %x1
print ("x2 = %d") %x2

# continua = input("Deseja Sair? Digite Q ou ENTER para novo Cálculo:")
#    if (continua == "q" or "Q"):
#        break