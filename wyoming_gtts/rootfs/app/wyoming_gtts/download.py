"""Utility for downloading Piper voices."""
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple, Union
from urllib.error import URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import urlopen

URL_FORMAT = "{file}"

_DIR = Path(__file__).parent
_LOGGER = logging.getLogger(__name__)

_SKIP_FILES = {"MODEL_CARD"}


class VoiceNotFoundError(Exception):
    pass


def _quote_url(url: str) -> str:
    """Quote file part of URL in case it contains UTF-8 characters."""
    parts = list(urlsplit(url))
    parts[2] = quote(parts[2])
    return urlunsplit(parts)


def get_voices(
    download_dir: Union[str, Path], update_voices: bool = False
) -> Dict[str, Any]:
    """Loads available voices from downloaded or embedded JSON file."""
    download_dir = Path(download_dir)
    voices_download = download_dir / "voices.json"

    if update_voices:
        # Download latest voices.json
        try:
            voices_url = URL_FORMAT.format(file="voices.json")
            _LOGGER.debug("Downloading %s to %s", voices_url, voices_download)
            with urlopen(_quote_url(voices_url)) as response:
                with open(voices_download, "wb") as download_file:
                    shutil.copyfileobj(response, download_file)
        except Exception:
            _LOGGER.exception("Failed to update voices list")

    # Prefer downloaded file to embedded
    if voices_download.exists():
        try:
            _LOGGER.debug("Loading %s", voices_download)
            with open(voices_download, "r", encoding="utf-8") as voices_file:
                return json.load(voices_file)
        except Exception:
            _LOGGER.exception("Failed to load %s", voices_download)

    # Fall back to embedded
    voices_embedded = _DIR / "voices.json"
    _LOGGER.debug("Loading %s", voices_embedded)
    with open(voices_embedded, "r", encoding="utf-8") as voices_file:
        return json.load(voices_file)
