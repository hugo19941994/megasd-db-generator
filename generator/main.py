#!/usr/bin/env python3

import argparse
import logging
import sys
from datDownloader import downloadDATs
from IGDBDownloader import IGDBDownloader
from XMLBuilder import XMLGenerator


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info('MegaSD DB Generator')

    parser = argparse.ArgumentParser()

    parser.add_argument("--download-dats", action="store_true", help="Download No-Intro DATs")
    parser.add_argument("--download-db", action="store_true", help="Download and generate the IGDB DB")
    parser.add_argument("--generate-xml", action="store_true", help="Generate the db.xml file")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()

    if args.download_dats:
        downloadDATs()

    if args.download_db:
        IGDBDownloader()

    if args.generate_xml:
        XMLGenerator()


if __name__ == "__main__":
    main()
