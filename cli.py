import logging

from dotenv import load_dotenv

from src import application_path, env_path
from src.cli.app import CommonBirdApp

logging.basicConfig(
    filename=application_path / "log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if not env_path.exists():
    open(env_path, "a").close()
load_dotenv(env_path)


def main():
    app = CommonBirdApp()
    app.run()


if __name__ == "__main__":
    main()
