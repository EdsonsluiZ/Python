#!/usr/bin/env python3
"""Validador PD: triagem conservadora de domínios .com.br e marcas.
Não declara disponibilidade com base apenas em RDAP 404.
"""
import csv
import socket
import secrets
import json
import queue
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_DIR = Path.home() / '.validador_pd'
APP_DIR.mkdir(exist_ok=True)
DB = APP_DIR / 'consultas.sqlite3'
UA = 'ValidadorPD/1.1 (ISAVAIL oficial + RDAP complementar)'
ISAVAIL_HOST = 'avail.registro.br'
ISAVAIL_PORT = 43

def db_init():
    with sqlite3.connect(DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS consultas(id INTEGER PRIMARY KEY,
          instante_utc TEXT NOT NULL, nome TEXT NOT NULL, dominio TEXT NOT NULL,
          status TEXT NOT NULL, http_status INTEGER, evidencia TEXT,
          resposta_json TEXT, inpi_status TEXT NOT NULL)''')

def slug(name):
    name = unicodedata.normalize('NFKD', name.strip().lower())
    name = ''.join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r'[^a-z0-9-]', '', name.replace(' ', ''))
    return name

def validate_domain(label):
    return bool(2 <= len(label) <= 26 and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', label)
                and not label.isdigit())

def rdap_check(domain):
    url = 'https://rdap.registro.br/domain/' + urllib.parse.quote(domain, safe='.')
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rdap+json, application/json'})
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            code = response.status
            raw = response.read(150_000).decode('utf-8', errors='replace')
            data = json.loads(raw)
            if code == 200 and isinstance(data, dict) and data.get('ldhName'):
                return ('REGISTRADO (RDAP)', code, 'RDAP retornou objeto de domínio.', raw)
            return ('INCONCLUSIVO', code, 'Resposta inesperada do RDAP.', raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read(15_000).decode('utf-8', errors='replace')
        if exc.code == 404:
            return ('NÃO LOCALIZADO NO RDAP', 404,
                    '404 NÃO confirma disponibilidade. Verifique no Registro.br/ISAVAIL.', raw)
        if exc.code == 429:
            return ('INCONCLUSIVO', 429, 'Limite de consultas do RDAP. Aguarde.', raw)
        return ('INCONCLUSIVO', exc.code, 'Erro HTTP do RDAP.', raw)
    except (TimeoutError, urllib.error.URLError, ValueError, OSError) as exc:
        return ('INCONCLUSIVO', None, f'Falha de rede/resposta: {exc}', '')

ISAVAIL_CODES = {
    0: 'DISPONÍVEL (ISAVAIL)',
    1: 'DISPONÍVEL COM RESSALVAS',
    2: 'REGISTRADO (ISAVAIL)',
    3: 'INDISPONÍVEL (ISAVAIL)',
    4: 'CONSULTA INVÁLIDA',
    5: 'AGUARDANDO LIBERAÇÃO',
    6: 'PROCESSO DE LIBERAÇÃO',
    7: 'PROCESSO COMPETITIVO',
    8: 'LIMITE DE CONSULTAS',
    9: 'PROCESSO COMPETITIVO',
}

def parse_isavail(raw, qid):
    """Interpreta apenas códigos conhecidos; preserva resposta integral."""
    lines=[line.strip() for line in raw.splitlines() if line.strip()]
    for line in lines:
        if line.startswith('CK '):
            parts=line.split()
            if len(parts)>=3 and parts[2]==str(qid) and re.fullmatch(r'[a-fA-F0-9]{8,128}',parts[1]):
                return ('COOKIE',None,'Desafio de cookie ISAVAIL.',parts[1])
            return ('INCONCLUSIVO',None,'Cookie inesperado ou QID divergente.',None)
        if line.startswith('ST '):
            parts=line.split()
            if len(parts)<3 or parts[2]!=str(qid):
                return ('INCONCLUSIVO',None,'Identificador da resposta não corresponde à consulta.',None)
            try: code=int(parts[1])
            except ValueError: return ('INCONCLUSIVO',None,'Código ISAVAIL inválido.',None)
            return (ISAVAIL_CODES.get(code,'INCONCLUSIVO'),code,'Código oficial ISAVAIL ST '+str(code),None)
    return ('INCONCLUSIVO',None,'Resposta sem CK/ST reconhecível.',None)

def isavail_check(domain):
    """Consulta UDP com cookie anti-spoofing, timeout e sem retries agressivos."""
    qid=secrets.randbelow(900000000)+100000000
    cookie='0'
    responses=[]
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(7)
            sock.connect((ISAVAIL_HOST,ISAVAIL_PORT))
            for attempt in range(3):
                # Versão 2, idioma português, campo suggest obrigatório.
                packet=f'2 {cookie} 1 {qid} {domain} 0\n'.encode('ascii')
                sock.send(packet)
                raw=sock.recv(8192).decode('latin-1',errors='replace')
                responses.append(raw)
                status,code,detail,new_cookie=parse_isavail(raw,qid)
                if status=='COOKIE':
                    cookie=new_cookie
                    continue
                return status,code,detail,'\n--- RESPOSTA ISAVAIL ---\n'.join(responses)
        return 'INCONCLUSIVO',None,'Número máximo de desafios ISAVAIL excedido.','\n--- RESPOSTA ISAVAIL ---\n'.join(responses)
    except (socket.timeout, OSError, UnicodeError) as exc:
        return 'INCONCLUSIVO',None,'ISAVAIL indisponível ou UDP/43 bloqueado: '+str(exc),'\n--- RESPOSTA ISAVAIL ---\n'.join(responses)

def combined_check(domain):
    status,code,evidence,raw=isavail_check(domain)
    # Consulta RDAP apenas quando não existe conclusão confiável no ISAVAIL.
    if status in ('INCONCLUSIVO','CONSULTA INVÁLIDA'):
        rdap_status,http,rdap_evidence,rdap_raw=rdap_check(domain)
        if rdap_status=='REGISTRADO (RDAP)':
            return rdap_status,code,'ISAVAIL inconclusivo; RDAP confirmou registro. '+evidence,raw+'\n--- RDAP ---\n'+rdap_raw
        return 'INCONCLUSIVO',code,evidence+'; RDAP: '+rdap_status+'. '+rdap_evidence,raw+'\n--- RDAP ---\n'+rdap_raw
    return status,code,evidence,raw

def save_result(record):
    with sqlite3.connect(DB) as con:
        con.execute('''INSERT INTO consultas(instante_utc,nome,dominio,status,http_status,evidencia,resposta_json,inpi_status)
                       VALUES(?,?,?,?,?,?,?,?)''', record)

def export_csv():
    target = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile='validador_pd.csv')
    if not target: return
    with sqlite3.connect(DB) as con:
        rows = con.execute('SELECT instante_utc,nome,dominio,status,http_status,evidencia,inpi_status FROM consultas ORDER BY id DESC').fetchall()
    with open(target,'w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,delimiter=';')
        writer.writerow(['Data UTC','Nome','Domínio','Resultado ISAVAIL/RDAP','Código ST','Evidência','INPI'])
        writer.writerows(rows)
    messagebox.showinfo('Exportação',f'{len(rows)} registros exportados.')

class UI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Validador PD v1.1 | ISAVAIL + RDAP')
        self.geometry('1100x680')
        self.q=queue.Queue()
        self.busy=False
        ttk.Label(self,text='Nomes candidatos (um por linha)',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=16,pady=(16,5))
        self.names=tk.Text(self,height=6)
        self.names.pack(fill='x',padx=16)
        bar=ttk.Frame(self);bar.pack(fill='x',padx=16,pady=10)
        self.start=ttk.Button(bar,text='Consultar ISAVAIL + RDAP',command=self.run);self.start.pack(side='left')
        ttk.Button(bar,text='Exportar histórico CSV',command=export_csv).pack(side='left',padx=8)
        ttk.Button(bar,text='Abrir pesquisa oficial Registro.br',command=lambda:self.open_link('https://registro.br/busca-dominio/')).pack(side='left',padx=8)
        ttk.Button(bar,text='Abrir busca INPI',command=lambda:self.open_link('https://servicos.busca.inpi.gov.br/')).pack(side='left',padx=8)
        self.progress=ttk.Label(self,text='Pronto.');self.progress.pack(anchor='w',padx=16)
        cols=('nome','dominio','rdap','inpi','evidencia')
        self.tree=ttk.Treeview(self,columns=cols,show='headings')
        for c,title,width in [('nome','Nome',140),('dominio','Domínio',210),('rdap','Registro.br',195),('inpi','INPI',170),('evidencia','Interpretação',400)]:
            self.tree.heading(c,text=title);self.tree.column(c,width=width,anchor='w')
        self.tree.pack(fill='both',expand=True,padx=16,pady=8)
        self.tree.bind('<Double-1>',self.open_selected)
        ttk.Label(self,text='ISAVAIL é a fonte principal. RDAP 404 não confirma disponibilidade. INPI continua exigindo pesquisa oficial.\nResultados são pontuais; disponibilidade pode mudar antes do registro.',foreground='#8a4400').pack(anchor='w',padx=16,pady=(0,14))
        self.after(150,self.drain)
    def open_link(self,url):
        import webbrowser
        webbrowser.open(url)
    def open_selected(self,event):
        sel=self.tree.selection()
        if sel:self.open_link('https://registro.br/busca-dominio/')
    def run(self):
        if self.busy:return
        names=list(dict.fromkeys(x.strip() for x in self.names.get('1.0','end').splitlines() if x.strip()))
        if not names:messagebox.showwarning('Nomes','Informe ao menos um nome.');return
        if len(names)>50:messagebox.showwarning('Limite','Máximo de 50 nomes por lote.');return
        self.busy=True;self.start.configure(state='disabled')
        self.progress.configure(text=f'Iniciando {len(names)} consultas...')
        threading.Thread(target=self.worker,args=(names,),daemon=True).start()
    def worker(self,names):
        for i,name in enumerate(names,1):
            label=slug(name)
            domain=label+'.com.br'
            if not validate_domain(label):
                status,code,evidence,raw='INVÁLIDO',None,'Nome incompatível com regras básicas de domínio .br.',''
            else:
                status,code,evidence,raw=combined_check(domain)
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            record=(now,name,domain,status,code,evidence,raw,'PESQUISA MANUAL PENDENTE')
            save_result(record)
            self.q.put(('result',name,domain,status,'PENDENTE',evidence,i,len(names)))
            if status=='LIMITE DE CONSULTAS':
                self.q.put(('halt',))
                break
            if i<len(names):time.sleep(2)
        self.q.put(('done',))
    def drain(self):
        try:
            while True:
                event=self.q.get_nowait()
                if event[0]=='result':
                    _,name,domain,status,inpi,evidence,i,total=event
                    self.tree.insert('','end',values=(name,domain,status,inpi,evidence))
                    self.progress.configure(text=f'{i}/{total} consultas concluídas')
                else:
                    self.busy=False;self.start.configure(state='normal')
                    self.progress.configure(text='Consulta interrompida por limite do serviço.' if event[0]=='halt' else 'Concluído. Pesquise também as marcas no INPI.')
        except queue.Empty:pass
        self.after(150,self.drain)

if __name__=='__main__':
    db_init()
    UI().mainloop()
