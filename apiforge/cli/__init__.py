"""Command-line interface.

The CLI is intentionally thin: it shells out to the library rather
than re-implementing logic. Commands are organized as subcommands so
we can add ``generate``, ``install``, ``update`` in later phases
without breaking compatibility.
"""

from apiforge.cli.main import cli

__all__ = ["cli"]
