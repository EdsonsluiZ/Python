# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

from wifi_qrcode_generator import wifi_qrcode

qr_code = wifi_qrcode(
    ssid="clcoding",
    hidden=False,
    authentication_type="WPA",
    password="Cl@2014"
)

qr_code_img = qr_code.make_image()
qr_code_img.save("wifi_qr_code.png")

