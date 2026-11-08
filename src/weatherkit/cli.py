"""Command-line interface."""
import argparse
from .client import Client


def main(argv=None):
    """Entry point for `weatherkit CITY`."""
    p = argparse.ArgumentParser(prog="weatherkit")
    p.add_argument("city")
    a = p.parse_args(argv)
    print(Client().forecast(a.city))
