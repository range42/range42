import logging

from .config import Config
from .preparator import Preparator


def main():
    config = Config()
    logging.debug(f"Variables configured:\n\t{config}")
    preparator = Preparator(config)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    main()
