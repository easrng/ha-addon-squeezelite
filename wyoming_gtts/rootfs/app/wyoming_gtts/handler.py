"""Event handler for clients of the server."""
import argparse
import logging

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import Synthesize

from .local_gtts import LocalGTTS

_LOGGER = logging.getLogger(__name__)


def parser_voice_name(voice_name: str):
    vns = voice_name.split('-')
    language = "-".join(vns[:2])
    name = vns[2]
    gender = vns[3]
    return language, name, gender


class LocalGTTSEventHandler(AsyncEventHandler):
    """Event handler for clients of the server."""

    def __init__(
            self,
            wyoming_info: Info,
            cli_args: argparse.Namespace,
            *args,
            **kwargs,
    ) -> None:
        """Initialize."""
        super().__init__(*args, **kwargs)

        self.cli_args = cli_args
        self.wyoming_info_event = wyoming_info.event()
        language, name, gender = parser_voice_name(cli_args.voice)
        self.tts = LocalGTTS(cli_args.data_dir, language, name, gender)

    async def handle_event(self, event: Event) -> bool:
        """Handle an event."""
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if not Synthesize.is_type(event.type):
            _LOGGER.warning("Unexpected event: %s", event)
            return True

        synthesize = Synthesize.from_event(event)
        _LOGGER.debug(synthesize)

        # raw_text = synthesize.text
        #
        # # Join multiple lines
        # text = " ".join(raw_text.strip().splitlines())
        #
        # if self.cli_args.auto_punctuation and text:
        #     # Add automatic punctuation (important for some voices)
        #     has_punctuation = False
        #     for punc_char in self.cli_args.auto_punctuation:
        #         if text[-1] == punc_char:
        #             has_punctuation = True
        #             break
        #
        #     if not has_punctuation:
        #         text = text + self.cli_args.auto_punctuation[0]
        try:
            language, name, gender = parser_voice_name(synthesize.voice.name)
            _LOGGER.debug("check if we can reuse: " + language + ", " + self.tts.language)
            if language == self.tts.language:
                if name != self.tts.speaker:
                    self.tts.set_speaker(name, gender)
            else:
                _LOGGER.debug("recreating...")
                del self.tts
                self.tts = LocalGTTS(self.cli_args.data_dir, language, name, gender)

        except AttributeError:
            pass
        self.tts.init_synthesis(text=synthesize.text)

        await self.write_event(
            AudioStart(
                rate=self.tts.sample_rate,
                width=self.tts.data_width,
                channels=self.tts.channels,
            ).event(),
        )

        while True:
            res, chunk = self.tts.read_audio_buf()
            if res > 0:
                await self.write_event(
                    AudioChunk(
                        audio=chunk,
                        rate=self.tts.sample_rate,
                        width=self.tts.data_width,
                        channels=self.tts.channels,
                    ).event(),
                )
            else:
                break

        await self.write_event(AudioStop().event())
        _LOGGER.debug("Completed request")

        return True
