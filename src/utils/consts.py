from enum import Enum


class BirdreportTaxonVersion(Enum):
    G3 = "G3-22E81200EAAC4C3C8CCC8B6019DF3BF5"
    Z4 = "Z4-67FA07177A544FBD96006A7CC7489D25"


DOWNLOAD_URL = {
    "darwin": "https://gh-proxy.com/github.com/CKRainbow/commonBird/releases/latest/download/commonBird_mac_x64.tar.gz",
    "linux": "https://gh-proxy.com/github.com/CKRainbow/commonBird/releases/latest/download/commonBird_linux_x64.tar.gz",
    "windows": "https://gh-proxy.com/github.com/CKRainbow/commonBird/releases/latest/download/commonBird_win_x64.zip",
}

###### consts added in building process
GITHUB_API_TOKEN = ""
APP_VERSION = "v0.4.1"
