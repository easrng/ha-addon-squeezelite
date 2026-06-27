"""Microsoft TTS."""

import ctypes
import wyoming_gtts.tts_pb2 as Utterance  # protoc tts.proto --python_out=.
import wyoming_gtts.speaker_pb2 as Speaker  # protoc speaker.proto --python_out=.

import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

c_float_p = ctypes.POINTER(ctypes.c_float)
c_int_p = ctypes.POINTER(ctypes.c_int)


class LocalGTTS:
    """Class to handle local Google TTS."""
    sample_rate = 24000
    data_width = 4
    channels = 1

    def __init__(self, data_dir, language, speaker, gender) -> None:
        """Initialize."""
        _LOGGER.debug("Initialize local Google TTS")

        lib_name = 'libchrometts.so'
        pipeline_name = 'pipeline.pb'

        data_path = Path(data_dir)
        lib_path = data_path.joinpath(lib_name)
        self.language = language
        self.speaker = speaker
        self.gender = gender

        voice_path = data_path.joinpath(self.language)
        pipeline_path = voice_path.joinpath(pipeline_name)

        self.ttslib = ctypes.CDLL(str(lib_path))
        self.ttslib.GoogleTtsInit(bytes(str(pipeline_path).encode('utf8')), bytes(str(voice_path).encode('utf8')))
        self.set_speaker(self.speaker, self.gender)

    def __del__(self):
        self.ttslib.GoogleTtsShutdown()

    def set_speaker(self, name, gender):
        v = Speaker.Speaker()
        v.name = name
        v.gender = gender
        self.speaker_jspb = v.SerializeToString()

    def init_synthesis(self, text):
        """Begin synthesize text to speech."""
        _LOGGER.debug(f"Requested TTS for [{text}]")
        u = Utterance.Utterance()
        u.a.b.text = text
        u.a.b.params.pitch = 1.
        u.a.b.params.speed = 1.
        text_jspb = u.SerializeToString()
        self.ttslib.GoogleTtsInitBuffered(text_jspb, self.speaker_jspb, len(text_jspb), len(self.speaker_jspb))
        self.buf_len = self.ttslib.GoogleTtsGetFramesInAudioBuffer()
        self.audio_buffer = (ctypes.c_char * (self.buf_len * 4))()
        self.buf_fp = ctypes.cast(self.audio_buffer, c_float_p)
        self.buf_ip = ctypes.cast(self.audio_buffer, c_int_p)
        self.frames_in_buf = (ctypes.c_int * 1)()

    def read_audio_buf(self):
        res = self.ttslib.GoogleTtsReadBuffered(ctypes.cast(self.audio_buffer, c_float_p),
                                                ctypes.cast(self.frames_in_buf, c_int_p))
        for i in range(self.buf_len):
            val = self.buf_fp[i] * 2147483647
            self.buf_ip[i] = 0 if math.isnan(val) else val

        return res, self.audio_buffer[:]
