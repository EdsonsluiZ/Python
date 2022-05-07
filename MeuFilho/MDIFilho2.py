# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import wx

class MDIFilho2(wx.MDIChildFrame):

 def __init__(self,parent):
		wx.MDIChildFrame.__init__(self,parent,title='Janela Filho 2',size = wx.Size(350,400))
		menu = parent.GetWindowMenu()
		menu.Append(5600, "&Filho 2")


