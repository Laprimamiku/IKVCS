import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ASRService:
    """Cloud ASR service wrapper (GLM-ASR-2512)."""

    def __init__(self) -> None:
        self.api_key = settings.ASR_API_KEY or settings.LLM_API_KEY
        self.base_url = (settings.ASR_BASE_URL or "").rstrip("/")
        self.model = settings.ASR_MODEL
        endpoint = (getattr(settings, "ASR_ENDPOINT", "") or "").strip()
        if not endpoint:
            endpoint = "/audio/transcriptions"
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        self.endpoint = endpoint
        self.timeout = float(getattr(settings, "ASR_TIMEOUT", 120.0) or 120.0)
        self.max_chunk_seconds = 30
        self.max_concurrent = 5
        self.sample_rate = 16000

    async def transcribe(self, audio_bytes: bytes, filename: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.base_url or not self.model:
            logger.error("[ASR] Missing ASR config: api_key/base_url/model")
            return None

        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": (filename, audio_bytes, "application/octet-stream")}
        data = {"model": self.model}
        url = f"{self.base_url}{self.endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, data=data, files=files)
            if resp.status_code != 200:
                logger.error("[ASR] request failed: %s - %s", resp.status_code, resp.text)
                return None
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("[ASR] request error: %s", exc)
            return None

    async def transcribe_media_file(
        self,
        source_path: Path,
        chunk_seconds: int = 30,
        max_concurrent: int = 5,
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        if not self.api_key or not self.base_url or not self.model:
            error = "Missing ASR config: api_key/base_url/model"
            logger.error("[ASR] %s", error)
            errors.append({"error": error})
            return None, errors

        duration = self._get_media_duration(source_path)
        if duration <= 0:
            error = f"Failed to read media duration: {source_path}"
            logger.error("[ASR] %s", error)
            errors.append({"error": error})
            return None, errors

        chunk_seconds = max(5, int(chunk_seconds or self.max_chunk_seconds))
        if chunk_seconds > self.max_chunk_seconds:
            logger.warning("[ASR] chunk_seconds %s exceeds limit; forcing to %s", chunk_seconds, self.max_chunk_seconds)
            chunk_seconds = self.max_chunk_seconds

        chunk_count = int((duration + chunk_seconds - 1) // chunk_seconds)
        max_concurrent = max(1, int(max_concurrent or self.max_concurrent))
        if max_concurrent > self.max_concurrent:
            logger.warning("[ASR] max_concurrent %s exceeds limit; forcing to %s", max_concurrent, self.max_concurrent)
            max_concurrent = self.max_concurrent

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_chunk(idx: int) -> Dict[str, Any]:
            start = idx * chunk_seconds
            length = min(chunk_seconds, duration - start)
            audio_path, err = self._build_chunk_audio(source_path, start, length)
            if not audio_path:
                return {
                    "chunk": {
                        "index": idx,
                        "start": start,
                        "end": start + length,
                        "text": "",
                        "segments": [],
                        "raw_response": err,
                    },
                    "error": {"chunk_index": idx, "start": start, "error": err},
                }

            try:
                ok, response = await self._call_asr_file(audio_path)
            finally:
                try:
                    audio_path.unlink(missing_ok=True)
                except Exception:
                    pass

            if not ok:
                return {
                    "chunk": {
                        "index": idx,
                        "start": start,
                        "end": start + length,
                        "text": "",
                        "segments": [],
                        "raw_response": response,
                    },
                    "error": {"chunk_index": idx, "start": start, "error": response},
                }

            text, raw_segments = self._extract_text_and_segments(response)
            if raw_segments:
                segments = self._normalize_segments(raw_segments, length)
            else:
                segments = self._split_text_to_segments(text, length)
                if not segments and text:
                    segments = [{"index": 0, "start": 0.0, "end": length, "text": text}]

            for seg in segments:
                seg["start"] = float(seg.get("start", 0.0)) + start
                seg["end"] = float(seg.get("end", seg.get("start", 0.0))) + start

            return {
                "chunk": {
                    "index": idx,
                    "start": start,
                    "end": start + length,
                    "text": text,
                    "segments": segments,
                    "raw_response": response,
                },
                "error": None,
            }

        async def guarded_process(idx: int) -> Dict[str, Any]:
            async with semaphore:
                return await process_chunk(idx)

        tasks = [asyncio.create_task(guarded_process(i)) for i in range(chunk_count)]
        results = await asyncio.gather(*tasks)

        chunks: List[Dict[str, Any]] = []
        for item in results:
            chunk = item.get("chunk")
            if chunk:
                chunks.append(chunk)
            error = item.get("error")
            if error:
                errors.append(error)

        chunks.sort(key=lambda c: c.get("index", 0))
        full_text_parts: List[str] = []
        all_segments: List[Dict[str, Any]] = []
        for chunk in chunks:
            text = (chunk.get("text") or "").strip()
            if text:
                full_text_parts.append(text)
            all_segments.extend(chunk.get("segments", []))

        all_segments.sort(key=lambda s: s.get("start", 0.0))
        for i, seg in enumerate(all_segments):
            seg["index"] = i

        full_text = "\n".join(full_text_parts).strip()
        if not all_segments and not full_text:
            logger.error("[ASR] No valid subtitles produced: %s", source_path)
            return None, errors

        payload = {
            "model": self.model,
            "duration": duration,
            "chunk_seconds": chunk_seconds,
            "text": full_text,
            "segments": all_segments,
        }
        return payload, errors

    def extract_segments(self, payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        segments = self._find_segments(payload)
        text = self._find_text(payload)
        normalized: List[Dict[str, Any]] = []

        if segments:
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                start = self._to_float(seg.get("start") or seg.get("start_time") or seg.get("begin_time"))
                end = self._to_float(seg.get("end") or seg.get("end_time") or seg.get("finish_time"))
                content = seg.get("text") or seg.get("sentence") or seg.get("result")
                content = (content or "").strip()
                if content:
                    normalized.append(
                        {
                            "start_time": max(0.0, start),
                            "end_time": max(0.0, end if end >= start else start + 1.5),
                            "text": content,
                        }
                    )
            if not text:
                text = "\n".join(item["text"] for item in normalized if item.get("text"))

        if not normalized and text:
            normalized = self._fallback_segments(text)

        return normalized, text

    def _find_segments(self, payload: Any) -> Optional[List[Dict[str, Any]]]:
        if isinstance(payload, list):
            if payload and all(isinstance(item, dict) for item in payload):
                return payload
        if isinstance(payload, dict):
            for key in ("segments", "segment_list", "segment"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            for key in ("data", "result", "output"):
                value = payload.get(key)
                found = self._find_segments(value)
                if found:
                    return found
        return None

    def _find_text(self, payload: Any) -> str:
        if isinstance(payload, list):
            texts = []
            for item in payload:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    texts.append(item.get("text").strip())
            return "\n".join([t for t in texts if t])
        if isinstance(payload, dict):
            for key in ("text", "result", "transcript"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value.strip()
            for key in ("data", "output"):
                value = payload.get(key)
                text = self._find_text(value)
                if text:
                    return text
        return ""

    def _fallback_segments(self, text: str) -> List[Dict[str, Any]]:
        chunks = [chunk.strip() for chunk in re.split(r"(?<=[。！？.!?])\s+", text) if chunk.strip()]
        if not chunks:
            chunks = [text.strip()]
        segments: List[Dict[str, Any]] = []
        cursor = 0.0
        for chunk in chunks:
            duration = min(6.0, max(2.0, len(chunk) / 8.0))
            segments.append(
                {
                    "start_time": round(cursor, 2),
                    "end_time": round(cursor + duration, 2),
                    "text": chunk,
                }
            )
            cursor += duration
        return segments

    def _to_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _run_command(self, command: List[str]) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"
        if result.returncode != 0:
            return False, result.stderr.decode(errors="ignore")
        return True, ""

    def _get_media_duration(self, source_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source_path),
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            logger.error("[ASR] ffprobe not found in PATH")
            return 0.0
        if result.returncode != 0:
            logger.error("[ASR] ffprobe failed: %s", result.stderr.decode(errors="ignore"))
            return 0.0
        try:
            return float(result.stdout.decode().strip() or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _build_chunk_audio(self, source_path: Path, start: float, duration: float) -> Tuple[Optional[Path], Optional[str]]:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        output_path = Path(tmp.name)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        ok, err = self._run_command(cmd)
        if not ok:
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None, err
        return output_path, None

    def _guess_mime_type(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".wav":
            return "audio/wav"
        if ext == ".mp3":
            return "audio/mpeg"
        if ext == ".m4a":
            return "audio/mp4"
        if ext == ".aac":
            return "audio/aac"
        if ext == ".flac":
            return "audio/flac"
        if ext == ".ogg":
            return "audio/ogg"
        if ext == ".opus":
            return "audio/opus"
        return "application/octet-stream"

    async def _call_asr_file(self, audio_path: Path) -> Tuple[bool, Any]:
        url = f"{self.base_url}{self.endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": self.model}
        timeout = httpx.Timeout(self.timeout)
        try:
            with audio_path.open("rb") as f:
                files = {"file": (audio_path.name, f, self._guess_mime_type(audio_path))}
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, data=data, files=files)
        except Exception as exc:  # noqa: BLE001
            return False, f"Request error: {exc}"

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:500]}"

        try:
            return True, response.json()
        except Exception:
            return True, response.text

    def _extract_text_and_segments(self, data: Any) -> Tuple[str, List[Dict[str, Any]]]:
        if isinstance(data, dict):
            text = data.get("text") or data.get("transcript") or ""
            segments = data.get("segments") or data.get("results") or []
            if isinstance(segments, list):
                return str(text), segments
            return str(text), []
        if isinstance(data, str):
            return data, []
        return "", []

    def _normalize_segments(self, segments: List[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for idx, seg in enumerate(segments):
            start = seg.get("start")
            end = seg.get("end")
            text = seg.get("text") or seg.get("content") or ""
            try:
                start = float(start)
            except (TypeError, ValueError):
                start = 0.0
            try:
                end = float(end)
            except (TypeError, ValueError):
                end = start + 2.0
            normalized.append(
                {
                    "index": idx,
                    "start": max(0.0, start),
                    "end": max(0.0, end),
                    "text": str(text).strip(),
                }
            )

        if normalized:
            return normalized

        if duration <= 0:
            duration = 5.0
        return [{"index": 0, "start": 0.0, "end": duration, "text": ""}]

    def _split_text_to_segments(self, text: str, duration: float) -> List[Dict[str, Any]]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []

        sentence_parts = re.split(r"([。！？.!?\n]+)", cleaned)
        sentences: List[str] = []
        for i in range(0, len(sentence_parts), 2):
            chunk = sentence_parts[i].strip()
            if i + 1 < len(sentence_parts):
                chunk = f"{chunk}{sentence_parts[i + 1]}".strip()
            if chunk:
                sentences.append(chunk)

        if not sentences:
            return []

        if len(sentences) == 1:
            has_spaces = " " in cleaned
            target_segments = max(1, int(duration / 5.0)) if duration > 0 else 1
            max_chars = max(20, int(len(cleaned) / target_segments))

            if has_spaces:
                words = cleaned.split(" ")
                segments_text: List[str] = []
                current: List[str] = []
                current_len = 0
                for word in words:
                    add_len = len(word) + (1 if current else 0)
                    if current and current_len + add_len > max_chars:
                        segments_text.append(" ".join(current))
                        current = [word]
                        current_len = len(word)
                    else:
                        current.append(word)
                        current_len += add_len
                if current:
                    segments_text.append(" ".join(current))
                sentences = segments_text
            else:
                segments_text = []
                for start_idx in range(0, len(cleaned), max_chars):
                    segments_text.append(cleaned[start_idx : start_idx + max_chars])
                sentences = segments_text

        if duration <= 0:
            duration = max(5.0, len(sentences) * 3.0)
        slot = duration / max(1, len(sentences))
        segments = []
        for idx, part in enumerate(sentences):
            start_time = idx * slot
            end_time = start_time + slot
            segments.append({"index": idx, "start": start_time, "end": end_time, "text": part})
        return segments


asr_service = ASRService()
