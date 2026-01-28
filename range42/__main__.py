import logging
import warnings

from urllib3.exceptions import InsecureRequestWarning

from .config import Config
from .preparator import Preparator


def main():
    config = Config.from_env()
    logging.debug(f"Variables configured:\n\t{config}")
    try:
        Preparator(config)
    except Exception as e:
        logging.error(f"Something went wrong: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    warnings.simplefilter("ignore", InsecureRequestWarning)

    main()
