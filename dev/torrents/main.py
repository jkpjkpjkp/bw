import subprocess
import json
import os
from pathlib import Path

def download_and_parse_torrents(json_file, limit=None):
    """
    Download torrents from .anna.json and show their file contents

    Args:
        json_file: Path to the .anna.json file
        limit: Optional limit on number of torrents to process
    """
    # Read the JSON file
    with open(json_file, 'r') as f:
        torrents = json.load(f)

    # Limit if specified
    if limit:
        torrents = torrents[:limit]

    # Create a temp directory for downloads
    download_dir = Path('temp_torrents')
    download_dir.mkdir(exist_ok=True)

    for idx, torrent_data in enumerate(torrents, 1):
        url = torrent_data['url']
        display_name = torrent_data['display_name']

        print(f"\n{'='*80}")
        print(f"[{idx}/{len(torrents)}] {display_name}")
        print(f"{'='*80}")

        # Download the torrent file
        torrent_file = download_dir / display_name

        try:
            # Use wget to download
            subprocess.run(
                ['wget', '-q', '-O', str(torrent_file), url],
                check=True
            )

            # Parse the torrent file using parse.js
            result = subprocess.run(
                ['node', 'parse.js', str(torrent_file)],
                capture_output=True,
                text=True,
                check=True
            )

            print(result.stdout)

            # Clean up the downloaded file
            torrent_file.unlink()

        except subprocess.CalledProcessError as e:
            print(f"Error processing {display_name}: {e}")
            if torrent_file.exists():
                torrent_file.unlink()
            continue

    # Clean up temp directory
    download_dir.rmdir()

if __name__ == '__main__':
    import sys

    # Get arguments
    json_file = sys.argv[1] if len(sys.argv) > 1 else '../download/.anna.json'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Processing torrents from: {json_file}")
    print(f"Limit: {limit}")

    download_and_parse_torrents(json_file, limit)
