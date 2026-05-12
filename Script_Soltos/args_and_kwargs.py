# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

#Simple Function
def greet_(name, age):
    print(f"{name}, You are {age}`years old.")

greet_("Mister", 20)


#Args
def data(*args):
    print ("All Data:")
    for datas in args:
        print(datas)

data("codeSwiftz", "Coding", "Ai")

# Kwargs
def info(**kwargs):
    print("INFO : ")
    for key, value in kwargs.items():
        print(f"{key} : {value}")


info(Name = "CodeSwiftz", Age = "20", Subject = "CS")