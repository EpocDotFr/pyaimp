import win32gui
import win32api
import win32con

__version__ = '0.1.0'

WM_AIMP_COMMAND = win32con.WM_USER + 0x75
WM_AIMP_NOTIFY = win32con.WM_USER + 0x76
WM_AIMP_PROPERTY = win32con.WM_USER + 0x77

AIMP_RA_PROPVALUE_GET = 0
AIMP_RA_PROPVALUE_SET = 1

AIMP_RA_PROPERTY_VERSION = 0x10
AIMP_RA_PROPERTY_VOLUME = 0x50

class Client:
    hwnd = None

    def __init__(self):
        self.hwnd = win32gui.FindWindow('AIMP2_RemoteInfo', None)

        if not self.hwnd:
            raise RuntimeError('Unable to find the AIMP instance. Are you sure it is running?')

    def _get_prop(self, prop_id):
        return win32api.SendMessage(self.hwnd, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_GET, 0)

    def _set_prop(self, prop_id, value):
        return win32api.SendMessage(self.hwnd, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_SET, value)

    def get_version(self):
        version = self._get_prop(AIMP_RA_PROPERTY_VERSION)

        return (win32api.HIWORD(version), win32api.LOWORD(version))

    def get_volume(self):
        return self._get_prop(AIMP_RA_PROPERTY_VOLUME)

    def set_volume(self, volume):
        return self._set_prop(AIMP_RA_PROPERTY_VOLUME, volume)
