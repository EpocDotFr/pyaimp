from mmapfile import mmapfile
from enum import Enum
from collections import OrderedDict
import struct
import threading
import win32gui
import win32api
import win32con
import win32process
import win32con
import ctypes
import ctypes.wintypes
import time
import io
import subprocess

__version__ = '0.1.0'

__all__ = [
    'PlayBackState',
    'Client'
]

AIMPRemoteAccessClass = 'AIMP2_RemoteInfo'
AIMPRemoteAccessMapFileSize = 2048

AIMPRemoteAccessPackFormat = OrderedDict([
    ('Deprecated1', 'L'),
    ('Active', '?'),
    ('BitRate', 'L'),
    ('Channels', 'L'),
    ('Duration', 'L'),
    ('FileSize', 'l'),
    ('FileMark', 'L'),
    ('Deprecated2', '6I'),
    ('SampleRate', 'L'),
    ('TrackNumber', 'L'),
    ('AlbumLength', 'L'),
    ('ArtistLength', 'L'),
    ('DateLength', 'L'),
    ('FileNameLength', 'L'),
    ('GenreLength', 'L'),
    ('TitleLength', 'L')
])

# -----------------------------------------------------
# Message types to send to AIMP

WM_AIMP_COMMAND = win32con.WM_USER + 0x75
WM_AIMP_NOTIFY = win32con.WM_USER + 0x76
WM_AIMP_PROPERTY = win32con.WM_USER + 0x77

# -----------------------------------------------------
# Properties

AIMP_RA_PROPVALUE_GET = 0
AIMP_RA_PROPVALUE_SET = 1

AIMP_RA_PROPERTY_VERSION = 0x10
AIMP_RA_PROPERTY_PLAYER_POSITION = 0x20
AIMP_RA_PROPERTY_PLAYER_DURATION = 0x30
AIMP_RA_PROPERTY_PLAYER_STATE = 0x40
AIMP_RA_PROPERTY_VOLUME = 0x50
AIMP_RA_PROPERTY_MUTE = 0x60
AIMP_RA_PROPERTY_TRACK_REPEAT = 0x70
AIMP_RA_PROPERTY_TRACK_SHUFFLE = 0x80
AIMP_RA_PROPERTY_RADIOCAP = 0x90
AIMP_RA_PROPERTY_VISUAL_FULLSCREEN = 0xA0

# -----------------------------------------------------
# Commands

AIMP_RA_CMD_BASE = 10

WM_AIMP_COPYDATA_ALBUMART_ID = 0x41495043

AIMP_RA_CMD_REGISTER_NOTIFY = AIMP_RA_CMD_BASE + 1
AIMP_RA_CMD_UNREGISTER_NOTIFY = AIMP_RA_CMD_BASE + 2

AIMP_RA_CMD_PLAY = AIMP_RA_CMD_BASE + 3
AIMP_RA_CMD_PLAYPAUSE = AIMP_RA_CMD_BASE + 4
AIMP_RA_CMD_PAUSE = AIMP_RA_CMD_BASE + 5
AIMP_RA_CMD_STOP = AIMP_RA_CMD_BASE + 6
AIMP_RA_CMD_NEXT = AIMP_RA_CMD_BASE + 7
AIMP_RA_CMD_PREV = AIMP_RA_CMD_BASE + 8
AIMP_RA_CMD_VISUAL_NEXT = AIMP_RA_CMD_BASE + 9
AIMP_RA_CMD_VISUAL_PREV = AIMP_RA_CMD_BASE + 10
AIMP_RA_CMD_QUIT = AIMP_RA_CMD_BASE + 11
AIMP_RA_CMD_ADD_FILES = AIMP_RA_CMD_BASE + 12
AIMP_RA_CMD_ADD_FOLDERS = AIMP_RA_CMD_BASE + 13
AIMP_RA_CMD_ADD_PLAYLISTS = AIMP_RA_CMD_BASE + 14
AIMP_RA_CMD_ADD_URL = AIMP_RA_CMD_BASE + 15
AIMP_RA_CMD_OPEN_FILES = AIMP_RA_CMD_BASE + 16
AIMP_RA_CMD_OPEN_FOLDERS = AIMP_RA_CMD_BASE + 17
AIMP_RA_CMD_OPEN_PLAYLISTS = AIMP_RA_CMD_BASE + 18
AIMP_RA_CMD_GET_ALBUMART = AIMP_RA_CMD_BASE + 19
AIMP_RA_CMD_VISUAL_START = AIMP_RA_CMD_BASE + 20
AIMP_RA_CMD_VISUAL_STOP = AIMP_RA_CMD_BASE + 21

# -----------------------------------------------------
# Events

AIMP_RA_NOTIFY_BASE = 0

AIMP_RA_NOTIFY_TRACK_INFO = AIMP_RA_NOTIFY_BASE + 1
AIMP_RA_NOTIFY_TRACK_START = AIMP_RA_NOTIFY_BASE + 2
AIMP_RA_NOTIFY_PROPERTY = AIMP_RA_NOTIFY_BASE + 3

# -----------------------------------------------------

class AlbumImageCopyData(ctypes.Structure):
    _fields_ = [
        ('dwData', ctypes.wintypes.DWORD),
        ('cbData', ctypes.wintypes.DWORD),
        ('lpData', ctypes.c_void_p)
    ]

PAlbumImageCopyData = ctypes.POINTER(AlbumImageCopyData)

# -----------------------------------------------------

class AlbumImageInternalWindow(threading.Thread):
    def _handle_wm_copydata(self, hwnd, msg, wparam, lparam):
        self.image = None

        album_image_copy_data = ctypes.cast(lparam, PAlbumImageCopyData)

        if album_image_copy_data.contents.dwData != WM_AIMP_COPYDATA_ALBUMART_ID:
            self.stop()
        else:
            image_data = ctypes.wstring_at(album_image_copy_data.contents.lpData, album_image_copy_data.contents.cbData) # TODO

            self.image = image_data

        self.stop()

    def run(self):
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = 'pyaimp'
        wc.lpfnWndProc = {
            win32con.WM_COPYDATA: self._handle_wm_copydata
        }

        hinstance = wc.hInstance = win32api.GetModuleHandle(None)
        class_name = win32gui.RegisterClass(wc)

        self.hwnd = win32gui.CreateWindow(
            class_name,
            'PyAIMP ' + __version__,
            0,
            0, 
            0,
            win32con.CW_USEDEFAULT, 
            win32con.CW_USEDEFAULT,
            0, 
            0,
            hinstance, 
            None
        )

        win32gui.PumpMessages()

    def stop(self):
        win32api.PostQuitMessage()

# -----------------------------------------------------

class PlayBackState(Enum):
    """Enumeration (extending :py:class:`enum.Enum`) of all possible AIMP playback states.

    May be used in conjonction with :func:`pyaimp.Client.get_playback_state` result."""

    Stopped = 0 #: There's currently no track being played.
    Paused = 1 #: The current track playback is currently suspended.
    Playing = 2 #: A track is being played.


class Client:
    """Main class of the ``pyaimp`` module which is the wrapper around the AIMP remote API.

    When a new instance of this class is created, it will search for the current AIMP window. If none
    are found, a ``RuntimeError`` exception will be raised.

    .. note::

       Consider all methods to be **blocking**.

    :raises RuntimeError: The AIMP window cannot be found.
    """

    def __init__(self):
        self._get_aimp_window()
        self._get_aimp_exe_path()

    def _get_aimp_window(self):
        self._aimp_window = win32gui.FindWindow(AIMPRemoteAccessClass, None)

        if not self._aimp_window:
            raise RuntimeError('Unable to find the AIMP window. Are you sure it is running?')

    def _get_aimp_exe_path(self):
        win_thread_proc_id = win32process.GetWindowThreadProcessId(self._aimp_window)

        pwnd = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, win_thread_proc_id[1])

        self._aimp_exe_path = win32process.GetModuleFileNameEx(pwnd, None)

        if not self._aimp_exe_path:
            raise RuntimeError('Unable to retrieve the AIMP executable.')

    def _get_prop(self, prop_id):
        return win32api.SendMessage(self._aimp_window, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_GET, 0)

    def _set_prop(self, prop_id, value):
        win32api.SendMessage(self._aimp_window, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_SET, value)

    def _send_command(self, command_id, parameter=None):
        return win32api.SendMessage(self._aimp_window, WM_AIMP_COMMAND, command_id, parameter)

    def _run_cli_command(self, command, param1=None):
        cli = [
            self._aimp_exe_path,
            '/' + command.upper(),
            param1
        ]

        subprocess.run(cli, check=True)

    def get_current_track_infos(self):
        """Return a dictionnary of informations about the current active track.

        .. warning::

           This method is experimental and should be used with caution.

        :rtype: dict
        """

        mapped_file = mmapfile(None, AIMPRemoteAccessClass, MaximumSize=AIMPRemoteAccessMapFileSize)

        pack_format = ''.join(AIMPRemoteAccessPackFormat.values())

        meta_data_raw = mapped_file.read(struct.calcsize(pack_format))

        meta_data_unpacked = dict(zip(AIMPRemoteAccessPackFormat.keys(), struct.unpack(pack_format, meta_data_raw)))

        track_data = mapped_file.readline().decode().replace('\x00', '')

        mapped_file.close()

        ret = {
            'bit_rate': meta_data_unpacked['BitRate'],
            'channels': meta_data_unpacked['Channels'],
            'duration': meta_data_unpacked['Duration'],
            'file_size': meta_data_unpacked['FileSize'],
            'file_mark': meta_data_unpacked['FileMark'],
            'track_number': meta_data_unpacked['TrackNumber'],
            'sample_rate': meta_data_unpacked['SampleRate']
        }

        with io.StringIO(track_data) as s:
            ret['album'] = s.read(meta_data_unpacked['AlbumLength'])
            ret['artist'] = s.read(meta_data_unpacked['ArtistLength'])
            ret['year'] = s.read(meta_data_unpacked['DateLength'])
            ret['filename'] = s.read(meta_data_unpacked['FileNameLength'])
            ret['genre'] = s.read(meta_data_unpacked['GenreLength'])
            ret['title'] = s.read(meta_data_unpacked['TitleLength'])

        return ret

    # -----------------------------------------------------
    # Properties

    def get_version(self):
        """Return the AIMP version as a tuple containing the major version and the build number, e.g ``('4.12', 1878)``.

        :rtype: tuple
        """
        version = self._get_prop(AIMP_RA_PROPERTY_VERSION)

        if not version:
            return None

        return ('{:.2f}'.format(win32api.HIWORD(version) / 100), win32api.LOWORD(version))

    def get_player_position(self):
        return self._get_prop(AIMP_RA_PROPERTY_PLAYER_POSITION)

    def set_player_position(self, position):
        self._set_prop(AIMP_RA_PROPERTY_PLAYER_POSITION, position)

    def get_current_track_duration(self):
        return self._get_prop(AIMP_RA_PROPERTY_PLAYER_DURATION)

    def get_playback_state(self):
        """Return the current playback state. The returned value is equal to one of the :class:`pyaimp.PlayBackState` enumeration.

        :rtype: int
        """
        return self._get_prop(AIMP_RA_PROPERTY_PLAYER_STATE)

    def get_volume(self):
        return self._get_prop(AIMP_RA_PROPERTY_VOLUME)

    def set_volume(self, volume):
        self._set_prop(AIMP_RA_PROPERTY_VOLUME, volume)

    def is_muted(self):
        return bool(self._get_prop(AIMP_RA_PROPERTY_MUTE))

    def set_muted(self, muted):
        self._set_prop(AIMP_RA_PROPERTY_MUTE, int(muted))

    def is_track_repeated(self):
        return bool(self._get_prop(AIMP_RA_PROPERTY_TRACK_REPEAT))

    def set_track_repeated(self, repeat):
        self._set_prop(AIMP_RA_PROPERTY_TRACK_REPEAT, int(repeat))

    def is_shuffled(self):
        return bool(self._get_prop(AIMP_RA_PROPERTY_TRACK_SHUFFLE))

    def set_shuffled(self, shuffled):
        self._set_prop(AIMP_RA_PROPERTY_TRACK_SHUFFLE, int(shuffled))

    def is_recording(self):
        return bool(self._get_prop(AIMP_RA_PROPERTY_RADIOCAP))

    def set_recording(self, recording):
        self._set_prop(AIMP_RA_PROPERTY_RADIOCAP, int(recording))

    def is_visualization_fullscreen(self):
        return bool(self._get_prop(AIMP_RA_PROPERTY_VISUAL_FULLSCREEN))

    def set_visualization_fullscreen(self, visualization_fullscreen):
        self._set_prop(AIMP_RA_PROPERTY_VISUAL_FULLSCREEN, int(visualization_fullscreen))

    # -----------------------------------------------------
    # Commands

    def play(self):
        self._send_command(AIMP_RA_CMD_PLAY)

    def play_pause(self):
        self._send_command(AIMP_RA_CMD_PLAYPAUSE)

    def pause(self):
        self._send_command(AIMP_RA_CMD_PAUSE)

    def stop(self):
        self._send_command(AIMP_RA_CMD_STOP)

    def next(self):
        self._send_command(AIMP_RA_CMD_NEXT)

    def prev(self):
        self._send_command(AIMP_RA_CMD_PREV)

    def next_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_NEXT)

    def prev_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_PREV)

    def quit(self):
        self._send_command(AIMP_RA_CMD_QUIT)

    def add_files_dialog(self):
        self._send_command(AIMP_RA_CMD_ADD_FILES)

    def add_folders_dialog(self):
        self._send_command(AIMP_RA_CMD_ADD_FOLDERS)

    def add_playlists_dialog(self):
        self._send_command(AIMP_RA_CMD_ADD_PLAYLISTS)

    def add_url_dialog(self):
        self._send_command(AIMP_RA_CMD_ADD_URL)

    def open_files_dialog(self):
        self._send_command(AIMP_RA_CMD_OPEN_FILES)

    def open_folders_dialog(self):
        self._send_command(AIMP_RA_CMD_OPEN_FOLDERS)

    def open_playlists_dialog(self):
        self._send_command(AIMP_RA_CMD_OPEN_PLAYLISTS)

    def start_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_START)

    def stop_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_STOP)

    def get_album_image(self):
        """Return the binary data of the album image of the current active track or ``None`` if... there's none.

        .. warning::

           This method is WIP and is unusable at this moment.

        :rtype: bytes or None
        """
        album_image_internal_window = AlbumImageInternalWindow()
        album_image_internal_window.start()

        time.sleep(0.5) # FIXME Temp because the below line runs before the thread even start

        res = self._send_command(AIMP_RA_CMD_GET_ALBUMART, album_image_internal_window.hwnd)

        if not res:
            return None

        return album_image_internal_window.image

    def start_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_START)

    def stop_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_STOP)

    # -----------------------------------------------------
    # Events

    # TODO

    # -----------------------------------------------------
    # CLI commands

    def add_to_playlist_and_play(self):
        """CLI ``/ADD_PLAY`` command: Add objects to a playlist and start playing."""
        pass

    def add_to_bookmarks(self):
        """CLI ``/BOOKMARK`` command: Add files and / or folders to your bookmarks."""
        pass

    def add_dirs_to_playlist(self):
        """CLI ``/DIR`` command: Add folder(s) to the playlist."""
        pass

    def add_files_to_playlist(self):
        """CLI ``/FILE`` command: Add file(s) to the playlist."""
        pass

    def add_to_active_playlist(self, obj):
        """CLI ``/INSERT`` command: Add objects to the active playlist."""
        self._run_cli_command('INSERT', obj)

    def add_to_active_playlist_custom(self):
        """CLI ``/QUEUE`` command: Add objects to the active playlist and put them in custom playback queue."""
        pass
