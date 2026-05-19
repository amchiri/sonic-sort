"""Tests du scanner de bibliothèque."""
import tempfile
from pathlib import Path

import pytest

from src.scanner.library_scanner import LibraryScanner, AUDIO_EXTENSIONS


def test_scan_finds_audio_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "track01.mp3").write_bytes(b"fake")
        (root / "track02.flac").write_bytes(b"fake")
        (root / "cover.jpg").write_bytes(b"fake")
        (root / "sub").mkdir()
        (root / "sub" / "track03.m4a").write_bytes(b"fake")

        scanner = LibraryScanner(root)
        files = scanner.scan()

        extensions = {f.extension for f in files}
        assert ".mp3" in extensions
        assert ".flac" in extensions
        assert ".m4a" in extensions
        assert ".jpg" not in extensions
        assert len(files) == 3


def test_scan_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        LibraryScanner("/nonexistent/path/xyz")


def test_audio_extensions_set():
    assert ".mp3" in AUDIO_EXTENSIONS
    assert ".flac" in AUDIO_EXTENSIONS
    assert ".ogg" in AUDIO_EXTENSIONS
    assert ".txt" not in AUDIO_EXTENSIONS
