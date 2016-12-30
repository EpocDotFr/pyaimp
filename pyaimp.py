from mmapfile import mmapfile
from win32con import WM_USER
from enum import Enum
from io import StringIO
import struct
import win32gui
import win32api

__version__ = '0.1.0'

__all__ = [
    'PlayerState',
    'Client'
]

AIMPRemoteAccessClass = 'AIMP2_RemoteInfo'
AIMPRemoteAccessMapFileSize = 2048

# -----------------------------------------------------
# Message types to send to AIMP

WM_AIMP_COMMAND = WM_USER + 0x75
WM_AIMP_NOTIFY = WM_USER + 0x76
WM_AIMP_PROPERTY = WM_USER + 0x77

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

class PlayerState(Enum):
    Stopped = 0
    Paused = 1
    Playing = 2


class Client:
    def __init__(self):
        self._hwnd = win32gui.FindWindow(AIMPRemoteAccessClass, None)

        if not self._hwnd:
            raise RuntimeError('Unable to find the AIMP instance. Are you sure it is running?')

    def _get_prop(self, prop_id):
        return win32api.SendMessage(self._hwnd, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_GET, 0)

    def _set_prop(self, prop_id, value):
        win32api.SendMessage(self._hwnd, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_SET, value)

    def _send_command(self, command_id, parameter=None):
        return win32api.SendMessage(self._hwnd, WM_AIMP_COMMAND, command_id, parameter)

    def get_current_track_infos(self):
        mapped_file = mmapfile(None, AIMPRemoteAccessClass, MaximumSize=AIMPRemoteAccessMapFileSize)

        pack_format = 'L ? L L L l L L L L L L L L L 6I'

        meta_data = mapped_file.read(struct.calcsize(pack_format))

        meta_data_to_unpack = [
            'Deprecated1',
            'Active',
            'BitRate',
            'Channels',
            'Duration',
            'FileSize',
            'FileMark',
            'TrackNumber',
            'SampleRate',
            'AlbumLength',
            'Deprecated2',
            'ArtistLength',
            'DateLength',
            'FileNameLength',
            'GenreLength',
            'TitleLength'
        ]

        meta_data_unpacked = dict(zip(meta_data_to_unpack, struct.unpack(pack_format, meta_data)))

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

        with StringIO(track_data) as s:
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

    def get_player_state(self):
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

    def add_files(self):
        self._send_command(AIMP_RA_CMD_ADD_FILES)

    def add_folders(self):
        self._send_command(AIMP_RA_CMD_ADD_FOLDERS)

    def add_playlists(self):
        self._send_command(AIMP_RA_CMD_ADD_PLAYLISTS)

    def add_url(self):
        self._send_command(AIMP_RA_CMD_ADD_URL)

    def open_files(self):
        self._send_command(AIMP_RA_CMD_OPEN_FILES)

    def open_folders(self):
        self._send_command(AIMP_RA_CMD_OPEN_FOLDERS)

    def open_playlists(self):
        self._send_command(AIMP_RA_CMD_OPEN_PLAYLISTS)

    def get_album_image(self):
        album_art = self._send_command(AIMP_RA_CMD_GET_ALBUMART)

        if not album_art:
            return None

        # TODO

    def start_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_START)

    def stop_visualization(self):
        self._send_command(AIMP_RA_CMD_VISUAL_STOP)

    # -----------------------------------------------------
    # Events

    # TODO