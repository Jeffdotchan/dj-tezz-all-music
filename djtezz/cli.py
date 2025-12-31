"""CLI entry point for DJ Tezz Music Analyzer."""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from . import __version__
from .catalog import Catalog
from .config import DEFAULT_MUSIC_PATH, QWEN_API_BASE, QWEN_MODEL_NAME
from .utils.audio import scan_directory, get_audio_metadata
from .utils.hash import hash_file_quick

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """DJ Tezz Music Analyzer - EDM analysis and DJ workflow tools."""
    pass


@main.command()
@click.option("--tier1", is_flag=True, help="Run Essentia analysis (BPM, key, energy)")
@click.option("--tier2", is_flag=True, help="Run Whisper analysis (vocals, lyrics)")
@click.option("--tier3", is_flag=True, help="Run Qwen2-Audio analysis (rich descriptions)")
@click.option("--all", "all_tiers", is_flag=True, help="Run all analysis tiers")
@click.option("--path", type=click.Path(exists=True, path_type=Path), default=None,
              help="Path to music folder (default: current directory)")
@click.option("--force", is_flag=True, help="Re-analyze tracks even if already analyzed")
@click.option("--new-only", is_flag=True, help="Only analyze tracks not in catalog")
@click.option("--gpu-id", type=int, default=0, help="GPU device ID (default: 0)")
def analyze(tier1: bool, tier2: bool, tier3: bool, all_tiers: bool,
            path: Path | None, force: bool, new_only: bool, gpu_id: int):
    """Analyze music files with selected tiers."""

    # Determine which tiers to run
    if all_tiers:
        tier1 = tier2 = tier3 = True
    elif not any([tier1, tier2, tier3]):
        # Default to tier1 if nothing specified
        tier1 = True
        console.print("[yellow]No tier specified, defaulting to --tier1[/yellow]")

    music_path = path or DEFAULT_MUSIC_PATH
    catalog = Catalog()

    # Scan for audio files
    console.print(f"\n[bold]Scanning[/bold] {music_path}")
    audio_files = scan_directory(music_path)
    console.print(f"Found [bold]{len(audio_files)}[/bold] audio files\n")

    if not audio_files:
        console.print("[yellow]No audio files found.[/yellow]")
        return

    # Filter based on options
    files_to_analyze = []
    for file_path in audio_files:
        file_hash = hash_file_quick(file_path)
        track = catalog.get_track(file_hash)

        if new_only and track is not None:
            continue

        if not force and track is not None:
            # Check which tiers need running
            needs_analysis = False
            if tier1 and not catalog.has_tier(file_hash, "tier1"):
                needs_analysis = True
            if tier2 and not catalog.has_tier(file_hash, "tier2"):
                needs_analysis = True
            if tier3 and not catalog.has_tier(file_hash, "tier3"):
                needs_analysis = True

            if not needs_analysis:
                continue

        files_to_analyze.append((file_path, file_hash))

    console.print(f"[bold]{len(files_to_analyze)}[/bold] files to analyze\n")

    if not files_to_analyze:
        console.print("[green]All files already analyzed![/green]")
        return

    # Run analysis tiers
    tiers_to_run = []
    if tier1:
        tiers_to_run.append(("tier1", "Essentia", _run_tier1))
    if tier2:
        tiers_to_run.append(("tier2", "Whisper", _run_tier2))
    if tier3:
        tiers_to_run.append(("tier3", "Qwen2-Audio", _run_tier3))

    for tier_name, tier_label, tier_func in tiers_to_run:
        console.print(f"\n[bold blue]═══ {tier_label} Analysis ({tier_name}) ═══[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]{tier_label}...", total=len(files_to_analyze))

            for file_path, file_hash in files_to_analyze:
                progress.update(task, description=f"[cyan]{file_path.name[:40]}...")

                try:
                    # Ensure track exists in catalog
                    track = catalog.get_track(file_hash)
                    if track is None:
                        metadata = get_audio_metadata(file_path)
                        track = {
                            "file_path": str(file_path),
                            "filename": file_path.name,
                            **metadata,
                        }
                        catalog.set_track(file_hash, track)

                    # Skip if already analyzed and not forcing
                    if not force and catalog.has_tier(file_hash, tier_name):
                        progress.advance(task)
                        continue

                    # Run analysis
                    result = tier_func(file_path, gpu_id)
                    catalog.update_tier(file_hash, tier_name, result)
                    catalog.save()

                except Exception as e:
                    console.print(f"[red]Error analyzing {file_path.name}: {e}[/red]")

                progress.advance(task)

    # Print summary
    console.print("\n[bold green]Analysis complete![/bold green]")
    _print_stats(catalog)


def _run_tier1(file_path: Path, gpu_id: int) -> dict:
    """Run Tier 1 (Essentia) analysis."""
    from .analyzers.tier1_essentia import EssentiaAnalyzer

    with EssentiaAnalyzer(gpu_id=gpu_id) as analyzer:
        return analyzer.analyze(file_path)


def _run_tier2(file_path: Path, gpu_id: int) -> dict:
    """Run Tier 2 (Whisper) analysis."""
    from .analyzers.tier2_whisper import WhisperAnalyzer

    with WhisperAnalyzer(gpu_id=gpu_id) as analyzer:
        return analyzer.analyze(file_path)


def _run_tier3(file_path: Path, gpu_id: int) -> dict:
    """Run Tier 3 (Qwen2-Audio) analysis via local API."""
    from .analyzers.tier3_qwen import QwenAudioAnalyzer

    with QwenAudioAnalyzer(
        api_base=QWEN_API_BASE,
        model_name=QWEN_MODEL_NAME,
    ) as analyzer:
        return analyzer.analyze(file_path)


@main.command()
@click.argument("query", required=False)
@click.option("--bpm", help="BPM range (e.g., '120-128')")
@click.option("--key", help="Musical keys, comma-separated (e.g., 'Am,Cm')")
@click.option("--energy", help="Energy range 0-1 (e.g., '0.7-1.0')")
@click.option("--genre", help="Genre to filter by")
@click.option("--vocals/--no-vocals", default=None, help="Filter by vocal tracks")
@click.option("--limit", type=int, default=20, help="Max results to show")
def search(query: str | None, bpm: str | None, key: str | None,
           energy: str | None, genre: str | None, vocals: bool | None, limit: int):
    """Search and filter tracks."""

    catalog = Catalog()

    # Parse BPM range
    bpm_min, bpm_max = None, None
    if bpm:
        if "-" in bpm:
            bpm_min, bpm_max = map(float, bpm.split("-"))
        else:
            bpm_min = bpm_max = float(bpm)

    # Parse key list
    keys = None
    if key:
        keys = [k.strip() for k in key.split(",")]

    # Parse energy range
    energy_min, energy_max = None, None
    if energy:
        if "-" in energy:
            energy_min, energy_max = map(float, energy.split("-"))
        else:
            energy_min = energy_max = float(energy)

    # Search
    results = catalog.search(
        query=query,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        keys=keys,
        energy_min=energy_min,
        energy_max=energy_max,
        genre=genre,
        has_vocals=vocals,
    )

    if not results:
        console.print("[yellow]No tracks found matching criteria.[/yellow]")
        return

    console.print(f"\n[bold]Found {len(results)} tracks[/bold]\n")

    # Display results
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", max_width=35)
    table.add_column("Artist", style="dim", max_width=20)
    table.add_column("BPM", justify="right")
    table.add_column("Key", justify="center")
    table.add_column("Energy", justify="right")
    table.add_column("Genre", max_width=15)

    for track in results[:limit]:
        tier1 = track.get("tier1", {})
        tier3 = track.get("tier3", {})

        table.add_row(
            track.get("title", track.get("filename", "Unknown")),
            track.get("artist", "-"),
            str(tier1.get("bpm", "-")),
            tier1.get("key_camelot", tier1.get("key", "-")),
            f"{tier1.get('energy', 0):.2f}" if tier1.get("energy") else "-",
            tier3.get("subgenre") or tier1.get("genre", "-"),
        )

    console.print(table)

    if len(results) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(results)} results. Use --limit to see more.[/dim]")


@main.command()
@click.argument("track_id")
def show(track_id: str):
    """Show detailed info for a track."""

    catalog = Catalog()
    track = catalog.get_track(track_id)

    if not track:
        # Try to find by filename
        for t in catalog.get_all_tracks():
            if track_id.lower() in t.get("filename", "").lower():
                track = t
                break

    if not track:
        console.print(f"[red]Track not found: {track_id}[/red]")
        return

    console.print(f"\n[bold]{track.get('title', track.get('filename'))}[/bold]")
    console.print(f"[dim]by {track.get('artist', 'Unknown')}[/dim]\n")

    # Tier 1 info
    tier1 = track.get("tier1", {})
    if tier1:
        console.print("[bold cyan]── Audio Analysis ──[/bold cyan]")
        console.print(f"  BPM: {tier1.get('bpm', '-')}")
        console.print(f"  Key: {tier1.get('key', '-')} ({tier1.get('key_camelot', '-')})")
        console.print(f"  Energy: {tier1.get('energy', '-')}")
        console.print(f"  Danceability: {tier1.get('danceability', '-')}")
        console.print()

    # Tier 2 info
    tier2 = track.get("tier2", {})
    if tier2:
        console.print("[bold cyan]── Vocals ──[/bold cyan]")
        console.print(f"  Has vocals: {'Yes' if tier2.get('has_vocals') else 'No'}")
        if tier2.get("lyrics"):
            console.print(f"  Lyrics: {tier2.get('lyrics', '')[:200]}...")
        console.print()

    # Tier 3 info
    tier3 = track.get("tier3", {})
    if tier3:
        console.print("[bold cyan]── Vibe Analysis ──[/bold cyan]")
        console.print(f"  Subgenre: {tier3.get('subgenre', '-')}")
        console.print(f"  Mood: {', '.join(tier3.get('mood', []))}")
        console.print(f"  Energy: {tier3.get('energy_description', '-')}")
        console.print(f"  Setting: {tier3.get('best_setting', '-')}")
        console.print(f"  Similar to: {', '.join(tier3.get('similar_artists', []))}")
        if tier3.get("vibe_description"):
            console.print(f"\n  [italic]{tier3.get('vibe_description')}[/italic]")


@main.command()
@click.argument("track_id")
@click.option("--bpm-tolerance", type=float, default=3.0, help="BPM tolerance for matching")
@click.option("--no-harmonic", is_flag=True, help="Skip harmonic key matching")
def compatible(track_id: str, bpm_tolerance: float, no_harmonic: bool):
    """Find tracks compatible for mixing with a given track."""

    catalog = Catalog()

    # Find the source track
    source = None
    for hash_id, track in catalog.data["tracks"].items():
        if track_id.lower() in track.get("filename", "").lower():
            source = (hash_id, track)
            break

    if not source:
        console.print(f"[red]Track not found: {track_id}[/red]")
        return

    hash_id, track = source
    tier1 = track.get("tier1", {})

    console.print(f"\n[bold]Finding tracks compatible with:[/bold]")
    console.print(f"  {track.get('title', track.get('filename'))}")
    console.print(f"  BPM: {tier1.get('bpm')} | Key: {tier1.get('key_camelot')}\n")

    results = catalog.find_compatible(
        hash_id,
        bpm_tolerance=bpm_tolerance,
        harmonic=not no_harmonic,
    )

    if not results:
        console.print("[yellow]No compatible tracks found.[/yellow]")
        return

    console.print(f"[bold green]Found {len(results)} compatible tracks:[/bold green]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", max_width=35)
    table.add_column("BPM", justify="right")
    table.add_column("Key", justify="center")

    for match in results[:20]:
        match_tier1 = match.get("tier1", {})
        table.add_row(
            match.get("title", match.get("filename", "Unknown")),
            str(match_tier1.get("bpm", "-")),
            match_tier1.get("key_camelot", "-"),
        )

    console.print(table)


@main.command()
def stats():
    """Show catalog statistics."""
    catalog = Catalog()
    _print_stats(catalog)


def _print_stats(catalog: Catalog):
    """Print catalog statistics."""
    s = catalog.stats()

    console.print("\n[bold]Catalog Statistics[/bold]")
    console.print(f"  Total tracks: {s['total_tracks']}")
    console.print(f"  Tier 1 (Essentia): {s['tier1_analyzed']}")
    console.print(f"  Tier 2 (Whisper): {s['tier2_analyzed']}")
    console.print(f"  Tier 3 (Qwen2-Audio): {s['tier3_analyzed']}")


if __name__ == "__main__":
    main()
