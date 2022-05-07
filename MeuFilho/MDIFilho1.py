# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import wx

class MDIFilho1(wx.MDIChildFrame):

	def __init__(self,parent):
		wx.MDIChildFrame.__init__(self,parent,title='Janela Filho 1',size = wx.Size(200,250))
		menu = parent.GetWindowMenu()
		menu.Append(5500, "&Filho 01")

