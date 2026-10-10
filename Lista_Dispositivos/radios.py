# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

""" Leitura de Wi-Fi (RSSI nativo) e descoberta Bluetooth no Windows """

import asyncio
import ctypes as C
import sys
import time

U8, U16, U32, I32, U64 = C.c_uint8, C.c_uint16, C.c_uint32, C.c_int32, C.c_uint64
PTR = C.c_void_p


class Cancelled(Exception):
    pass


class GUID(C.Structure):
    _fields_ = [('a', U32), ('b', U16), ('c', U16), ('d', U8 * 8)]


class SSID(C.Structure):
    _fields_ = [('length', U32), ('data', U8 * 32)]


class Interface(C.Structure):
    _fields_ = [('guid', GUID), ('description', U16 * 256), ('state', U32)]


class RateSet(C.Structure):
    _fields_ = [('length', U32), ('rates', U16 * 126)]


class BssEntry(C.Structure):
    _fields_ = [('ssid', SSID), ('phy', U32), ('bssid', U8 * 6),
                ('bss_type', U32), ('phy_type', U32), ('rssi', I32),
                ('quality', U32), ('in_domain', U8), ('beacon', U16),
                ('timestamp', U64), ('host_timestamp', U64), ('capability', U16),
                ('frequency', U32), ('rates', RateSet), ('ie_offset', U32),
                ('ie_size', U32)]


class Notification(C.Structure):
    _fields_ = [('source', U32), ('code', U32), ('guid', GUID),
                ('size', U32), ('data', PTR)]


def require_windows():
    if sys.platform != 'win32':
        raise RuntimeError('Esta versão de Wi-Fi requer Windows 10/11.')


def bind(dll, name, restype, args):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = restype, args
    return fn


def check(code, operation):
    if code:
        if code == 5:
            raise RuntimeError(f'{operation}: acesso negado. No Windows, habilite '
                               'Privacidade e segurança > Localização e o acesso de aplicativos.')
        raise RuntimeError(f'{operation}: erro Windows {code}. '
                           'Verifique adaptador, rádio e serviço Configuração Automática de WLAN.')


def wide_text(values):
    raw = bytes(values)
    return raw.decode('utf-16-le', errors='replace').split('\0', 1)[0]


def signal_label(rssi):
    if rssi >= -50:
        return 'Excelente'
    if rssi >= -60:
        return 'Bom'
    if rssi >= -70:
        return 'Regular'
    return 'Fraco'


def bss_row(entry, adapter):
    name = bytes(entry.ssid.data[:min(entry.ssid.length, 32)]).decode('utf-8', errors='replace')
    mac = ':'.join(f'{x:02X}' for x in entry.bssid)
    # Não converte porcentagem em dBm: lê diretamente lRssi do driver.
    return dict(ssid=name or '(SSID oculto)', address=mac, rssi=int(entry.rssi),
                quality=int(entry.quality), signal=signal_label(entry.rssi),
                frequency=round(entry.frequency / 1000, 1), adapter=adapter)


def scan_wifi(stop):
    """Espera notificação de conclusão; não publica cache após timeout/falha."""
    require_windows()
    dll = C.WinDLL('wlanapi.dll')
    open_handle = bind(dll, 'WlanOpenHandle', U32, [U32, PTR, C.POINTER(U32), C.POINTER(PTR)])
    close_handle = bind(dll, 'WlanCloseHandle', U32, [PTR, PTR])
    enum = bind(dll, 'WlanEnumInterfaces', U32, [PTR, PTR, C.POINTER(PTR)])
    free = bind(dll, 'WlanFreeMemory', None, [PTR])
    scan = bind(dll, 'WlanScan', U32, [PTR, C.POINTER(GUID), PTR, PTR, PTR])
    get_bss = bind(dll, 'WlanGetNetworkBssList', U32,
                   [PTR, C.POINTER(GUID), PTR, U32, I32, PTR, C.POINTER(PTR)])
    callback_type = C.WINFUNCTYPE(None, C.POINTER(Notification), PTR)
    # callback é recebido como void* para permitir desregistro com NULL.
    register = bind(dll, 'WlanRegisterNotification', U32,
                    [PTR, U32, I32, PTR, PTR, PTR, C.POINTER(U32)])
    handle, negotiated = PTR(), U32()
    check(open_handle(2, None, C.byref(negotiated), C.byref(handle)), 'Abrir Wi-Fi')
    outcomes = {}

    def notified(pointer, context):
        n = pointer.contents
        if n.source & 8 and n.code in (7, 8):  # ACM scan_complete / scan_fail
            outcomes[bytes(n.guid)] = n.code

    callback = callback_type(notified)  # manter referência até fechar handle
    registered = False
    try:
        previous = U32()
        check(register(handle, 8, 0, C.cast(callback, PTR), None, None,
                       C.byref(previous)), 'Notificações Wi-Fi')
        registered = True
        interfaces = PTR()
        check(enum(handle, None, C.byref(interfaces)), 'Listar adaptadores Wi-Fi')
        try:
            count = U32.from_address(interfaces.value).value
            if count > 64:
                raise RuntimeError('Lista de adaptadores inválida.')
            adapters = [Interface.from_buffer_copy(C.string_at(
                interfaces.value + 8 + i * C.sizeof(Interface), C.sizeof(Interface)))
                for i in range(count)]
        finally:
            free(interfaces)
        if not adapters:
            raise RuntimeError('Nenhum adaptador Wi-Fi encontrado. Verifique o hardware/driver.')
        rows, warnings, successes = {}, [], 0
        for adapter in adapters:
            if stop.is_set():
                raise Cancelled()
            key = bytes(adapter.guid)
            outcomes.pop(key, None)
            try:
                check(scan(handle, C.byref(adapter.guid), None, None, None), 'Buscar redes')
                deadline = time.monotonic() + 8
                while key not in outcomes:
                    if stop.wait(0.1):
                        raise Cancelled()
                    if time.monotonic() >= deadline:
                        raise RuntimeError('O driver Wi-Fi não confirmou a busca em 8 segundos.')
                if outcomes[key] != 7:
                    raise RuntimeError('O driver informou falha na busca Wi-Fi. Verifique rádio/permissões.')
                result = PTR()
                # SSID NULL: todos os BSS, dot11_BSS_type_any=3 conforme API.
                check(get_bss(handle, C.byref(adapter.guid), None, 3, 0, None,
                              C.byref(result)), 'Ler sinal Wi-Fi')
                try:
                    total = U32.from_address(result.value).value
                    count = U32.from_address(result.value + 4).value
                    if 8 + count * C.sizeof(BssEntry) > total:
                        raise RuntimeError('Tamanho da lista Wi-Fi inválido.')
                    description = wide_text(adapter.description)
                    for i in range(count):
                        entry = BssEntry.from_address(result.value + 8 + i * C.sizeof(BssEntry))
                        row = bss_row(entry, description)
                        existing = rows.get(row['address'])
                        if not existing or row['rssi'] > existing['rssi']:
                            rows[row['address']] = row
                    successes += 1
                finally:
                    free(result)
            except RuntimeError as exc:
                warnings.append(str(exc))
        if not successes:
            raise RuntimeError(' | '.join(warnings))
        return sorted(rows.values(), key=lambda r: r['rssi'], reverse=True), warnings
    finally:
        if registered:
            register(handle, 0, 0, None, None, None, None)
        close_handle(handle, None)


class LiveBleDevices:
    """Presença recente baseada exclusivamente em callbacks de anúncios BLE.

    Não lê lista de pareados, histórico do Windows nem BLEDevice.name. A janela
    de presença usa relógio monotônico e começa vazia a cada nova ativação.
    """
    def __init__(self, ttl=10.0, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self.devices = {}

    def received(self, device, advertisement):
        address = device.address.upper()
        previous = self.devices.get(address)
        now = self.clock()
        # Nome somente do anúncio (ou anúncio recente anterior desta sessão).
        name = advertisement.local_name or (
            previous['name'] if previous and now - previous['seen'] < self.ttl
            else '(Sem nome no anúncio)')
        self.devices[address] = dict(name=name, address=address, kind='BLE',
                                    rssi=advertisement.rssi, seen=now)

    def snapshot(self):
        now = self.clock()
        for address in list(self.devices):
            if now - self.devices[address]['seen'] >= self.ttl:
                del self.devices[address]
        rows = []
        for device in self.devices.values():
            age = max(0.0, now - device['seen'])
            rows.append(dict(name=device['name'], address=device['address'],
                             kind='BLE', rssi=device['rssi'],
                             status=f"há {age:.1f} s"))
        return sorted(rows, key=lambda row: (row['name'].casefold(), row['address']))


async def watch_ble(stop, publish, ttl=10.0, refresh=0.5):
    """Escuta contínua de anúncios; publica snapshot recente a cada 0,5 s."""
    if stop.is_set():
        raise Cancelled()
    try:
        from bleak import BleakScanner
    except ImportError as exc:
        raise RuntimeError('Instale Bleak: python -m pip install -r requirements.txt') from exc
    live = LiveBleDevices(ttl=ttl)
    try:
        # No Windows, Bleak usa BluetoothLEAdvertisementWatcher. Não há fallback
        # para enumeração clássica/pareados se o rádio estiver indisponível.
        async with BleakScanner(detection_callback=live.received, scanning_mode='active'):
            next_publish = 0.0
            while not stop.is_set():
                now = time.monotonic()
                if now >= next_publish:
                    publish(live.snapshot())
                    next_publish = now + refresh
                await asyncio.sleep(0.1)
    finally:
        live.devices.clear()


def watch_bluetooth(stop, publish):
    asyncio.run(watch_ble(stop, publish))
