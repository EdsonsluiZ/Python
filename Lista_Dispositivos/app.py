# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

""" Monitor local de câmera, redes Wi-Fi e dispositivos Bluetooth — Tkinter """

import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk

from radios import Cancelled, scan_wifi, watch_bluetooth

VERSION = '1.0.1'
BUILD = '20261010-01'

@dataclass
class Job:
    stop: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    state: str = 'idle'
    serial: int = 0


def put_latest(target, item):
    """Uma imagem apenas na fila: memória e latência permanecem limitadas."""
    try:
        target.put_nowait(item)
    except queue.Full:
        try:
            target.get_nowait()
        except queue.Empty:
            pass
        try:
            target.put_nowait(item)
        except queue.Full:
            pass


def camera_worker(stop, send, frames, serial, index):
    try:
        import cv2
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError('Instale as dependências: python -m pip install -r requirements.txt') from exc
    capture = None
    try:
        backends = (cv2.CAP_DSHOW, cv2.CAP_MSMF) if sys.platform == 'win32' else (cv2.CAP_ANY,)
        for backend in backends:
            if stop.is_set():
                raise Cancelled()
            capture = cv2.VideoCapture(index, backend)
            if capture.isOpened():
                break
            capture.release()
            capture = None
        if capture is None:
            raise RuntimeError('Não foi possível abrir a câmera. Verifique o índice, '
                               'as permissões e se outro aplicativo está usando o dispositivo.')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        capture.set(cv2.CAP_PROP_FPS, 24)
        send('status', 'Câmera ativa • transmissão local')
        failures = 0
        while not stop.is_set():
            ok, frame = capture.read()
            if not ok:
                failures += 1
                if failures >= 12:
                    raise RuntimeError('A câmera parou de enviar imagens. Verifique a conexão.')
                stop.wait(0.1)
                continue
            failures = 0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            put_latest(frames, (serial, Image.fromarray(rgb)))
            stop.wait(1 / 30)
    finally:
        if capture is not None:
            capture.release()


class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Monitor de Dispositivos • v{VERSION}')
        self.geometry('1180x740')
        self.minsize(950, 640)
        self.configure(bg='#edf2f7')
        self.jobs = {name: Job() for name in ('camera', 'wifi', 'bluetooth')}
        self.events = queue.Queue()
        self.frames = queue.Queue(maxsize=1)
        self.photo = None
        self.closing = False
        self.close_started = 0
        self.buttons, self.status = {}, {}
        self._style()
        self._build()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(70, self._tick)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 9), background='#edf2f7')
        style.configure('TButton', padding=(12, 6))
        style.configure('TLabelframe', background='#ffffff')
        style.configure('TLabelframe.Label', font=('Segoe UI', 11, 'bold'), background='#edf2f7')
        style.configure('Panel.TFrame', background='#ffffff')
        style.configure('Panel.TLabel', background='#ffffff', foreground='#334155')
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), foreground='#0f172a')
        style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', rowheight=26)
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))
        style.map('Treeview', background=[('selected', '#2563eb')], foreground=[('selected', 'white')])

    def _build(self):
        header = ttk.Frame(self, padding=(18, 14, 18, 10))
        header.pack(fill='x')
        ttk.Label(header, text='Monitor de Dispositivos', style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text='Câmera, Wi-Fi e Bluetooth • controles independentes').pack(anchor='w', pady=(4, 0))
        content = ttk.Frame(self, padding=(16, 4, 16, 12))
        content.pack(fill='both', expand=True)
        content.columnconfigure(0, weight=4, minsize=330)
        content.columnconfigure(1, weight=6, minsize=550)
        content.rowconfigure(0, weight=1)

        camera = ttk.LabelFrame(content, text='  Câmera  ', padding=12)
        camera.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        controls = ttk.Frame(camera, style='Panel.TFrame')
        controls.pack(fill='x')
        ttk.Label(controls, text='Índice:', style='Panel.TLabel').pack(side='left')
        self.camera_index = tk.StringVar(value='0')
        self.camera_spin = ttk.Spinbox(controls, from_=0, to=20, textvariable=self.camera_index, width=3)
        self.camera_spin.pack(side='left', padx=(6, 10))
        self.buttons['camera'] = ttk.Button(controls, text='Ativar câmera', command=lambda: self.toggle('camera'))
        self.buttons['camera'].pack(side='right')
        self.preview = tk.Label(camera, text='Câmera desativada', bg='#0f172a', fg='#cbd5e1',
                                font=('Segoe UI', 12), borderwidth=0)
        self.preview.pack(fill='both', expand=True, pady=12)
        self.status['camera'] = tk.StringVar(value='Pronto • câmera 0 é normalmente a câmera principal.')
        ttk.Label(camera, textvariable=self.status['camera'], style='Panel.TLabel',
                  wraplength=340).pack(fill='x')

        right = ttk.Frame(content)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        wifi = ttk.LabelFrame(right, text='  Wi-Fi  ', padding=12)
        wifi.grid(row=0, column=0, sticky='nsew', pady=(0, 12))
        toolbar = ttk.Frame(wifi, style='Panel.TFrame')
        toolbar.pack(fill='x')
        self.wifi_count = tk.StringVar(value='0 pontos de acesso')
        ttk.Label(toolbar, textvariable=self.wifi_count, style='Panel.TLabel').pack(side='left')
        self.buttons['wifi'] = ttk.Button(toolbar, text='Exibir redes', command=lambda: self.toggle('wifi'))
        self.buttons['wifi'].pack(side='right')
        self.wifi_table = self._table(wifi, [
            ('ssid', 'Rede (SSID)', 160), ('address', 'BSSID', 135),
            ('rssi', 'RSSI (dBm)', 83), ('signal', 'Sinal', 78),
            ('quality', 'Qualidade', 78), ('frequency', 'MHz', 75)])
        for tag, color in [('Excelente', '#166534'), ('Bom', '#15803d'),
                           ('Regular', '#a16207'), ('Fraco', '#b91c1c')]:
            self.wifi_table.tag_configure(tag, foreground=color)
        self.status['wifi'] = tk.StringVar(value='Oculto • atualização automática enquanto exibido.')
        ttk.Label(wifi, textvariable=self.status['wifi'], style='Panel.TLabel', wraplength=550).pack(fill='x')
        ttk.Label(wifi, text='dBm: quanto mais próximo de zero, mais forte o sinal.',
                  style='Panel.TLabel').pack(anchor='w', pady=(4, 0))

        bluetooth = ttk.LabelFrame(right, text='  Bluetooth BLE • sinais recebidos  ', padding=12)
        bluetooth.grid(row=1, column=0, sticky='nsew')
        toolbar = ttk.Frame(bluetooth, style='Panel.TFrame')
        toolbar.pack(fill='x')
        self.bt_count = tk.StringVar(value='0 dispositivos BLE recentes')
        ttk.Label(toolbar, textvariable=self.bt_count, style='Panel.TLabel').pack(side='left')
        self.buttons['bluetooth'] = ttk.Button(toolbar, text='Buscar dispositivos', command=lambda: self.toggle('bluetooth'))
        self.buttons['bluetooth'].pack(side='right')
        self.bt_table = self._table(bluetooth, [
            ('name', 'Dispositivo', 150), ('address', 'Endereço', 135),
            ('kind', 'Tipo', 70), ('rssi', 'RSSI (dBm)', 85), ('status', 'Último sinal', 100)])
        self.status['bluetooth'] = tk.StringVar(value='Parado • escuta de anúncios BLE pelo adaptador.')
        ttk.Label(bluetooth, textvariable=self.status['bluetooth'], style='Panel.TLabel', wraplength=550).pack(fill='x')
        ttk.Label(bluetooth, text='Somente BLE anunciando • remove após 10 s sem sinal • clássico não incluído.',
                  style='Panel.TLabel', wraplength=550).pack(anchor='w', pady=(4, 0))
        ttk.Label(self, text=f'Desenvolvido por: Projetos Design Consultorias • v{VERSION} • Build {BUILD}',
                  anchor='center').pack(fill='x', pady=(0, 8))

    @staticmethod
    def _table(parent, columns):
        box = ttk.Frame(parent, style='Panel.TFrame')
        box.pack(fill='both', expand=True, pady=(10, 8))
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        table = ttk.Treeview(box, columns=[col[0] for col in columns], show='headings', height=5)
        for name, title, width in columns:
            table.heading(name, text=title)
            table.column(name, width=width, minwidth=60, stretch=name in ('ssid', 'name'))
        scroll_y = ttk.Scrollbar(box, orient='vertical', command=table.yview)
        scroll_x = ttk.Scrollbar(box, orient='horizontal', command=table.xview)
        table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        table.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')
        return table

    def toggle(self, name):
        job = self.jobs[name]
        if self.closing or job.state == 'stopping':
            return
        if job.state == 'running':
            job.state = 'stopping'
            job.stop.set()
            self.buttons[name].configure(state='disabled', text='Parando…')
            self.status[name].set('Parando • aguardando liberação do dispositivo…')
            self._clear(name)
            return
        index = 0
        if name == 'camera':
            try:
                index = int(self.camera_index.get())
                if not 0 <= index <= 20:
                    raise ValueError()
            except ValueError:
                self.status[name].set('Informe um índice de câmera inteiro entre 0 e 20.')
                return
            self.camera_spin.configure(state='disabled')
        job.stop = threading.Event()
        job.serial += 1
        job.state = 'running'
        self.buttons[name].configure(text={'camera': 'Desativar câmera', 'wifi': 'Não exibir redes',
                                          'bluetooth': 'Parar busca'}[name])
        self.status[name].set('Iniciando…')
        job.thread = threading.Thread(target=self._run, args=(name, job.stop, job.serial, index),
                                      name=f'monitor-{name}', daemon=True)
        job.thread.start()

    def _run(self, name, stop, serial, index):
        def send(kind, payload):
            self.events.put((name, serial, kind, payload))
        try:
            if name == 'camera':
                camera_worker(stop, send, self.frames, serial, index)
            elif name == 'bluetooth':
                send('status', 'Iniciando escuta contínua de anúncios BLE…')

                def received(rows):
                    if not stop.is_set():
                        send('rows', (rows, [], time.strftime('%H:%M:%S')))

                watch_bluetooth(stop, received)
            else:
                while not stop.is_set():
                    send('status', 'Buscando redes…')
                    rows, warnings = scan_wifi(stop)
                    if stop.is_set():
                        break
                    send('rows', (rows, warnings, time.strftime('%H:%M:%S')))
                    # Intervalo após a conclusão, nunca sobrepõe varreduras do mesmo rádio.
                    if stop.wait(8):
                        break
        except Cancelled:
            pass
        except Exception as exc:
            send('error', str(exc))
        finally:
            send('done', None)

    def _clear(self, name):
        if name == 'camera':
            self.preview.configure(image='', text='Câmera desativada')
            self.photo = None
            return
        table = self.wifi_table if name == 'wifi' else self.bt_table
        table.delete(*table.get_children())
        (self.wifi_count if name == 'wifi' else self.bt_count).set(
            '0 pontos de acesso' if name == 'wifi' else '0 dispositivos BLE recentes')

    def _render_rows(self, name, payload):
        rows, warnings, stamp = payload
        self._clear(name)
        table = self.wifi_table if name == 'wifi' else self.bt_table
        for row in rows:
            if name == 'wifi':
                table.insert('', 'end', values=(row['ssid'], row['address'], row['rssi'], row['signal'],
                                                f"{row['quality']}%", row['frequency']), tags=(row['signal'],))
            else:
                table.insert('', 'end', values=(row['name'], row['address'], row['kind'],
                                                row['rssi'] if row['rssi'] is not None else '—', row['status']))
        count = self.wifi_count if name == 'wifi' else self.bt_count
        count.set(f'{len(rows)} pontos de acesso' if name == 'wifi' else f'{len(rows)} dispositivos BLE recentes')
        message = (f'Última busca: {stamp} • aguardando próxima atualização.' if name == 'wifi'
                   else f'Escuta BLE ativa • {stamp} • anúncios recebidos nos últimos 10 s.')
        if warnings:
            message = f'Busca parcial às {stamp}: ' + ' | '.join(warnings)
        self.status[name].set(message)

    def _tick(self):
        for _ in range(100):
            try:
                name, serial, kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            job = self.jobs[name]
            if serial != job.serial:
                continue
            if kind == 'done':
                stopped = job.state == 'stopping'
                job.state = 'idle'
                self.buttons[name].configure(state='normal', text={
                    'camera': 'Ativar câmera', 'wifi': 'Exibir redes',
                    'bluetooth': 'Buscar dispositivos'}[name])
                if name == 'camera':
                    self.camera_spin.configure(state='normal')
                    self._clear(name)
                if stopped:
                    self.status[name].set('Desativado.' if name == 'camera' else 'Busca parada • lista limpa.')
            elif job.state == 'running' and not self.closing:
                if kind in ('error', 'status'):
                    if kind == 'error':
                        self._clear(name)
                    self.status[name].set(('Erro: ' if kind == 'error' else '') + payload)
                elif kind == 'rows':
                    self._render_rows(name, payload)
        try:
            serial, image = self.frames.get_nowait()
            job = self.jobs['camera']
            if job.state == 'running' and serial == job.serial and not self.closing:
                from PIL import Image, ImageTk
                width, height = max(self.preview.winfo_width(), 2), max(self.preview.winfo_height(), 2)
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(image)
                self.preview.configure(image=self.photo, text='')
        except queue.Empty:
            pass
        if self.closing:
            alive = any(job.thread and job.thread.is_alive() for job in self.jobs.values())
            if not alive or time.monotonic() - self.close_started >= 15:
                self.destroy()
                return
        self.after(70, self._tick)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.close_started = time.monotonic()
        self.title('Encerrando • liberando dispositivos…')
        for name, job in self.jobs.items():
            job.stop.set()
            self.buttons[name].configure(state='disabled')
            self._clear(name)


if __name__ == '__main__':
    MonitorApp().mainloop()
