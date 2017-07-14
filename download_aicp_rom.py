#!/bin/env python

import argparse
import hashlib
import os
import sys

import requests
from bs4 import BeautifulSoup


# thanks to:
# https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
def hash_bytestr_iter(bytes_iter, hasher, as_hex_str=False):
    for block in bytes_iter:
        hasher.update(block)
    return hasher.hexdigest() if as_hex_str else hasher.digest()


def file_as_blockiter(file_object, blocksize=65536):
    with file_object:
        block = file_object.read(blocksize)
        while block:
            yield block
            block = file_object.read(blocksize)


def get_aicp_rom_info(device_name):
    aicp_base_url = "http://dwnld.aicp-rom.com"
    query_string = "?device={device}"

    aicp_catalog_url = os.path.join(aicp_base_url,
                                    query_string.format(device=device_name))
    response = requests.get(aicp_catalog_url)
    if response.status_code == 200:
        parsed_catalog = BeautifulSoup(response.content, "html.parser")
    else:
        sys.stderr.write("failed to get ROM catalog from AICP server.\n")
        sys.exit(1)

    download_urls = []
    for link in parsed_catalog.find_all("a"):
        download_url = link.get("href")
        if download_url.split('.')[-1] == "zip":
            download_urls.append(download_url)
    checksums = []
    for checksum in parsed_catalog.find_all("small", {"class": "md5"}):
        md5sum_line = str(checksum.string.encode("ascii", "ignore"))
        md5sum = md5sum_line.split(':')[1].split(' ')[0]
        checksums.append(md5sum)

    return download_urls[0], checksums[0]


def download_aicp_rom(download_url, saved_to_dir):
    file_name = os.path.basename(download_url)
    file_location = os.path.join(saved_to_dir, file_name)
    response = requests.get(download_url, stream=True)

    chunk_size = 16 * (2**10)
    with open(file_location, 'wb') as file_object:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                file_object.write(chunk)
    return file_location


def verify_downloaded_aicp_rom(file_location, checksum):
    with open(file_location, 'rb') as file_object:
        md5sum = hash_bytestr_iter(file_object, hashlib.md5(), as_hex_str=True)
    if checksum != md5sum:
        sys.stderr.write("downloaded ROM seems to be broken\n")
        sys.stderr.write("remove downloaded ROM\n")
        os.remove(file_location)
        return None
    return file_location


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description=("Download latest AICP ROM for given device "
                     "to specified directory"))
    PARSER.add_argument(
        "device_name",
        metavar="<device>",
        type=str,
        help="device name")
    PARSER.add_argument(
        "saved_to_dir",
        metavar="<directory>",
        type=str,
        help="directory where ROM saved")

    ARGS = PARSER.parse_args()
    DEVICE_NAME = ARGS.device_name
    SAVED_TO_DIR = ARGS.saved_to_dir

    DOWNLOAD_URL, CHECKSUM = get_aicp_rom_info(DEVICE_NAME)
    print("URL: {u}".format(u=DOWNLOAD_URL))
    print("checksum: {c}".format(c=CHECKSUM))

    ROM_LOCATION = download_aicp_rom(DOWNLOAD_URL, SAVED_TO_DIR)
    ROM_LOCATION = verify_downloaded_aicp_rom(ROM_LOCATION, CHECKSUM)
    if ROM_LOCATION:
        print("ROM for {d} is downloaded successfully".format(d=DEVICE_NAME))
