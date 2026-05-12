# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


import pywhatkit

phone = input("Enter Phone Number (+countrycode): ")
msg = input("Enter Message: ")
hour = int(input("Enter Hour (24-Hour format): "))
minute = int(input ("Enter Minute: "))

pywhatkit.sendwhatmsg(phone, msg, hour, minute)

print("Message Schedule Successfully")