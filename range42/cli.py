"""
Command-line interface for the Range42 infrastructure project.

This module provides the main entry point for the Range42 CLI, allowing
users to initialize and prepare the deployer infrastructure.

It supports:

- Argument parsing
- Configurable logging verbosity
- Initialization of the deployer environment via the Preparator
- Suppression of insecure request warnings from urllib3
"""

import argparse
import logging
import sys
import warnings

from urllib3.exceptions import InsecureRequestWarning

from range42.config import Config
from range42.preparator import Preparator


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser for the Range42 CLI.

    :return: Configured ArgumentParser instance.
    :rtype: argparse.ArgumentParser
    """
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
    """
    Configure logging level and format based on verbosity.

    :param verbosity: Verbosity level. 0 = WARNING, 1 = INFO, >=2 = DEBUG.
    :type verbosity: int
    """
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
    """
    Main entry point for the Range42 CLI.

    Parses command-line arguments, sets up logging, loads configuration,
    and runs the Preparator to initialize the infrastructure.

    :param argv: Optional list of command-line arguments. Defaults to None,
                 in which case sys.argv is used.
    :type argv: list[str] | None
    :return: Exit code. 0 for success, 1 for failure.
    :rtype: int
    """
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
