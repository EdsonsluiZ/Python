# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

"""PD Database Migrator v1.3.2 """
import queue
import re
import threading
import traceback
import time
from pathlib import Path
from credential_vault import save_profiles, load_profiles, delete_profiles, VAULT_PATH
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pymysql
except ImportError:
    pymysql = None

APP_TITLE = 'PD Database Migrator v1.3.2'
TRANSIENT_CODES = {2002, 2003, 2006, 2013, 2055, 1205}


def qi(value):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('Identificador MySQL inválido')
    return '`' + value.replace('`', '``') + '`'


def connect(cfg, readonly=False):
    c = pymysql.connect(host=cfg['host'], port=int(cfg['port']), user=cfg['user'],
                        password=cfg['password'], database=cfg['database'],
                        charset='utf8mb4', connect_timeout=15, read_timeout=180,
                        write_timeout=180, autocommit=False)
    if readonly:
        with c.cursor() as cur:
            cur.execute('SET SESSION TRANSACTION READ ONLY')
    return c


def objects(c):
    with c.cursor() as cur:
        cur.execute('SELECT TABLE_NAME,TABLE_TYPE FROM information_schema.TABLES '
                    'WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME')
        return cur.fetchall()


def count(c, table):
    with c.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM ' + qi(table))
        return int(cur.fetchone()[0])


def ddl(c, table):
    with c.cursor() as cur:
        cur.execute('SHOW CREATE TABLE ' + qi(table))
        return cur.fetchone()[1]


def mysql_error(exc):
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else '?'
    msg = str(exc.args[1]) if len(exc.args) > 1 else type(exc).__name__
    # No passwords are logged; remove potential connection string user/host details.
    msg = re.sub(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s,;]+", r'\1=[OCULTO]', msg)
    return f'MySQL {code}: {msg}'


def ensure_not_same(src, dst):
    if (src['host'].lower().rstrip('.'), src['port'], src['database'].lower()) == (dst['host'].lower().rstrip('.'), dst['port'], dst['database'].lower()):
        raise RuntimeError('Origem e destino apontam para o mesmo servidor e banco. Operação bloqueada.')
    if src['database'].lower() == dst['database'].lower():
        raise RuntimeError('Por segurança, origem e destino devem ter nomes de banco diferentes.')


def clean_destination(c, send):
    """Only called after typed confirmation in the GUI; never drops the database itself."""
    found = objects(c)
    if not found:
        send('Destino já está vazio.')
        return
    send(f'Limpando exclusivamente o banco de destino ({len(found)} objetos)...')
    with c.cursor() as cur:
        cur.execute('SET SESSION FOREIGN_KEY_CHECKS=0')
        for name, typ in found:
            if typ == 'VIEW':
                cur.execute('DROP VIEW IF EXISTS ' + qi(name))
            elif typ == 'BASE TABLE':
                cur.execute('DROP TABLE IF EXISTS ' + qi(name))
            else:
                raise RuntimeError(f'Tipo de objeto inesperado: {typ}')
        cur.execute('SET SESSION FOREIGN_KEY_CHECKS=1')
    c.commit()
    if objects(c):
        raise RuntimeError('Destino ainda contém objetos após a limpeza; migração interrompida.')
    send('Destino limpo e conferido. Banco de origem não foi alterado.')


def recreate_connections(src, dst, src_cfg, dst_cfg, send):
    for c in (src, dst):
        try:
            c.close()
        except Exception:
            pass
    send('Reconectando às duas bases após falha transitória...')
    src = connect(src_cfg, readonly=True)
    dst = connect(dst_cfg)
    with dst.cursor() as cur:
        cur.execute('SET SESSION FOREIGN_KEY_CHECKS=0')
    return src, dst


def copy_table(src, dst, table, index, total_tables, batch_size, send):
    """Paginate SELECT with a regular buffered cursor; never leave SSCursor open."""
    expected = count(src, table)
    copied = 0
    # Explicit stable order avoids OFFSET paging drifting on non-unique sort.
    # Caller must freeze writes to source during migration.
    with src.cursor() as cur:
        cur.execute('SHOW COLUMNS FROM ' + qi(table))
        columns = cur.fetchall()
    ncols = len(columns)
    if not ncols:
        raise RuntimeError(f'Tabela sem colunas: {table}')
    with src.cursor() as cur:
        cur.execute('SHOW INDEX FROM ' + qi(table) + ' WHERE Key_name = %s', ('PRIMARY',))
        pk_cols = [row[4] for row in sorted(cur.fetchall(), key=lambda row: int(row[3]))]
    if not pk_cols:
        # Stable enough only while source is frozen; physical order may vary.
        # Fail closed instead of silently skipping/duplicating data on OFFSET.
        raise RuntimeError(f'{table}: tabela sem chave primária; requer estratégia de cópia específica para garantir integridade')
    order = ','.join(qi(col) for col in pk_cols)
    insert = 'INSERT INTO ' + qi(table) + ' VALUES (' + ','.join(['%s'] * ncols) + ')'
    while copied < expected:
        # Each SELECT is fully consumed before the cursor closes. No SSCursor.
        with src.cursor() as reader:
            reader.execute('SELECT * FROM ' + qi(table) + ' ORDER BY ' + order + ' LIMIT %s OFFSET %s', (batch_size, copied))
            batch = reader.fetchall()
        if not batch:
            raise RuntimeError(f'Leitura incompleta em {table}: {copied}/{expected}')
        with dst.cursor() as writer:
            writer.executemany(insert, batch)
        dst.commit()
        copied += len(batch)
        send(f'[{index}/{total_tables}] {table}: {copied}/{expected} registros')
    actual = count(dst, table)
    if actual != expected:
        raise RuntimeError(f'Contagem divergente no destino {table}: {actual}/{expected}')


def migrate(src_cfg, dst_cfg, send, reset=False, batch_size=100):
    ensure_not_same(src_cfg, dst_cfg)
    src = dst = None
    stage = 'conexão inicial'
    try:
        send('Conectando à origem...')
        src = connect(src_cfg, readonly=True)
        send('Conectando ao destino...')
        dst = connect(dst_cfg)
        if reset:
            stage = 'limpeza do destino'
            clean_destination(dst, send)
        elif objects(dst):
            raise RuntimeError('Destino não está vazio. Marque a limpeza controlada e confirme o nome exato do banco de destino.')
        stage = 'leitura das tabelas'
        tables = [name for name, typ in objects(src) if typ == 'BASE TABLE']
        if not tables:
            raise RuntimeError('Origem sem tabelas base.')
        send(f'Encontradas {len(tables)} tabelas. Lote: {batch_size} registros.')
        stage = 'criação da estrutura'
        with dst.cursor() as cur:
            cur.execute('SET SESSION FOREIGN_KEY_CHECKS=0')
        for i, table in enumerate(tables, 1):
            with dst.cursor() as cur:
                cur.execute(ddl(src, table))
            dst.commit()
            send(f'[{i}/{len(tables)}] Estrutura: {table}')
        for i, table in enumerate(tables, 1):
            stage = f'tabela {i}/{len(tables)}: {table}'
            for attempt in range(1, 4):
                try:
                    # Restart the whole table from zero on every retry. This handles
                    # ambiguous COMMIT outcomes without duplicating rows.
                    with dst.cursor() as cur:
                        cur.execute('DELETE FROM ' + qi(table))
                    dst.commit()
                    copy_table(src, dst, table, i, len(tables), batch_size, send)
                    break
                except (pymysql.MySQLError, AttributeError, OSError) as exc:
                    # PyMySQL can raise AttributeError during SSCursor cleanup
                    # when a connection socket has already disappeared.
                    code = exc.args[0] if isinstance(exc, pymysql.MySQLError) and exc.args and isinstance(exc.args[0], int) else None
                    detail = mysql_error(exc) if isinstance(exc, pymysql.MySQLError) else f'{type(exc).__name__}: {exc}'
                    send(f'Falha em {stage}, tentativa {attempt}/3 — {detail}')
                    transient = code in TRANSIENT_CODES or (isinstance(exc, AttributeError) and 'settimeout' in str(exc)) or isinstance(exc, OSError)
                    if not transient or attempt == 3:
                        raise
                    time.sleep(min(attempt * 2, 5))
                    src, dst = recreate_connections(src, dst, src_cfg, dst_cfg, send)
        stage = 'validação'
        send('Validando contagens...')
        mismatches = []
        for table in tables:
            old, new = count(src, table), count(dst, table)
            if old != new:
                mismatches.append(f'{table}: origem={old}, destino={new}')
        if mismatches:
            raise RuntimeError('Contagens divergentes: ' + '; '.join(mismatches))
        with dst.cursor() as cur:
            cur.execute('SET SESSION FOREIGN_KEY_CHECKS=1')
        send(f'SUCESSO: {len(tables)} tabelas copiadas; contagens conferidas.')
        send('ATENÇÃO: views, triggers, rotinas e eventos NÃO são migrados; conferir antes da troca definitiva.')
        send('ATENÇÃO: comparação de contagens não valida conteúdo linha a linha nem integridade referencial.')
        return True
    except pymysql.MySQLError as exc:
        raise RuntimeError(f'Etapa: {stage}. {mysql_error(exc)}') from exc
    finally:
        for c in (dst, src):
            if c is not None:
                try:
                    if c is dst:
                        with c.cursor() as cur:
                            cur.execute('SET SESSION FOREIGN_KEY_CHECKS=1')
                except Exception:
                    pass
                try:
                    c.close()
                except Exception:
                    pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('850x740')
        self.minsize(760, 620)
        self.events = queue.Queue()
        self.vars = {}
        self.build()
        self.after(100, self.poll)

    def build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill='both', expand=True)
        ttk.Label(root, text=APP_TITLE, font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(root, text='Origem somente leitura · Destino independente · Perfis criptografados com senha mestra').pack(anchor='w', pady=(0, 8))
        vault_panel = ttk.LabelFrame(root, text='Cofre local de conexões', padding=8)
        vault_panel.pack(fill='x', pady=(0, 8))
        ttk.Label(vault_panel, text='Senha mestra (mínimo 12 caracteres; não é salva):').pack(side='left')
        self.master_password = tk.StringVar()
        ttk.Entry(vault_panel, textvariable=self.master_password, show='•', width=24).pack(side='left', padx=6)
        ttk.Button(vault_panel, text='Salvar perfis', command=self.save_vault).pack(side='left', padx=3)
        ttk.Button(vault_panel, text='Carregar perfis', command=self.load_vault).pack(side='left', padx=3)
        ttk.Button(vault_panel, text='Limpar perfis', command=self.clear_vault).pack(side='left', padx=3)
        columns = ttk.Frame(root)
        columns.pack(fill='x')
        for side, title in [('src', 'ORIGEM'), ('dst', 'DESTINO')]:
            panel = ttk.LabelFrame(columns, text=title, padding=8)
            panel.pack(side='left', fill='x', expand=True, padx=(0, 5) if side == 'src' else (5, 0))
            for key, label in [('host', 'Servidor'), ('port', 'Porta'), ('database', 'Banco'), ('user', 'Usuário'), ('password', 'Senha')]:
                ttk.Label(panel, text=label).pack(anchor='w')
                var = tk.StringVar(value='3306' if key == 'port' else '')
                self.vars[(side, key)] = var
                ttk.Entry(panel, textvariable=var, show='•' if key == 'password' else '').pack(fill='x', pady=(0, 3))
        opts = ttk.Frame(root)
        opts.pack(fill='x', pady=(10, 2))
        ttk.Label(opts, text='Registros por lote:').pack(side='left')
        self.batch = tk.StringVar(value='100')
        ttk.Combobox(opts, textvariable=self.batch, values=['25', '50', '100', '200', '300'], width=7, state='readonly').pack(side='left', padx=6)
        self.reset = tk.BooleanVar(value=False)
        ttk.Checkbutton(root, text='Apagar tabelas/views EXISTENTES somente do banco de DESTINO antes de migrar', variable=self.reset).pack(anchor='w', pady=(8, 3))
        ttk.Label(root, text='Para autorizar a limpeza, digite abaixo o nome EXATO do banco de destino:', foreground='#a04a00').pack(anchor='w')
        self.typed = tk.StringVar()
        ttk.Entry(root, textvariable=self.typed).pack(fill='x', pady=(2, 6))
        self.confirm = tk.BooleanVar(value=False)
        ttk.Checkbutton(root, text='Confirmo que tenho backup e que a origem não receberá gravações durante a cópia.', variable=self.confirm).pack(anchor='w', pady=5)
        self.start = ttk.Button(root, text='Iniciar migração', command=self.run)
        self.start.pack(anchor='w', pady=4)
        ttk.Label(root, text='Log detalhado da execução').pack(anchor='w', pady=(10, 4))
        self.log = tk.Text(root, height=13, state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True)
        ttk.Label(root, text='A limpeza não remove procedures, functions, eventos nem o banco de dados. Verifique esses objetos separadamente.', foreground='#a04a00').pack(anchor='w', pady=(6, 0))

    def save_vault(self):
        profiles = {side: {key: self.vars[(side, key)].get().strip()
                           for key in ('host', 'port', 'database', 'user', 'password')}
                    for side in ('src', 'dst')}
        if any(not all(profile.values()) for profile in profiles.values()):
            messagebox.showwarning('Cofre', 'Preencha todos os campos de ambas as conexões.')
            return
        if VAULT_PATH.exists() and not messagebox.askyesno('Sobrescrever cofre', 'Substituir os perfis criptografados existentes?'):
            return
        try:
            path = save_profiles(profiles, self.master_password.get())
            messagebox.showinfo('Cofre', f'Perfis salvos criptografados em:\n{path}\n\nGuarde sua senha mestra: não há recuperação.')
        except Exception as exc:
            messagebox.showerror('Cofre', f'Não foi possível salvar: {type(exc).__name__}')

    def load_vault(self):
        try:
            profiles = load_profiles(self.master_password.get())
            for side in ('src', 'dst'):
                for key in ('host', 'port', 'database', 'user', 'password'):
                    self.vars[(side, key)].set(str(profiles[side][key]))
            messagebox.showinfo('Cofre', 'Perfis carregados. Confirme origem e destino antes de migrar.')
        except FileNotFoundError:
            messagebox.showerror('Cofre', 'Nenhum cofre salvo neste computador.')
        except Exception as exc:
            messagebox.showerror('Cofre', f'Não foi possível abrir: {type(exc).__name__}: {exc}')

    def clear_vault(self):
        """Clear fields and remove the saved encrypted profile only after confirmation."""
        saved = VAULT_PATH.exists()
        description = (
            'Apagar o arquivo de perfis criptografados deste computador e '
            'limpar os campos de conexão e a senha mestra da tela?'
            if saved else
            'Não há arquivo de perfis salvo. Limpar os campos de conexão e '
            'a senha mestra da tela?'
        )
        if not messagebox.askyesno('Confirmar limpeza de perfis', description +
                                   '\n\nEsta ação não modifica os bancos MySQL.'):
            return
        try:
            if saved:
                delete_profiles()
            for var in self.vars.values():
                var.set('')
            for side in ('src', 'dst'):
                self.vars[(side, 'port')].set('3306')
            self.master_password.set('')
            self.typed.set('')
            self.reset.set(False)
            self.confirm.set(False)
            self.log_line('Perfis locais limpos; bancos de dados não foram alterados.')
            messagebox.showinfo('Cofre', 'Perfis apagados deste computador e campos limpos.' if saved
                                else 'Campos de conexão limpos.')
        except OSError as exc:
            messagebox.showerror('Cofre', f'Não foi possível apagar o cofre: {type(exc).__name__}: {exc}')

    def log_line(self, line):
        self.log.configure(state='normal')
        self.log.insert('end', str(line) + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def run(self):
        if pymysql is None:
            messagebox.showerror('Dependência ausente', 'Execute: python -m pip install -r requirements.txt')
            return
        if not self.confirm.get():
            messagebox.showwarning('Confirmação', 'Confirme o backup e a ausência de gravações na origem.')
            return
        cfg = {}
        for side in ('src', 'dst'):
            cfg[side] = {key: self.vars[(side, key)].get().strip() for key in ('host', 'port', 'database', 'user', 'password')}
            if not all(cfg[side].values()):
                messagebox.showwarning('Campos', 'Preencha todos os campos de origem e destino.')
                return
        try:
            ensure_not_same(cfg['src'], cfg['dst'])
        except RuntimeError as exc:
            messagebox.showerror('Segurança', str(exc))
            return
        if self.reset.get():
            if self.typed.get().strip() != cfg['dst']['database']:
                messagebox.showerror('Confirmação', 'O nome digitado não coincide com o banco de destino. Limpeza bloqueada.')
                return
            if not messagebox.askyesno('ATENÇÃO: APAGAR DESTINO', f'APAGAR todas as tabelas e views do banco de DESTINO {cfg["dst"]["database"]}?\n\nO banco de origem será preservado. Esta ação não pode ser desfeita.'):
                return
        elif not messagebox.askyesno('Confirmar migração', 'Copiar para um banco de destino VAZIO?'):
            return
        self.start.configure(state='disabled')
        self.log_line('Iniciando migração...')
        threading.Thread(target=self.worker, args=(cfg['src'], cfg['dst'], self.reset.get(), int(self.batch.get())), daemon=True).start()

    def worker(self, src, dst, reset, batch):
        try:
            migrate(src, dst, lambda line: self.events.put(('log', line)), reset=reset, batch_size=batch)
            self.events.put(('done', 'Migração concluída; confira os avisos e valide o sistema.'))
        except Exception as exc:
            # Log only traceback frames and the exception type/message. Never log connection dictionaries.
            frames = traceback.extract_tb(exc.__traceback__)
            location = ' > '.join(f'{Path(frame.filename).name}:{frame.lineno} ({frame.name})' for frame in frames[-5:])
            message = str(exc)
            for cfg in (src, dst):
                secret = cfg.get('password', '')
                if secret:
                    message = message.replace(secret, '[SENHA OCULTA]')
            message = re.sub(r'(?i)(password|passwd|pwd)\s*[:=]\s*[^\s,;]+', r'\1=[OCULTO]', message)
            self.events.put(('error', f'{type(exc).__name__}: {message}\nLocal: {location}'))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                self.log_line(payload)
                if kind != 'log':
                    self.start.configure(state='normal')
                    if kind == 'done':
                        messagebox.showinfo('Concluído', payload)
                    else:
                        messagebox.showerror('Falha', payload)
        except queue.Empty:
            pass
        self.after(100, self.poll)


if __name__ == '__main__':
    App().mainloop()
