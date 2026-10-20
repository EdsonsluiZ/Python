import unittest
from unittest.mock import patch
import validador_pd as m

class Tests(unittest.TestCase):
 def test_status(self):
  self.assertEqual(m.parse_isavail('% Copyright Nic.br\nST 0 123\n',123)[0],'DISPONÍVEL (ISAVAIL)')
  self.assertEqual(m.parse_isavail('ST 2 123\n',123)[0],'REGISTRADO (ISAVAIL)')
  self.assertEqual(m.parse_isavail('ST 8 123\n',123)[0],'LIMITE DE CONSULTAS')
 def test_cookie(self):
  self.assertEqual(m.parse_isavail('CK 1234567890abcdef 123',123)[3],'1234567890abcdef')
 def test_mismatch(self):
  self.assertEqual(m.parse_isavail('ST 0 321',123)[0],'INCONCLUSIVO')
 def test_fallback(self):
  with patch.object(m,'isavail_check',return_value=('INCONCLUSIVO',None,'timeout','')),patch.object(m,'rdap_check',return_value=('NÃO LOCALIZADO NO RDAP',404,'não confirma','')):
   self.assertEqual(m.combined_check('exemplo.com.br')[0],'INCONCLUSIVO')

if __name__=='__main__': unittest.main()
