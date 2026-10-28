# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

"""Encrypted local connection profiles. No plaintext passwords or master key stored."""
import base64
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

VAULT_PATH = Path.home() / '.pd_database_migrator' / 'connections.enc'
ITERATIONS = 600_000


def _key(master_password, salt, iterations):
    if not master_password:
        raise ValueError('Informe uma senha mestra.')
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode('utf-8')))


def save_profiles(profiles, master_password):
    if len(master_password) < 12:
        raise ValueError('A senha mestra deve ter pelo menos 12 caracteres.')
    if set(profiles) != {'src', 'dst'}:
        raise ValueError('Perfis de origem e destino obrigatórios.')
    salt = os.urandom(16)
    payload = json.dumps(profiles, ensure_ascii=False).encode('utf-8')
    token = Fernet(_key(master_password, salt, ITERATIONS)).encrypt(payload)
    envelope = {'format': 1, 'kdf': 'pbkdf2-sha256', 'iterations': ITERATIONS,
                'salt': base64.b64encode(salt).decode('ascii'), 'token': token.decode('ascii')}
    VAULT_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = VAULT_PATH.with_suffix('.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as handle:
            json.dump(envelope, handle)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(VAULT_PATH)
    finally:
        if tmp.exists():
            tmp.unlink()
    return VAULT_PATH


def load_profiles(master_password):
    envelope = json.loads(VAULT_PATH.read_text(encoding='utf-8'))
    if envelope.get('format') != 1 or envelope.get('kdf') != 'pbkdf2-sha256':
        raise ValueError('Formato do cofre desconhecido.')
    iterations = int(envelope['iterations'])
    if not 100_000 <= iterations <= 2_000_000:
        raise ValueError('Parâmetros de derivação inválidos.')
    salt = base64.b64decode(envelope['salt'], validate=True)
    try:
        payload = Fernet(_key(master_password, salt, iterations)).decrypt(envelope['token'].encode('ascii'))
    except InvalidToken as exc:
        raise ValueError('Senha mestra incorreta ou cofre corrompido.') from exc
    profiles = json.loads(payload)
    if set(profiles) != {'src', 'dst'}:
        raise ValueError('Perfis armazenados inválidos.')
    return profiles


def delete_profiles():
    """Delete the saved encrypted vault; does not guarantee secure disk erasure."""
    try:
        VAULT_PATH.unlink()
    except FileNotFoundError:
        return False
    return True
