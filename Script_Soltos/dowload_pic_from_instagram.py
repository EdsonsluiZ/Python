# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

#pip install instaloader

import instaloader

app = instaloader.Instaloader()
user_name = input("User Name: ")
app.download_profile(user_name, profile_pic_only=True)
