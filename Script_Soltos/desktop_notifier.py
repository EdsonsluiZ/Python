# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

#pip install py-notifier==0.1.3 win10toast

from pynotifier import Notification
Notification(
    title="Hi There, sou uma Notificação",
    description="Muito Bom  :)",
    icon_path=None,
    duration=10
).send()

