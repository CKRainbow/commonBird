import os
import sys
from pathlib import Path

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
