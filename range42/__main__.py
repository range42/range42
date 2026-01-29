import argparse
import logging
import sys
import warnings

from urllib3.exceptions import InsecureRequestWarning

from .config import Config
from .preparator import Preparator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="range42",
        description="Range42 infrastructure CLI",
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize and prepare the deployer infrastructure",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)",
    )

    return parser


def configure_logging(verbosity: int) -> None:
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    warnings.simplefilter("ignore", InsecureRequestWarning)

    if not args.init:
        parser.error("No action specified. Use --init to run the preparator.")

    try:
        config = Config.from_env()
        logging.debug("Configuration loaded successfully")
        Preparator(config).run()
    except Exception:
        logging.exception("Fatal error during initialization")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
