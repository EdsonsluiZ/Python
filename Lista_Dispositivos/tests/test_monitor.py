"""Testes sem hardware: contratos nativos, sinais, cache e ciclo dos workers."""
import ctypes as C
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

import app
import radios as r


class Function:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *args):
        return self.fn(*args)


class FakeWlan:
    """Memória com layout Windows e callback equivalente ao sistema operacional."""
    def __init__(self, complete=7, scan_error=0):
        self.complete, self.scan_error = complete, scan_error
        self.callback = None
        self.freed, self.closed = [], False
        self.interface = r.Interface()
        self.interface.guid.a = 123
        self.interface_buffer = C.create_string_buffer(8 + C.sizeof(r.Interface))
        C.c_uint32.from_buffer(self.interface_buffer).value = 1
        C.memmove(C.addressof(self.interface_buffer) + 8, C.byref(self.interface), C.sizeof(r.Interface))
        self.entry = r.BssEntry()
        self.entry.ssid.length = 4
        self.entry.ssid.data[:4] = b'Test'
        self.entry.bssid[:] = [1, 2, 3, 4, 5, 6]
        self.entry.rssi, self.entry.quality, self.entry.frequency = -43, 88, 2412000
        self.bss_buffer = C.create_string_buffer(8 + C.sizeof(r.BssEntry))
        C.c_uint32.from_buffer(self.bss_buffer).value = len(self.bss_buffer)
        C.c_uint32.from_buffer(self.bss_buffer, 4).value = 1
        C.memmove(C.addressof(self.bss_buffer) + 8, C.byref(self.entry), C.sizeof(r.BssEntry))
        for name, fn in {
            'WlanOpenHandle': self.open, 'WlanCloseHandle': self.close,
            'WlanEnumInterfaces': self.enum, 'WlanFreeMemory': self.free,
            'WlanScan': self.scan, 'WlanGetNetworkBssList': self.bss,
            'WlanRegisterNotification': self.register,
        }.items():
            setattr(self, name, Function(fn))

    def open(self, version, reserved, negotiated, handle):
        C.cast(handle, C.POINTER(C.c_void_p))[0] = 1234
        return 0

    def close(self, *args):
        self.closed = True
        return 0

    def enum(self, handle, reserved, pointer):
        C.cast(pointer, C.POINTER(C.c_void_p))[0] = C.addressof(self.interface_buffer)
        return 0

    def free(self, pointer):
        self.freed.append(pointer.value)

    def register(self, handle, source, ignore, callback, *args):
        self.callback = callback
        return 0

    def scan(self, handle, guid, *args):
        if self.scan_error:
            return self.scan_error
        notification = r.Notification()
        notification.source, notification.code = 8, self.complete
        notification.guid = C.cast(guid, C.POINTER(r.GUID)).contents
        fn = C.CFUNCTYPE(None, C.POINTER(r.Notification), C.c_void_p)(self.callback.value)
        fn(C.byref(notification), None)
        return 0

    def bss(self, handle, guid, ssid, kind, security, reserved, pointer):
        C.cast(pointer, C.POINTER(C.c_void_p))[0] = C.addressof(self.bss_buffer)
        return 0


class RadioTests(unittest.TestCase):
    def test_windows_layouts(self):
        self.assertEqual(C.sizeof(r.GUID), 16)
        self.assertEqual(C.sizeof(r.Interface), 532)
        self.assertEqual(C.sizeof(r.BssEntry), 360)
        self.assertEqual(r.BssEntry.rssi.offset, 56)

    def invoke_wlan(self, native, stop=None):
        with patch.object(r.sys, 'platform', 'win32'), \
             patch.object(C, 'WinDLL', return_value=native, create=True), \
             patch.object(C, 'WINFUNCTYPE', C.CFUNCTYPE, create=True):
            return r.scan_wifi(stop or threading.Event())

    def test_native_rssi_is_not_derived_from_percent(self):
        native = FakeWlan()
        rows, warnings = self.invoke_wlan(native)
        self.assertEqual(warnings, [])
        self.assertEqual(rows[0]['rssi'], -43)
        self.assertEqual(rows[0]['quality'], 88)
        self.assertEqual(rows[0]['frequency'], 2412)
        self.assertEqual(rows[0]['address'], '01:02:03:04:05:06')
        self.assertTrue(native.closed)
        self.assertEqual(len(native.freed), 2)
        self.assertIsNone(native.callback)

    def test_scan_failure_never_returns_cached_rows(self):
        native = FakeWlan(complete=8)
        with self.assertRaisesRegex(RuntimeError, 'falha'):
            self.invoke_wlan(native)
        self.assertTrue(native.closed)
        self.assertEqual(len(native.freed), 1)

    def test_permission_error_is_actionable(self):
        native = FakeWlan(scan_error=5)
        with self.assertRaisesRegex(RuntimeError, 'Localização'):
            self.invoke_wlan(native)
        self.assertTrue(native.closed)

    def test_wifi_cancel_closes_handles(self):
        native = FakeWlan()
        stop = threading.Event()
        stop.set()
        with self.assertRaises(r.Cancelled):
            self.invoke_wlan(native, stop)
        self.assertTrue(native.closed)



class WorkerTests(unittest.TestCase):
    def test_frame_queue_is_bounded_and_keeps_latest(self):
        q = queue.Queue(maxsize=1)
        for i in range(100):
            app.put_latest(q, i)
        self.assertEqual(q.qsize(), 1)
        self.assertEqual(q.get_nowait(), 99)

    def test_worker_cancellation_emits_no_late_rows(self):
        # Chama somente o controlador de trabalho: não necessita display Tk.
        controller = type('Controller', (), {})()
        controller.events, controller.frames = queue.Queue(), queue.Queue(maxsize=1)
        stop = threading.Event()

        def scanner(event):
            event.set()
            return [dict(fake=True)], []

        with patch.object(app, 'scan_wifi', scanner):
            app.MonitorApp._run(controller, 'wifi', stop, 7, 0)
        messages = list(controller.events.queue)
        self.assertEqual([x[2] for x in messages], ['status', 'done'])
        self.assertTrue(all(x[1] == 7 for x in messages))

    def test_error_is_reported_and_worker_finishes(self):
        controller = type('Controller', (), {})()
        controller.events, controller.frames = queue.Queue(), queue.Queue(maxsize=1)
        with patch.object(app, 'scan_wifi', side_effect=RuntimeError('sem adaptador')):
            app.MonitorApp._run(controller, 'wifi', threading.Event(), 1, 0)
        kinds = [x[2] for x in list(controller.events.queue)]
        self.assertEqual(kinds, ['status', 'error', 'done'])

    def test_camera_releases_capture_on_read_exception(self):
        import types
        released = []
        class Capture:
            def isOpened(self):
                return True
            def set(self, *args):
                pass
            def read(self):
                raise RuntimeError('falha no driver')
            def release(self):
                released.append(True)
        fake = types.SimpleNamespace(VideoCapture=lambda *args: Capture(),
                                     CAP_DSHOW=1, CAP_MSMF=2, CAP_ANY=0,
                                     CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_FPS=5)
        with patch.dict(sys.modules, {'cv2': fake}):
            with self.assertRaisesRegex(RuntimeError, 'falha no driver'):
                app.camera_worker(threading.Event(), lambda *args: None,
                                  queue.Queue(maxsize=1), 1, 0)
        self.assertEqual(released, [True])


if __name__ == '__main__':
    unittest.main()
