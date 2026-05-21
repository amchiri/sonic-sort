"""Interface CLI SonicSort via Click + Rich."""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.table import Table

from src.pipeline import SonicSortPipeline
from src.plex.plex_trigger import PlexTrigger
from src.utils.logger import console


@click.group()
@click.version_option("1.0.0", prog_name="sonic-sort")
def main():
    """SonicSort — Optimiseur de bibliothèque musicale pour Plex Media Server."""
    pass


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--output", "-o", default=None, help="Dossier de sortie (défaut: même que l'entrée)")
@click.option("--dry-run", is_flag=True, help="Prévisualise les changements sans modifier les fichiers")
@click.option("--no-fingerprint", is_flag=True, help="Désactive AcoustID (plus rapide, moins précis)")
@click.option("--min-missing", default=1, show_default=True, help="Nombre minimum de champs manquants pour déclencher le fingerprint")
@click.option("--plex-scan", is_flag=True, help="Déclenche un scan Plex après traitement")
@click.option("--plex-section", default=1, show_default=True, help="ID de section Plex à scanner")
@click.option("--report", default=None, help="Exporte un rapport JSON vers ce fichier")
def run(input_dir, output, dry_run, no_fingerprint, min_missing, plex_scan, plex_section, report):
    """Analyse et corrige la bibliothèque musicale pour Plex."""

    if dry_run:
        console.print("[yellow bold]Mode DRY-RUN activé — aucun fichier ne sera modifié[/yellow bold]\n")

    pipeline = SonicSortPipeline(
        input_dir=input_dir,
        output_dir=output,
        dry_run=dry_run,
        use_fingerprint=not no_fingerprint,
        min_missing_fields=min_missing,
    )

    results, stats = pipeline.run()

    if report:
        _export_report(results, Path(report))
        console.print(f"\nRapport exporté : [cyan]{report}[/cyan]")

    if plex_scan and not dry_run:
        PlexTrigger().trigger_scan(section_id=plex_section)


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
def scan(input_dir):
    """Scanne la bibliothèque et affiche un rapport des métadonnées manquantes."""
    from src.scanner.library_scanner import LibraryScanner
    from src.metadata.reader import MetadataReader

    scanner = LibraryScanner(input_dir)
    reader = MetadataReader()
    files = scanner.scan()

    table = Table(title="Rapport de la bibliothèque", show_lines=True)
    table.add_column("Fichier", style="cyan", max_width=40)
    table.add_column("Artiste")
    table.add_column("Album")
    table.add_column("Titre")
    table.add_column("Champs manquants", style="red")

    incomplete = 0
    for af in files:
        meta = reader.read(af.path)
        missing = ", ".join(meta.missing_fields)
        if missing:
            incomplete += 1
        table.add_row(
            af.path.name,
            meta.artist or "[red]—[/red]",
            meta.album or "[red]—[/red]",
            meta.title or "[red]—[/red]",
            missing or "[green]✓[/green]",
        )

    console.print(table)
    console.print(
        f"\n[bold]{incomplete}[/bold] / {len(files)} fichiers avec des métadonnées incomplètes"
    )


@main.command()
def plex_sections():
    """Liste les sections Plex disponibles (nécessite PLEX_URL et PLEX_TOKEN)."""
    sections = PlexTrigger().list_sections()
    if not sections:
        console.print("[red]Aucune section trouvée ou Plex non configuré[/red]")
        return
    for s in sections:
        console.print(f"  [{s.get('key')}] {s.get('title')} — {s.get('type')}")


def _export_report(results, path: Path) -> None:
    data = []
    for r in results:
        data.append(
            {
                "file": str(r.audio_file.path),
                "original": _meta_to_dict(r.original_meta),
                "final": _meta_to_dict(r.final_meta),
                "acoustid_score": r.acoustid_score,
                "mb_recording_id": r.mb_recording_id,
                "tags_written": r.tags_written,
                "file_moved": r.file_moved,
                "new_path": str(r.new_path) if r.new_path else None,
                "errors": r.errors,
            }
        )
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _meta_to_dict(meta) -> dict:
    if meta is None:
        return {}
    return {
        "title": meta.title,
        "artist": meta.artist,
        "album_artist": meta.album_artist,
        "album": meta.album,
        "year": meta.year,
        "track_number": meta.track_number,
        "disc_number": meta.disc_number,
        "genre": meta.genre,
        "has_cover": meta.has_cover,
    }


if __name__ == "__main__":
    main()
