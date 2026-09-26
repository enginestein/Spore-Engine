"""Thin, leak-free wrappers around the external ``ffmpeg``/``ffprobe`` binaries.

Both are optional. Every entry point raises
:class:`~spore_engine.media.ffmpeg.FFmpegUnavailable` when the binary is
missing, instead of a bare ``FileNotFoundError`` from deep inside
``subprocess``.

The important part of this module is :class:`FFmpegPipe`: a context manager
that guarantees the child process is *killed and reaped* and its stdout closed
on every exit path, including exceptions and early ``break``. Reading raw
frames from a pipe and then returning early (which ``max_frames`` does)
otherwise leaves an orphaned ffmpeg holding the output file open.
"""

from __future__ import annotations

import os
import shutil
import subprocess

__all__ = [
    'FFmpegError',
    'FFmpegPipe',
    'FFmpegUnavailable',
    'have_ffmpeg',
    'have_ffprobe',
    'probe_duration',
    'probe_fps',
    'probe_size',
    'require_ffmpeg',
]


class FFmpegError(RuntimeError):
    """ffmpeg or ffprobe ran but failed."""


class FFmpegUnavailable(FFmpegError):
    """The ffmpeg/ffprobe binary is not installed or not on ``PATH``."""


def have_ffmpeg() -> bool:
    """Whether an ``ffmpeg`` binary is on ``PATH``."""
    return shutil.which('ffmpeg') is not None


def have_ffprobe() -> bool:
    """Whether an ``ffprobe`` binary is on ``PATH``."""
    return shutil.which('ffprobe') is not None


def require_ffmpeg() -> None:
    """Raise :class:`FFmpegUnavailable` unless ffmpeg is installed."""
    if not have_ffmpeg():
        raise FFmpegUnavailable(
            'ffmpeg is required for this operation but was not found on PATH. '
            'Install it, or install pillow to use the pure-Python image path.')


def _run_probe(args: list, what: str) -> str:
    """Run a ffprobe query and return stripped stdout.

    Raises :class:`FFmpegUnavailable` if ffprobe is missing and
    :class:`FFmpegError` if the probe fails - the previous code caught
    ``Exception`` and returned a silent ``(0, 0)``/``30.0``, which then
    divided by zero somewhere much less obvious.
    """
    if not have_ffprobe():
        raise FFmpegUnavailable(
            f'ffprobe is required to read {what} but was not found on PATH')
    try:
        proc = subprocess.run(['ffprobe', '-v', '0', *args],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=30)
    except subprocess.TimeoutExpired:
        raise FFmpegError(f'ffprobe timed out reading {what}') from None
    except OSError as exc:
        raise FFmpegUnavailable(f'could not run ffprobe: {exc}') from None
    if proc.returncode != 0:
        raise FFmpegError(
            f'ffprobe could not read {what} (exit {proc.returncode})')
    return proc.stdout.decode('utf-8', 'replace').strip()


def probe_size(path: str) -> tuple:
    """``(width, height)`` of the first video stream.

    Raises a typed error rather than returning ``(0, 0)``, because every
    caller divides by these."""
    if not os.path.isfile(path):
        raise FFmpegError(f'media file not found: {path}')
    out = _run_probe(['-select_streams', 'v:0', '-show_entries',
                      'stream=width,height', '-of', 'csv=p=0', path],
                     f'the size of {path}')
    parts = out.split(',')
    if len(parts) != 2:
        raise FFmpegError(
            f'{path} has no decodable video stream (got {out!r})')
    try:
        w, h = int(parts[0]), int(parts[1])
    except ValueError:
        raise FFmpegError(f'unreadable dimensions from {path}: {out!r}') from None
    if w <= 0 or h <= 0:
        raise FFmpegError(f'{path} reports a {w}x{h} video stream')
    return (w, h)


def probe_fps(path: str) -> float:
    """Frame rate of the first video stream, or 30.0 if ffprobe cannot say."""
    try:
        out = _run_probe(['-select_streams', 'v:0', '-show_entries',
                          'stream=r_frame_rate', '-of', 'csv=p=0', path],
                         f'the frame rate of {path}')
        parts = out.split('/')
        if len(parts) == 2:
            num, den = float(parts[0]), float(parts[1])
            if den:
                return num / den
    except FFmpegError:
        pass
    return 30.0


def probe_duration(path: str) -> float:
    """Duration in seconds, or 0.0 when unknown (used only for progress)."""
    try:
        out = _run_probe(['-show_entries', 'format=duration',
                          '-of', 'csv=p=0', path], f'the duration of {path}')
        return float(out)
    except (FFmpegError, ValueError):
        return 0.0


class FFmpegPipe:
    """A running ffmpeg writing raw frames to stdout, cleaned up on exit.

    ::

        with FFmpegPipe(['-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
                        ) as pipe:
            while chunk := pipe.read(frame_size):
                ...

    On exit the child is terminated (if still running), waited on so it cannot
    become a zombie, and stdout is closed. A ``KeyError`` or callback exception
    inside the ``with`` body will not leak the process.
    """

    def __init__(self, args: list, binary: str = 'ffmpeg'):
        if shutil.which(binary) is None:
            raise FFmpegUnavailable(
                f'{binary} is required for this operation but was not found '
                'on PATH')
        args = list(args)
        if args and args[0] == binary:
            # Prepending binary to a command that already names it runs
            # `ffmpeg ffmpeg -i ...`: ffmpeg treats the second "ffmpeg" as an
            # input file, exits 1 and writes nothing to stdout, so the caller
            # just sees an empty stream.
            raise ValueError(
                f'{binary} is added automatically; pass only the arguments '
                f'(got {args[0]!r} as the first element)')
        self.args = args
        self.binary = binary
        self._proc: subprocess.Popen | None = None
        self.returncode: int | None = None

    def __enter__(self) -> FFmpegPipe:
        try:
            self._proc = subprocess.Popen(
                [self.binary, *self.args],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise FFmpegUnavailable(
                f'could not run {self.binary}: {exc}') from None
        return self

    def read(self, size: int) -> bytes:
        """Read up to ``size`` bytes. Returns ``b''`` at end of stream."""
        if self._proc is None or self._proc.stdout is None:
            return b''
        return self._proc.stdout.read(size)

    def read_all(self) -> bytes:
        """Read the whole stream to EOF."""
        chunks = []
        while True:
            chunk = self.read(1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b''.join(chunks)

    def terminate(self) -> None:
        """Ask ffmpeg to stop early (used by ``max_frames``)."""
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def __exit__(self, *exc) -> bool:
        proc = self._proc
        if proc is not None:
            if proc.poll() is None:
                self.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # ffmpeg ignored SIGTERM; do not hang the caller.
                    proc.kill()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
            else:
                proc.wait()
            if proc.stdout is not None:
                try:
                    proc.stdout.close()
                except OSError:
                    pass
            self.returncode = proc.returncode
            self._proc = None
        return False
