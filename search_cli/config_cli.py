import argparse
import sys
from dataclasses import fields
from typing import List

from search_cli.config import (
    CONFIG_PATH,
    config_field_names,
    load_config,
    set_config_value,
    unset_config_value,
)
from search_cli.providers import REGISTRY
from search_cli.ui import console


def run_config_command(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="terch config",
        description="View or modify terch's config file without opening it",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("show", help="Print the full current config")
    sub.add_parser("path", help="Print the config file path")

    get_parser = sub.add_parser("get", help="Print a single config value")
    get_parser.add_argument("key", choices=config_field_names())

    set_parser = sub.add_parser("set", help="Set a config value")
    set_parser.add_argument("key", choices=config_field_names())
    set_parser.add_argument("value")

    unset_parser = sub.add_parser("unset", help="Reset a config value to its default")
    unset_parser.add_argument("key", choices=config_field_names())

    args = parser.parse_args(argv)

    if args.action == "path":
        console.print(str(CONFIG_PATH))
        return

    if args.action == "show":
        config = load_config()
        for f in fields(config):
            console.print(f"[cyan]{f.name}[/cyan] = {getattr(config, f.name)}")
        return

    if args.action == "get":
        config = load_config()
        console.print(getattr(config, args.key))
        return

    if args.action == "set":
        if args.key == "default_provider" and args.value.lower() not in ("none", "unset", "") and args.value not in REGISTRY:
            console.print(
                f"[yellow]Notice:[/yellow] {args.value!r} isn't a known provider "
                f"({', '.join(REGISTRY.keys())}), setting it anyway.\n"
            )
        try:
            config = set_config_value(args.key, args.value)
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)
        console.print(f"[bold green]Set[/bold green] {args.key} = {getattr(config, args.key)}")
        return

    if args.action == "unset":
        config = unset_config_value(args.key)
        console.print(f"[bold green]Reset[/bold green] {args.key} = {getattr(config, args.key)}")
        return
