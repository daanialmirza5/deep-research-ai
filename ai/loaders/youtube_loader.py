import asyncio
import re
from typing import ClassVar

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import YouTubeTranscriptApiException

from ai.loaders.base import BaseLoader, LoaderError

_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})")


def _extract_video_id(url: str) -> str:
    match = _VIDEO_ID.search(url)
    if not match:
        raise LoaderError(f"could not find a video id in {url!r}")
    return match.group(1)


def _fetch_transcript_text(video_id: str) -> str:
    transcript = YouTubeTranscriptApi().fetch(video_id)
    return " ".join(snippet.text for snippet in transcript)


class YoutubeLoader(BaseLoader):
    """Fetches the video's transcript/captions. `source` is the video URL."""

    source_type: ClassVar[str] = "youtube"

    async def load(self, source: bytes | str) -> str:
        if not isinstance(source, str):
            raise LoaderError("YoutubeLoader expects a URL string")
        video_id = _extract_video_id(source)
        try:
            text = await asyncio.to_thread(_fetch_transcript_text, video_id)
        except YouTubeTranscriptApiException as exc:
            raise LoaderError(f"could not fetch transcript for {source}: {exc}") from exc

        if not text.strip():
            raise LoaderError(f"transcript for {source} was empty")
        return text
