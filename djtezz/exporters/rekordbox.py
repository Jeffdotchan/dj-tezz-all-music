"""Export tracks to Rekordbox XML format."""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from ..catalog import Catalog


def export_to_rekordbox_xml(
    track_hashes: list[str] | None = None,
    output_path: Path | None = None,
    playlist_name: str = "DJ Tezz Export",
) -> Path:
    """Export tracks to Rekordbox XML format.

    Args:
        track_hashes: List of track hashes to export, or None for all
        output_path: Where to save the XML file
        playlist_name: Name of the playlist in Rekordbox

    Returns:
        Path to the exported XML file
    """
    catalog = Catalog()

    if output_path is None:
        output_path = Path(__file__).parent.parent.parent / "rekordbox_export.xml"

    # Get tracks to export
    if track_hashes:
        tracks = [(h, catalog.get_track(h)) for h in track_hashes if catalog.get_track(h)]
    else:
        tracks = list(catalog.data["tracks"].items())

    # Create XML structure
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")

    # Product info
    product = ET.SubElement(root, "PRODUCT",
                           Name="rekordbox",
                           Version="6.0.0",
                           Company="Pioneer DJ")

    # Collection
    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(tracks)))

    track_ids = {}
    for idx, (hash_id, track) in enumerate(tracks, 1):
        tier1 = track.get("tier1", {})

        # File path needs to be file:// URL encoded
        file_path = track.get("file_path", "")
        file_url = "file://localhost" + quote(file_path)

        # Calculate duration in seconds
        duration = track.get("duration_sec", 0)

        # Get BPM and key
        bpm = tier1.get("bpm", 0)
        key = tier1.get("key", "")

        # Map key to Rekordbox key code (simplified)
        key_map = {
            "C major": 1, "A minor": 1,
            "G major": 2, "E minor": 2,
            "D major": 3, "B minor": 3,
            "A major": 4, "F# minor": 4,
            "E major": 5, "C# minor": 5,
            "B major": 6, "G# minor": 6,
            "F# major": 7, "D# minor": 7,
            "Db major": 8, "Bb minor": 8,
            "Ab major": 9, "F minor": 9,
            "Eb major": 10, "C minor": 10,
            "Bb major": 11, "G minor": 11,
            "F major": 12, "D minor": 12,
        }
        tonality = key_map.get(key, 0)

        track_elem = ET.SubElement(collection, "TRACK",
            TrackID=str(idx),
            Name=track.get("title") or track.get("filename") or "Unknown",
            Artist=track.get("artist") or "",
            Album=track.get("album") or "",
            Kind="WAV File" if file_path.endswith(".wav") else "MP3 File",
            Size=str(int((track.get("file_size_mb") or 0) * 1024 * 1024)),
            TotalTime=str(int(duration or 0)),
            AverageBpm=f"{bpm:.2f}" if bpm else "0.00",
            Tonality=str(tonality) if tonality else "",
            Location=file_url,
            DateAdded=datetime.now().strftime("%Y-%m-%d"),
        )

        # Add tempo track for beatgrid
        if bpm:
            tempo = ET.SubElement(track_elem, "TEMPO",
                Inizio="0.000",
                Bpm=f"{bpm:.2f}",
                Metro="4/4",
                Battito="1")

        track_ids[hash_id] = str(idx)

    # Playlists
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")

    playlist_node = ET.SubElement(root_node, "NODE",
        Type="1",
        Name=playlist_name,
        KeyType="0",
        Entries=str(len(tracks)))

    for idx, (hash_id, _) in enumerate(tracks):
        ET.SubElement(playlist_node, "TRACK", Key=track_ids[hash_id])

    # Write XML
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    with open(output_path, "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)

    return output_path


def export_tracks_by_query(
    query: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    output_path: Path | None = None,
    playlist_name: str = "DJ Tezz Export",
) -> Path:
    """Export tracks matching a query to Rekordbox XML.

    Args:
        query: Text search query
        bpm_min: Minimum BPM
        bpm_max: Maximum BPM
        output_path: Where to save the XML
        playlist_name: Name of the playlist

    Returns:
        Path to the exported XML file
    """
    catalog = Catalog()
    results = catalog.search(
        query=query,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
    )

    # Get hashes for matching tracks
    hashes = []
    for track in results:
        for hash_id, t in catalog.data["tracks"].items():
            if t.get("file_path") == track.get("file_path"):
                hashes.append(hash_id)
                break

    return export_to_rekordbox_xml(
        track_hashes=hashes,
        output_path=output_path,
        playlist_name=playlist_name,
    )
