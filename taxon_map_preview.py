import argparse
from pathlib import Path

from src import database_path
from src.utils.taxon import preview_taxon_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--map_file", type=str, default="taxon_map.json")
    parser.add_argument("--output_path", type=str, default="taxon_map_example.html")

    args = parser.parse_args()

    map_file = database_path / args.map_file
    output_path = Path(args.output_path)

    preview_taxon_map(map_file, output_path)
