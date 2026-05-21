"""Pipeline principal : scan → lecture → fingerprint → MusicBrainz → normalise → renomme."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src.scanner.library_scanner import LibraryScanner, AudioFile
from src.metadata.reader import MetadataReader, TrackMetadata
from src.fingerprint.acoustid_client import AcoustIDClient
from src.matcher.musicbrainz_client import MusicBrainzClient
from src.normalizer.tag_normalizer import TagNormalizer
from src.renamer.file_renamer import FileRenamer
from src.utils.logger import get_logger, console

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    audio_file: AudioFile
    original_meta: Optional[TrackMetadata] = None
    final_meta: Optional[TrackMetadata] = None
    new_path: Optional[Path] = None
    acoustid_score: float = 0.0
    mb_recording_id: str = ""
    tags_written: bool = False
    file_moved: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class PipelineStats:
    total: int = 0
    identified: int = 0
    tags_updated: int = 0
    files_renamed: int = 0
    errors: int = 0


class SonicSortPipeline:
    def __init__(
        self,
        input_dir: str | Path,
        output_dir: Optional[str | Path] = None,
        dry_run: bool = False,
        use_fingerprint: bool = True,
        min_missing_fields: int = 1,
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir
        self.dry_run = dry_run
        self.use_fingerprint = use_fingerprint
        self.min_missing_fields = min_missing_fields

        self.scanner = LibraryScanner(self.input_dir)
        self.reader = MetadataReader()
        self.acoustid = AcoustIDClient()
        self.mb = MusicBrainzClient()
        self.normalizer = TagNormalizer()
        self.renamer = FileRenamer(self.output_dir)

    def run(self) -> tuple[list[ProcessResult], PipelineStats]:
        files = self.scanner.scan()
        stats = PipelineStats(total=len(files))
        results: list[ProcessResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Traitement des fichiers...", total=len(files))

            for af in files:
                result = self._process_file(af)
                results.append(result)

                if result.success:
                    if result.mb_recording_id:
                        stats.identified += 1
                    if result.tags_written:
                        stats.tags_updated += 1
                    if result.file_moved:
                        stats.files_renamed += 1
                else:
                    stats.errors += 1

                progress.advance(task)

        self._print_summary(stats)
        return results, stats

    def _process_file(self, af: AudioFile) -> ProcessResult:
        result = ProcessResult(audio_file=af)

        # 1. Lecture des tags existants
        meta = self.reader.read(af.path)
        result.original_meta = meta

        # 2. Fingerprint + MusicBrainz si tags insuffisants
        source_meta: dict = {}
        if self.use_fingerprint and len(meta.missing_fields) >= self.min_missing_fields:
            source_meta = self._identify(af, result)

        # 3. Normalisation (fusion tags existants + données MB)
        final_meta = self.normalizer.normalize(meta, source_meta)
        result.final_meta = final_meta

        # 4. Écriture des tags
        if source_meta or len(meta.missing_fields) > 0:
            ok = self.normalizer.write(final_meta, dry_run=self.dry_run)
            result.tags_written = ok

        # 5. Renommage / déplacement
        new_path, moved = self.renamer.rename(final_meta, dry_run=self.dry_run)
        result.new_path = new_path
        result.file_moved = moved

        return result

    def _identify(self, af: AudioFile, result: ProcessResult) -> dict:
        matches = self.acoustid.lookup(af.path)
        if not matches:
            return {}

        best = matches[0]
        result.acoustid_score = best["score"]
        recording_id = best.get("recording_id", "")

        if not recording_id:
            return {}

        result.mb_recording_id = recording_id
        recording = self.mb.get_recording(recording_id)
        if not recording:
            return {}

        return self.mb.extract_metadata(recording)

    def _print_summary(self, stats: PipelineStats) -> None:
        console.rule("[bold blue]Résumé SonicSort[/bold blue]")
        console.print(f"  Fichiers analysés  : [bold]{stats.total}[/bold]")
        console.print(f"  Identifiés (MB)    : [green]{stats.identified}[/green]")
        console.print(f"  Tags mis à jour    : [green]{stats.tags_updated}[/green]")
        console.print(f"  Fichiers renommés  : [green]{stats.files_renamed}[/green]")
        console.print(f"  Erreurs            : [red]{stats.errors}[/red]")
        if self.dry_run:
            console.print("\n[yellow bold]Mode DRY-RUN — aucun fichier modifié[/yellow bold]")
