"""Regressões: histórico do SO não é presença; somente anúncios recebidos."""
import asyncio
import queue
import threading
import types
import unittest
from unittest.mock import patch

import app
import radios as r


def device(address='AA:BB:CC:DD:EE:FF', saved_name='Nome salvo no Windows'):
    return types.SimpleNamespace(address=address, name=saved_name)


def advertisement(name=None, rssi=-57):
    return types.SimpleNamespace(local_name=name, rssi=rssi)


class LivePresenceTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.live = r.LiveBleDevices(ttl=10, clock=lambda: self.now)

    def test_starts_empty(self):
        self.assertEqual(self.live.snapshot(), [])

    def test_never_uses_saved_windows_name(self):
        self.live.received(device(), advertisement())
        row = self.live.snapshot()[0]
        self.assertEqual(row['name'], '(Sem nome no anúncio)')
        self.assertEqual(row['rssi'], -57)

    def test_name_and_rssi_come_from_current_advertisement(self):
        self.live.received(device(), advertisement('Sensor anunciado', -63))
        self.assertEqual(self.live.snapshot()[0]['name'], 'Sensor anunciado')
        self.now += 1
        self.live.received(device(), advertisement(rssi=-42))
        row = self.live.snapshot()[0]
        self.assertEqual(row['name'], 'Sensor anunciado')
        self.assertEqual(row['rssi'], -42)

    def test_removes_device_after_ten_seconds_without_signal(self):
        self.live.received(device(), advertisement())
        self.now += 9.9
        self.assertEqual(len(self.live.snapshot()), 1)
        self.now += 0.1
        self.assertEqual(self.live.snapshot(), [])

    def test_new_packet_refreshes_presence_deadline(self):
        self.live.received(device(), advertisement())
        self.now += 9
        self.live.received(device(), advertisement(rssi=-48))
        self.now += 2
        self.assertEqual(len(self.live.snapshot()), 1)
        self.assertEqual(self.live.snapshot()[0]['status'], 'há 2.0 s')

    def test_same_address_is_one_device_same_name_is_not(self):
        self.live.received(device(), advertisement('Mesmo nome'))
        self.live.received(device('aa:bb:cc:dd:ee:ff'), advertisement('Mesmo nome', -41))
        self.live.received(device('00:11:22:33:44:55'), advertisement('Mesmo nome'))
        self.assertEqual(len(self.live.snapshot()), 2)

    def test_new_session_has_no_previous_presence(self):
        self.live.received(device(), advertisement())
        self.assertEqual(r.LiveBleDevices().snapshot(), [])

    def test_expired_advertised_name_is_not_reused(self):
        self.live.received(device(), advertisement('Nome antigo'))
        self.now += 11
        self.live.received(device(), advertisement())
        self.assertEqual(self.live.snapshot()[0]['name'], '(Sem nome no anúncio)')


class WatcherTests(unittest.TestCase):
    def fake_backend(self, emit=False):
        closed, modes = [], []

        class Scanner:
            # Esses registros não foram anunciados e jamais devem ser lidos.
            discovered_devices = [device('11:22:33:44:55:66')]

            def __init__(self, detection_callback, scanning_mode):
                self.callback = detection_callback
                modes.append(scanning_mode)

            async def __aenter__(self):
                if emit:
                    self.callback(device(), advertisement('Anúncio atual', -45))
                return self

            async def __aexit__(self, *args):
                closed.append(True)

        return types.SimpleNamespace(BleakScanner=Scanner), closed, modes

    def test_cached_scanner_list_does_not_enter_count(self):
        backend, closed, modes = self.fake_backend()
        stop, received = threading.Event(), []

        def publish(rows):
            received.append(rows)
            stop.set()

        with patch.dict('sys.modules', {'bleak': backend}):
            asyncio.run(r.watch_ble(stop, publish))
        self.assertEqual(received, [[]])
        self.assertEqual(closed, [True])
        self.assertEqual(modes, ['active'])

    def test_only_received_advertisement_enters_count(self):
        backend, closed, _ = self.fake_backend(emit=True)
        stop, received = threading.Event(), []

        def publish(rows):
            received.append(rows)
            stop.set()

        with patch.dict('sys.modules', {'bleak': backend}):
            asyncio.run(r.watch_ble(stop, publish))
        self.assertEqual(len(received[0]), 1)
        self.assertEqual(received[0][0]['address'], 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(received[0][0]['rssi'], -45)
        self.assertEqual(closed, [True])

    def test_publish_failure_stops_scanner(self):
        backend, closed, _ = self.fake_backend()
        def publish(rows):
            raise RuntimeError('erro no consumidor')
        with patch.dict('sys.modules', {'bleak': backend}):
            with self.assertRaisesRegex(RuntimeError, 'consumidor'):
                asyncio.run(r.watch_ble(threading.Event(), publish))
        self.assertEqual(closed, [True])

    def test_pre_cancel_does_not_even_open_scanner(self):
        stop = threading.Event()
        stop.set()
        with self.assertRaises(r.Cancelled):
            asyncio.run(r.watch_ble(stop, lambda rows: None))

    def test_controller_discards_packets_after_stop(self):
        controller = types.SimpleNamespace(events=queue.Queue(), frames=queue.Queue(maxsize=1))
        stop = threading.Event()

        def watcher(event, publish):
            event.set()
            publish([{'fake': True}])

        with patch.object(app, 'watch_bluetooth', watcher):
            app.MonitorApp._run(controller, 'bluetooth', stop, 4, 0)
        self.assertEqual([x[2] for x in controller.events.queue], ['status', 'done'])


if __name__ == '__main__':
    unittest.main()
