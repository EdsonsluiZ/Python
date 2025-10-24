# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

#pip install pyttsx3

import pyttsx3 as ptk

pt = ptk.init()
pt.say("Olá Mundo, eu falo português")
pt.runAndWait()
pt.stop()