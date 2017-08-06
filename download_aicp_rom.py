#!/bin/env python

"""Get AICP ROM more simply"""

import argparse
import configparser
import errno
import hashlib
import os
import sys
from logging import getLogger, StreamHandler
from logging import INFO

import requests
from bs4 import BeautifulSoup


class DownloadAICPRom(object):
    """Download AICP ROM for specified device(s)"""

    def __init__(self, device_name=None, saved_to_dir=None, conf_name=None,
                 remove=False):
        """Constructor: set device_name and saved_to_dir if given.
        If conf_name given, read config and set device(s) and saved_to_dir."""
        if device_name and saved_to_dir:
            self.device = device_name
            self.saved_to_dir = saved_to_dir
        elif conf_name:
            conf = configparser.ConfigParser(allow_no_value=True)
            conf.read(conf_name)
            # get device name
            section = "device"
            self.device = conf.get(section, "device_name").split(',')
            # get saved_to_dir
            section = "location"
            self.saved_to_dir = conf.get(section, "saved_to_dir")
        if remove:
            self.remove = remove
        else:
            self.remove = False

        # set logger
        self.logger = getLogger(__name__)
        handler = StreamHandler()
        handler.setLevel(INFO)
        self.logger.setLevel(INFO)
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def do_task(self, logger=None):
        """Download AICP ROM"""
        if self.remove:
            self.remove_old_rom()

        try:
            if isinstance(self.device, str):
                self.do_download_aicp_rom(self.device, logger=self.logger)
            elif isinstance(self.device, list):
                for device in self.device:
                    self.do_download_aicp_rom(device, logger=self.logger)
        except KeyboardInterrupt:
            logger.info("Interrupted. Clean files in saved_to_dir")
            self.remove_old_rom()

    def do_download_aicp_rom(self, device, logger=None):
        """Download AICP ROM for given device"""
        try:
            download_url, checksum = self.get_aicp_rom_info(device)
        except IndexError:
            message = "ROM for device {d} seems not to be provided on AICP."
            logger.error(message.format(d=device))
            return

        logger.info("URL: {u}".format(u=download_url))
        logger.info("checksum: {c}".format(c=checksum))
        rom_location = self.download_aicp_rom(download_url,
                                              self.saved_to_dir)
        rom_location = self.verify_downloaded_aicp_rom(rom_location,
                                                       checksum)
        if rom_location:
            message = "ROM for device {d} downloaded successfully"
            logger.info(message.format(d=device))

    # thanks for below 2 method to:
    # https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    @staticmethod
    def hash_bytestr_iter(bytes_iter, hasher, as_hex_str=False):
        """Return digest for given bytes object iterator bytes_iter
        using given hasher.
        If as_hex_str set, return hexadecimal string instead of
        default plain string."""
        for block in bytes_iter:
            hasher.update(block)
        return hasher.hexdigest() if as_hex_str else hasher.digest()

    @staticmethod
    def file_as_blockiter(file_object, blocksize=65536):
        """Convert given file_object (file object, as you see) as iterator"""
        with file_object:
            block = file_object.read(blocksize)
            while block:
                yield block
                block = file_object.read(blocksize)

    @staticmethod
    def get_aicp_rom_info(device_name):
        """Download AICP ROM list for given device_name, then return
        'lastest' ROM info, which are URL and checksum"""
        aicp_base_url = "http://dwnld.aicp-rom.com"
        query_string = "?device={device}"

        aicp_catalog_url = os.path.join(
            aicp_base_url,
            query_string.format(device=device_name))
        response = requests.get(aicp_catalog_url)
        if response.status_code == 200:
            parsed_catalog = BeautifulSoup(response.content, "html.parser")
        else:
            sys.stderr.write("failed to get ROM catalog from AICP server.\n")
            sys.exit(errno.EREMOTEIO)

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

    @staticmethod
    def download_aicp_rom(download_url, saved_to_dir):
        """Download ROM file from given download_url and
        store to saved_to_dir"""
        file_name = os.path.basename(download_url)
        file_location = os.path.join(saved_to_dir, file_name)
        response = requests.get(download_url, stream=True)

        chunk_size = 16 * (2**10)
        with open(file_location, 'wb') as file_object:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file_object.write(chunk)
        return file_location

    def verify_downloaded_aicp_rom(self, file_location, checksum):
        """Generate checksum for file in file_location and compare it with
        given checksum.
        If both matches, return file_location. Otherwise return None."""
        with open(file_location, 'rb') as file_object:
            md5sum = self.hash_bytestr_iter(file_object,
                                            hashlib.md5(),
                                            as_hex_str=True)
        if checksum != md5sum:
            sys.stderr.write("downloaded ROM seems to be broken\n")
            sys.stderr.write("remove downloaded ROM\n")
            os.remove(file_location)
            return None
        return file_location

    def remove_old_rom(self):
        """Remove existed ROM(s) in self.saved_to_dir"""
        for file_name in os.listdir(self.saved_to_dir):
            old_rom = os.path.join(self.saved_to_dir, file_name)
            os.remove(old_rom)
            sys.stdout.write("{r} is removed\n".format(r=old_rom))


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description=("Download latest AICP ROM for given device "
                     "to specified directory"))
    PARSER.add_argument(
        "--device-name",
        dest="device_name",
        type=str,
        help=("device name "
              "(required when --config is not specified)"))
    PARSER.add_argument(
        "--saved-to-dir",
        dest="saved_to_dir",
        type=str,
        help=("directory where ROM saved "
              "(required when --config is not specified)"))
    PARSER.add_argument(
        "--conf",
        dest="config",
        type=str,
        help=("location of config file "
              "(required when --device-name and --saved-to-dir "
              "are not specified)"))
    PARSER.add_argument(
        "--remove-old-rom",
        dest="remove_old_rom",
        action="store_true",
        help=("if specified, remove all of ROM(s) in saved-to directory"))

    ARGS = PARSER.parse_args()
    REMOVE_OLD_ROM = ARGS.remove_old_rom
    if ARGS.device_name and ARGS.saved_to_dir:
        DEVICE_NAME = ARGS.device_name
        SAVED_TO_DIR = ARGS.saved_to_dir
        WORKER = DownloadAICPRom(device_name=DEVICE_NAME,
                                 saved_to_dir=SAVED_TO_DIR,
                                 remove=REMOVE_OLD_ROM)
    elif ARGS.config:
        CONF = ARGS.config
        WORKER = DownloadAICPRom(conf_name=CONF,
                                 remove=REMOVE_OLD_ROM)
    else:
        sys.stderr.write(("Invalid or missing arguments. "
                          "Check help of this script\n"))
        sys.exit(errno.EINVAL)
    WORKER.do_task(WORKER.logger)
