# What's this?
This is maybe useful when you download ROM for your device(s) from [AICP Downloads](http://dwnld.aicp-rom.com/).

# Usage
```
$ python download-aicp-rom.py -h
usage: download-aicp-rom.py [-h] [--device-name DEVICE_NAME]
                            [--saved-to-dir SAVED_TO_DIR] [--conf CONFIG]

Download latest AICP ROM for given device to specified directory

optional arguments:
  -h, --help            show this help message and exit
  --device-name DEVICE_NAME
                        device name (required when --config is not specified)
  --saved-to-dir SAVED_TO_DIR
                        directory where ROM saved (required when --config is
                        not specified)
  --conf CONFIG         location of config file required when --device-name
                        and --saved-to-dir are not specified
```

# Dependencies
- beautifulsoup4
- requests
