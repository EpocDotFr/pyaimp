from mmapfile import mmapfile
from enum import Enum
from collections import OrderedDict
import struct
import win32gui
import win32api
import win32con
import win32process
import io
import subprocess

__version__ = '0.2.1'

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


class PlayBackState(Enum):
    """Enumeration (extending :py:class:`enum.Enum`) of all possible AIMP playback states.

    May be used in conjonction with :func:`pyaimp.Client.get_playback_state` result."""

    Stopped = 0 #: There's currently no track being played.
    Paused = 1 #: The current track playback is currently suspended.
    Playing = 2 #: A track is being played.


class Client:
    """Main class of the ``pyaimp`` module which is the wrapper around the AIMP remote API.

    When a new instance of this class is created, it will search for the current AIMP window
    handle using :func:`pyaimp.Client.detect_aimp`. If none are found, a ``RuntimeError``
    exception will be raised.

    .. note::

       Consider all methods in this class to be **blocking**.

    :raises RuntimeError: The AIMP window cannot be found.
    """

    def __init__(self):
        self.detect_aimp()

    def _get_aimp_window(self):
        """Find the AIMP window handler who provides the remote API calls endpoint.

        :raises RuntimeError: The AIMP window cannot be found.
        :rtype: None
        """
        self._aimp_window = win32gui.FindWindow(AIMPRemoteAccessClass, None)

        if not self._aimp_window:
            raise RuntimeError('Unable to find the AIMP window. Are you sure it is running?')

    def _get_aimp_exe_path(self):
        """Find the AIMP executable path given its window handler.

        :raises RuntimeError: The AIMP executable path cannot be found.
        :rtype: None
        """
        win_thread_proc_id = win32process.GetWindowThreadProcessId(self._aimp_window)

        pwnd = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, win_thread_proc_id[1])

        self._aimp_exe_path = win32process.GetModuleFileNameEx(pwnd, None)

        if not self._aimp_exe_path:
            raise RuntimeError('Unable to retrieve the AIMP executable.')

    def _get_prop(self, prop_id):
        """Retrieve an AIMP property."""
        return win32api.SendMessage(self._aimp_window, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_GET, 0)

    def _set_prop(self, prop_id, value):
        """Set an AIMP property."""
        win32api.SendMessage(self._aimp_window, WM_AIMP_PROPERTY, prop_id | AIMP_RA_PROPVALUE_SET, value)

    def _send_command(self, command_id, parameter=None):
        """Send an AIMP command."""
        return win32api.SendMessage(self._aimp_window, WM_AIMP_COMMAND, command_id, parameter)

    def _run_cli_command(self, command, param1=None):
        """Run an AIMP CLI command."""
        cli = [
            self._aimp_exe_path,
            '/' + command.upper(),
            param1
        ]

        subprocess.run(cli, check=True)

    def detect_aimp(self):
        """
        Detect the AIMP window handler and the full path to its executable, which are required in order
        to be able to remote control AIMP.

        This method is automatically called for you when creating a new instance of this class.

        This method may be useful for you when AIMP is closed, then restarted for any reason. You'll
        need to call it to retrieve the newly created AIMP window handler or you won't be able to use the
        same instance anymore.

        There isn't anything returned because it defines internal attributes.

        :raises RuntimeError: The AIMP window cannot be found.
        :rtype: None
        """
        self._get_aimp_window()
        self._get_aimp_exe_path()

    def get_current_track_info(self):
        """Return a dictionary of information about the current active track.

        Dictionary keys are:

          - ``bit_rate`` (``int``): `Audio bit rate <https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate>`_
          - ``channels`` (``int``): Number of `audio channels <https://en.wikipedia.org/wiki/Audio_signal>`_
          - ``duration`` (``int``): Duration of the track, in milliseconds. `0` if unknown or none (i.e a stream)
          - ``file_size`` (``int``): Size of the file, in bytes. `0` if unknown or none (i.e a stream)
          - ``file_mark`` (``int``): Unknown
          - ``track_number`` (``int``): Track number (as stored in the audio tags). `0` if unknown
          - ``sample_rate`` (``int``): `Audio sample rate <https://en.wikipedia.org/wiki/Sampling_(signal_processing)#Sampling_rate>`_
          - ``album`` (``str``): Album name or an empty string if none
          - ``artist`` (``str``): Artist name or an empty string if unknown
          - ``year`` (``int``): Track year or an empty string if unknown
          - ``filename`` (``str``): Path to the track or URL to the stream
          - ``genre`` (``str``): Track genre or an empty string if unknown
          - ``title`` (``str``): Track title or an empty string if unknown

        .. warning::

           This method is experimental and should be used with caution. See `this issue <https://github.com/EpocDotFr/pyaimp/issues/1>`_ for more information.

        :rtype: dict
        """

        mapped_file = mmapfile(None, AIMPRemoteAccessClass, MaximumSize=AIMPRemoteAccessMapFileSize)

        pack_format = ''.join(AIMPRemoteAccessPackFormat.values())

        meta_data_raw = mapped_file.read(struct.calcsize(pack_format))

        meta_data_unpacked = dict(zip(AIMPRemoteAccessPackFormat.keys(), struct.unpack(pack_format, meta_data_raw)))

        track_data = mapped_file.read(mapped_file.size() - mapped_file.tell()).decode().replace('\x00', '')

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
        """Return the current player position as the number of elapsed milliseconds since the beginning of the track.

        :rtype: int
        """
        return self._get_prop(AIMP_RA_PROPERTY_PLAYER_POSITION)

    def set_player_position(self, position):
        """Set the current player position.

        :param int position: Number of elapsed milliseconds since the beginning of the track
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_PLAYER_POSITION, position)

    def get_current_track_duration(self):
        """Return the current track duration, in milliseconds.

        :rtype: int
        """
        return self._get_prop(AIMP_RA_PROPERTY_PLAYER_DURATION)

    def get_playback_state(self):
        """Return the current playback state. The returned value is equal to one of the :class:`pyaimp.PlayBackState` enumeration.

        :rtype: pyaimp.PlayBackState.Stopped or pyaimp.PlayBackState.Paused or pyaimp.PlayBackState.Playing
        """
        current_playback_state = self._get_prop(AIMP_RA_PROPERTY_PLAYER_STATE)

        for playback_state in PlayBackState:
            if playback_state.value == current_playback_state:
                return playback_state

        return None

    def get_volume(self):
        """Return the current volume, in percents.

        :rtype: int
        """
        return self._get_prop(AIMP_RA_PROPERTY_VOLUME)

    def set_volume(self, volume):
        """Set the current volume.

        :param int volume: The new volume, in percent
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_VOLUME, volume)

    def is_muted(self):
        """Return the muted state of the player.

        :rtype: bool
        """
        return bool(self._get_prop(AIMP_RA_PROPERTY_MUTE))

    def set_muted(self, muted):
        """Set the muted state of the player.

        :param bool muted: Whether the player should be muted or not
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_MUTE, int(muted))

    def is_track_repeated(self):
        """Return the repeat state of the player.

        :rtype: bool
        """
        return bool(self._get_prop(AIMP_RA_PROPERTY_TRACK_REPEAT))

    def set_track_repeated(self, repeat):
        """Set the repeat state of the player.

        :param bool repeat: Whether the track should be repeated or not
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_TRACK_REPEAT, int(repeat))

    def is_shuffled(self):
        """Return the shuffle state of the player.

        :rtype: bool
        """
        return bool(self._get_prop(AIMP_RA_PROPERTY_TRACK_SHUFFLE))

    def set_shuffled(self, shuffled):
        """Set the shuffle state of the player.

        :param bool shuffled: Whether the tracks should be shuffled or not
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_TRACK_SHUFFLE, int(shuffled))

    def is_recording(self):
        """Return the radio recording state of the player.

        :rtype: bool
        """
        return bool(self._get_prop(AIMP_RA_PROPERTY_RADIOCAP))

    def set_recording(self, recording):
        """Set the radio recording state of the player.

        :param bool recording: Whether the radio recording should be active or not
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_RADIOCAP, int(recording))

    def is_visualization_fullscreen(self):
        """Return whether the visualization is fullscreen or not.

        :rtype: bool
        """
        return bool(self._get_prop(AIMP_RA_PROPERTY_VISUAL_FULLSCREEN))

    def set_visualization_fullscreen(self, visualization_fullscreen):
        """Set the visualization to be fullscreen or not.

        :param bool visualization_fullscreen: Whether the visualization should be fullscreen or not
        :rtype: None
        """
        self._set_prop(AIMP_RA_PROPERTY_VISUAL_FULLSCREEN, int(visualization_fullscreen))

    # -----------------------------------------------------
    # Commands

    def play(self):
        """Different behaviors may be encountered when using this method:

          - If the player is stopped, this will start playback.
          - If the player is paused, this will resume playback.
          - If the player is playing, this will start playback from beginning.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_PLAY)

    def play_pause(self):
        """Different behaviors may be encountered when using this method:

          - If the player is stopped, this will start playback.
          - If the player is paused, this will resume playback.
          - If the player is playing, this will start pauses playback.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_PLAYPAUSE)

    def pause(self):
        """Different behaviors may be encountered when using this method:

          - If the player is playing, this will pause playback.
          - If the player is paused, this will resume playback.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_PAUSE)

    def stop(self):
        """Stop the playback.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_STOP)

    def next(self):
        """Start playing the next track in the playlist.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_NEXT)

    def prev(self):
        """Start playing the previous track in the playlist.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_PREV)

    def next_visualization(self):
        """Start the next visualization.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_VISUAL_NEXT)

    def prev_visualization(self):
        """Start the previous visualization.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_VISUAL_PREV)

    def quit(self):
        """Shutdown and exit AIMP.

        You'll obviously not be able to do anything after using this method until AIMP is opened again and
        :func:`pyaimp.Client.detect_aimp` is manually called.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_QUIT)

    def add_files_dialog(self):
        """Display the "Add Files" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_ADD_FILES)

    def add_folders_dialog(self):
        """Display the "Add Folders" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_ADD_FOLDERS)

    def add_playlists_dialog(self):
        """Display the "Add Playlists" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_ADD_PLAYLISTS)

    def add_url_dialog(self):
        """Display the "Add URLs" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_ADD_URL)

    def open_files_dialog(self):
        """Display the "Open Files" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_OPEN_FILES)

    def open_folders_dialog(self):
        """Display the "Open Folders" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_OPEN_FOLDERS)

    def open_playlists_dialog(self):
        """Display the "Open Playlists" dialog window.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_OPEN_PLAYLISTS)

    def start_visualization(self):
        """Start the visualization.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_VISUAL_START)

    def stop_visualization(self):
        """Stop the visualization.

        :rtype: None
        """
        self._send_command(AIMP_RA_CMD_VISUAL_STOP)

    # -----------------------------------------------------
    # CLI commands

    def add_to_playlist_and_play(self, obj):
        """CLI ``/ADD_PLAY`` command: Add objects to a playlist and start playing.

        :param str obj: Path to a playlist, folder or file
        :rtype: None
        """
        self._run_cli_command('ADD_PLAY', obj)

    def add_to_bookmarks(self, obj):
        """CLI ``/BOOKMARK`` command: Add files and/or folders to your bookmarks.

        :param str obj: Path to a folder or file
        :rtype: None
        """
        self._run_cli_command('BOOKMARK', obj)

    def add_dirs_to_playlist(self, dir):
        """CLI ``/DIR`` command: Add folder(s) to the playlist.

        Whether playing of added the files starts depends on the player settings.

        :param str dir: Path to a directory
        :rtype: None
        """
        self._run_cli_command('DIR', dir)

    def add_files_to_playlist(self, file):
        """CLI ``/FILE`` command: Add file(s) to the playlist.

        Whether playing of added the files starts depends on the player settings.

        :param str file: Path to a file
        :rtype: None
        """
        self._run_cli_command('FILE', file)

    def add_to_active_playlist(self, obj):
        """CLI ``/INSERT`` command: Add objects to the active playlist.

        Whether playing of added the files starts depends on the player settings.

        :param str obj: Path to a playlist, folder or file
        :rtype: None
        """
        self._run_cli_command('INSERT', obj)

    def add_to_active_playlist_custom(self, obj):
        """CLI ``/QUEUE`` command: Add objects to the active playlist and put them in custom playback queue.

        :param str obj: Path to a playlist, folder or file
        :rtype: None
        """
        self._run_cli_command('QUEUE', obj)
