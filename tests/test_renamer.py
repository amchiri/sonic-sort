"""Tests pour la logique de renommage des fichiers."""
from pathlib import Path
from unittest.mock import MagicMock

from src.renamer.file_renamer import build_target_path, sanitize
from src.metadata.reader import TrackMetadata


def make_meta(**kwargs) -> TrackMetadata:
    defaults = dict(
        path=Path("/music/test.mp3"),
        title="My Song",
        artist="The Artist",
        album_artist="The Artist",
        album="Great Album",
        year="2023",
        track_number=3,
        disc_number=1,
    )
    defaults.update(kwargs)
    m = MagicMock(spec=TrackMetadata)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def test_build_target_path_standard():
    meta = make_meta()
    root = Path("/output")
    target = build_target_path(meta, root)
    assert target == Path("/output/The Artist/Great Album (2023)/03 - My Song.mp3")


def test_build_target_path_disc_2():
    meta = make_meta(disc_number=2, track_number=1)
    root = Path("/output")
    target = build_target_path(meta, root)
    assert "2-01" in target.name


def test_build_target_path_no_year():
    meta = make_meta(year="")
    root = Path("/output")
    target = build_target_path(meta, root)
    assert "()" not in str(target)
    assert "Great Album" in str(target)


def test_sanitize_illegal_chars():
    assert sanitize('AC/DC: Back in Black?') == "AC_DC_ Back in Black_"


def test_sanitize_trailing_dot():
    result = sanitize("album.")
    assert not result.endswith(".")
