import os
import sys
from pathlib import Path
from typing import List

from selenium.webdriver.common.driver_finder import DriverFinder

selenium_ori_deiver_finder_to_arg = DriverFinder._to_args

def selenium_ori_deiver_finder_to_arg_patch(self):
    args: List = selenium_ori_deiver_finder_to_arg(self)
    args.append("--timeout")
    args.append("20")
    return args

DriverFinder._to_args = selenium_ori_deiver_finder_to_arg_patch

if getattr(sys, "frozen", False):
    inner_path = Path(sys._MEIPASS)
    application_path = Path(os.path.dirname(sys.executable))
elif __file__:
    inner_path = Path(os.getcwd())
    application_path = Path(inner_path)

database_path = application_path / "database"
env_path = application_path / ".env"
cache_path = application_path / ".cache"
output_path = application_path / "output"

public_key_file = inner_path / "public_key.pem"

if not database_path.exists():
    database_path.mkdir()
if not cache_path.exists():
    cache_path.mkdir()
