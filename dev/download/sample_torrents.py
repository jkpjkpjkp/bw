"""
Download sample torrent files and extract filename conventions.

1. Groups torrent URLs by pattern (removing trailing datetime/numeric indices)
2. Downloads 2 torrent files per group using wget
3. Parses torrent files to extract filenames
4. Outputs YAML showing filename conventions per group
"""

import json
import re
import subprocess
from pathlib import Path
from collections import defaultdict
import bencodepy
import yaml


def extract_group_key(url: str) -> str:
    """
    Extract group key from URL by removing trailing datetime/numeric indices.

    Examples:
    - annas_archive_meta__aacid__duxiu_records__20240130T000000Z--20240209T000000Z.jsonl.zst.torrent
      -> annas_archive_meta__aacid__duxiu_records
    - annas_archive_data__aacid__duxiu_files__20240613T170516Z--20240613T170517Z.torrent
      -> annas_archive_data__aacid__duxiu_files
    """
    # Extract filename from URL
    filename = url.split("/")[-1]

    # Remove extension(s)
    # Handle .jsonl.zst.torrent, .jsonl.seekable.zst.torrent, .torrent
    name = re.sub(r"\.jsonl(\.seekable)?\.zst\.torrent$", "", filename)
    name = re.sub(r"\.torrent$", "", name)

    # Remove trailing datetime patterns like __20240130T000000Z--20240209T000000Z
    # or __20240613T170516Z--20240613T170517Z
    name = re.sub(r"__\d{8}T\d{6}Z--\d{8}T\d{6}Z$", "", name)

    return name


def group_urls(data: list[dict]) -> dict[str, list[dict]]:
    """Group torrent entries by their URL pattern."""
    groups = defaultdict(list)
    for entry in data:
        key = extract_group_key(entry["url"])
        groups[key].append(entry)
    return dict(groups)


def download_torrents(groups: dict[str, list[dict]], output_dir: Path, count_per_group: int = 2) -> dict[str, list[Path]]:
    """Download torrent files using wget, returning paths to downloaded files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = {}

    for group_key, entries in groups.items():
        downloaded[group_key] = []
        # Take first `count_per_group` entries
        for entry in entries[:count_per_group]:
            url = entry["url"]
            filename = url.split("/")[-1]
            output_path = output_dir / filename

            if output_path.exists():
                print(f"Already exists: {filename}")
                downloaded[group_key].append(output_path)
                continue

            print(f"Downloading: {filename}")
            result = subprocess.run(
                ["wget", "-q", "-O", str(output_path), url],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                downloaded[group_key].append(output_path)
            else:
                print(f"  Failed: {result.stderr}")

    return downloaded


def parse_torrent(torrent_path: Path) -> list[str]:
    """Parse a torrent file and extract filenames."""
    with open(torrent_path, "rb") as f:
        torrent_data = bencodepy.decode(f.read())

    info = torrent_data[b"info"]
    filenames = []

    if b"files" in info:
        # Multi-file torrent
        for file_entry in info[b"files"]:
            path_parts = [p.decode("utf-8", errors="replace") for p in file_entry[b"path"]]
            filenames.append("/".join(path_parts))
    else:
        # Single-file torrent
        filenames.append(info[b"name"].decode("utf-8", errors="replace"))

    return filenames


def sample_filenames(filenames: list[str], count: int = 5) -> list[str]:
    """Sample some filenames to show convention."""
    if len(filenames) <= count:
        return filenames
    # Take first, middle, and last samples
    indices = [0, len(filenames) // 4, len(filenames) // 2, 3 * len(filenames) // 4, len(filenames) - 1]
    return [filenames[i] for i in indices[:count]]


def main():
    base_dir = Path(__file__).parent
    data_file = base_dir / ".anna.json"
    torrents_dir = base_dir / "torrents"
    output_file = base_dir / "filename_conventions.yaml"

    # Load data
    print("Loading torrent metadata...")
    with open(data_file) as f:
        data = json.load(f)

    # Group URLs
    print("Grouping URLs by pattern...")
    groups = group_urls(data)
    print(f"Found {len(groups)} groups:")
    for key, entries in groups.items():
        print(f"  {key}: {len(entries)} entries")

    # Download torrents
    print("\nDownloading sample torrents (2 per group)...")
    downloaded = download_torrents(groups, torrents_dir, count_per_group=2)

    # Parse and extract filename conventions
    print("\nExtracting filename conventions...")
    conventions = {}

    for group_key, torrent_paths in downloaded.items():
        conventions[group_key] = {
            "torrents_sampled": [],
            "filename_samples": [],
            "total_files_in_samples": 0,
        }

        for torrent_path in torrent_paths:
            if not torrent_path.exists():
                continue
            try:
                filenames = parse_torrent(torrent_path)
                conventions[group_key]["torrents_sampled"].append(torrent_path.name)
                conventions[group_key]["filename_samples"].extend(sample_filenames(filenames))
                conventions[group_key]["total_files_in_samples"] += len(filenames)
            except Exception as e:
                print(f"  Error parsing {torrent_path.name}: {e}")

    # Write YAML output
    print(f"\nWriting conventions to {output_file}...")
    with open(output_file, "w") as f:
        yaml.dump(conventions, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print("Done!")

    # Print summary
    print("\n=== Summary ===")
    for group_key, conv in conventions.items():
        print(f"\n{group_key}:")
        print(f"  Torrents: {conv['torrents_sampled']}")
        print(f"  Total files: {conv['total_files_in_samples']}")
        print(f"  Sample filenames:")
        for fn in conv["filename_samples"][:3]:
            print(f"    - {fn}")


if __name__ == "__main__":
    main()
