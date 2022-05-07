# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import wx
from datetime import date
import MDIFilho1
import MDIFilho2

hoje=date.today()
mesporextenso=("Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro")
diadasemana=("Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo")
dia=hoje.day
mes=hoje.month
ano=hoje.year

class MDIFrame(wx.MDIParentFrame):

	def __init__(self):
		wx.MDIParentFrame.__init__(self, None, -1, "MDI Main Window Parent",size=(800,600))

		self.statusbar = self.CreateStatusBar(1, style=wx.STB_SIZEGRIP|wx.STB_ELLIPSIZE_END|wx.FULL_REPAINT_ON_RESIZE)
		self.statusbar.SetStatusText("%s, %d de %s de %d" % (diadasemana[hoje.weekday()],dia,mesporextenso[mes-1],ano))
		self.statusbar.SetToolTip("Data de Hoje!")
        
		menu = wx.Menu()
		menu.Append(5000, "&New Window 1")
		menu.Append(5002, "&New Window 2")
		menu.Append(5001, "E&xit")
		menubar = wx.MenuBar()
		menubar.Append(menu, "&File")
		self.SetMenuBar(menubar)
		self.Bind(wx.EVT_MENU, self.OnNewWindow1, id=5000)
		self.Bind(wx.EVT_MENU, self.OnExit, id=5001)
		self.Bind(wx.EVT_MENU, self.OnNewWindow2, id=5002)
  
	def OnExit(self, evt):
		self.Close(True)

	def OnNewWindow1(self, evt):
		#win = wx.MDIChildFrame(self, -1, "Child Window")
		win = MDIFilho1.MDIFilho1(self)
		win.Show(True)

	def OnNewWindow2(self, evt):
 		#win = wx.MDIChildFrame(self, -1, "Child Window")
		win = MDIFilho2.MDIFilho2(self)
		win.Show(True)



app = wx.PySimpleApp()
frame = MDIFrame()
frame.Show()
app.MainLoop()