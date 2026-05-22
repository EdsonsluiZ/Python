# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


import mysql.connector


conexao = mysql.connector.connect(
    host="dbride.mysql.dbaas.com.br",
    port=3306,
    user="dbride",
    password="DbRide!@0126",
    database="dbride"
)

cursor = conexao.cursor()