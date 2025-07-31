#!/usr/bin/env python3

import argparse
import logging
import sys

from generator.dat_downloader import download_dats
from generator.igdb_downloader import IGDBDownloader
from generator.redump_filler import check_missing
from generator.xml_builder import XMLGenerator


def main():
    log_format = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)

    logging.info("MegaSD DB Generator\n")

    parser = argparse.ArgumentParser()

    parser.add_argument("--download-dats", action="store_true", help="Download No-Intro DATs")
    parser.add_argument("--download-db", action="store_true", help="Download and generate the IGDB DB")
    parser.add_argument("--generate-xml", action="store_true", help="Generate the db.xml file")
    parser.add_argument("--update-custom-dat", nargs=1, required=False, help="Update the custom Sega CD DAT")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()

    if args.download_dats:
        download_dats()

    if args.update_custom_dat:
        print(args.update_custom_dat)
        check_missing(args.update_custom_dat[0])

    if args.download_db:
        IGDBDownloader()

    if args.generate_xml:
        XMLGenerator()


if __name__ == "__main__":
    main()
