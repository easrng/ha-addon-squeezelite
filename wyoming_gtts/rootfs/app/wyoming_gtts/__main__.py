#!/usr/bin/env python3
import argparse
import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import Any, Dict, Set

from wyoming.info import Attribution, Info, TtsProgram, TtsVoice, TtsVoiceSpeaker
from wyoming.server import AsyncServer

from . import __version__
from .download import get_voices
from .handler import LocalGTTSEventHandler

_LOGGER = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--voice",
        default="en-US-hol-female",
        help="Default voice to use (e.g., en-US-hol-female)",
    )
    parser.add_argument(
        "--uri",
        default="tcp://127.0.0.1:15000",
        help="unix:// or tcp://"
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Data directory to check for downloaded models",
    )
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    parser.add_argument(
        "--log-format", default=logging.BASIC_FORMAT, help="Format for log messages"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Print version and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO, format=args.log_format
    )
    _LOGGER.debug(args)

    # Load voice info
    voices_info = get_voices(Path(__file__), False)

    # Resolve aliases for backwards compatibility with old voice names
    aliases_info: Dict[str, Any] = {}
    for voice_info in voices_info.values():
        for voice_alias in voice_info.get("aliases", []):
            aliases_info[voice_alias] = {"_is_alias": True, **voice_info}

    voices_info.update(aliases_info)
    voices = [
        TtsVoice(
            name=voice_name,
            description=get_description(voice_info),
            attribution=Attribution(
                name="google", url=""
            ),
            installed=True,
            version=None,
            languages=[
                voice_info.get("language", {}).get(
                    "code",
                    voice_info.get("espeak", {}).get("voice", voice_name.split("_")[0]),
                )
            ],
            speakers=[
                TtsVoiceSpeaker(name=speaker_name)
                for speaker_name in voice_info["speaker_id_map"]
            ]
            if voice_info.get("speaker_id_map")
            else None,
        )
        for voice_name, voice_info in voices_info.items()
        if not voice_info.get("_is_alias", False)
    ]

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="Local Google TTS",
                description="Local Google TTS",
                attribution=Attribution(
                    name="google", url=""
                ),
                installed=True,
                voices=sorted(voices, key=lambda v: v.name),
                version=__version__,
            )
        ],
    )

    # Start server
    server = AsyncServer.from_uri(args.uri)

    _LOGGER.info("Ready")

    # aaaa = partial(
    #     LocalGTTSEventHandler,
    #     wyoming_info,
    #     args,
    # )
    #
    # await server.run(
    #     aaaa
    # )
    await server.run(
        partial(
            LocalGTTSEventHandler,
            wyoming_info,
            args,
        )
    )


# -----------------------------------------------------------------------------


def get_description(voice_info: Dict[str, Any]):
    """Get a human readable description for a voice."""
    name = voice_info["name"]
    name = " ".join(name.split("_"))
    quality = voice_info["quality"]

    return f"{name} ({quality})"


# -----------------------------------------------------------------------------


def run():
    asyncio.run(main())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
