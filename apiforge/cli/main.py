"""The ``apiforge`` command.

Subcommands:

* ``apiforge list`` — list registered plugins with one-line summaries.
* ``apiforge plugins`` — same as ``list`` (alias).
* ``apiforge info <name>`` — show full metadata for a plugin.
* ``apiforge generate`` — generate a plugin from an OpenAPI spec. (TODO[Phase 2])
* ``apiforge install`` — install a plugin package. (TODO[Phase 5])
* ``apiforge update`` — update a plugin package. (TODO[Phase 5])

The future subcommands are wired with ``NotImplementedError`` calls
so users get a clear error rather than a silent pass. We also pre-
register the commands in the parser so ``apiforge generate --help``
works today.
"""

from __future__ import annotations

import json
from typing import Any

import click

from apiforge import APIForge
from apiforge.core.exceptions import APIForgeError, PluginNotFoundError

# ---------------------------------------------------------------------- shared


def _make_client() -> APIForge:
    """Factory used by every subcommand."""
    return APIForge()


# ---------------------------------------------------------------------- list


@click.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def list_cmd(as_json: bool) -> None:
    """List all registered plugins."""
    client = _make_client()
    plugins = []
    for name in client.list_plugins():
        meta = client.get_plugin(name).metadata
        plugins.append(
            {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "auth_type": meta.auth_type.value,
            }
        )
    if as_json:
        click.echo(json.dumps(plugins, indent=2))
        return
    if not plugins:
        click.echo("No plugins installed.")
        click.echo("Install one with: pip install <apiforge-plugin-name>")
        return
    # Manual width calculation keeps the table readable without pulling
    # in a third-party table library for one screen of output.
    name_w = max(len(p["name"]) for p in plugins)
    ver_w = max(len(p["version"]) for p in plugins)
    click.echo(f"{'NAME'.ljust(name_w)}  {'VERSION'.ljust(ver_w)}  AUTH   DESCRIPTION")
    click.echo("-" * (name_w + ver_w + 60))
    for p in plugins:
        click.echo(
            f"{p['name'].ljust(name_w)}  {p['version'].ljust(ver_w)}  "
            f"{p['auth_type'].ljust(5)}  {p['description']}"
        )


# `apiforge plugins` is an alias for `apiforge list`; we re-use the
# same function under a different name.
plugins_cmd = click.command(name="plugins")(list_cmd.callback)  # type: ignore[arg-type]


# ---------------------------------------------------------------------- info


@click.command(name="info")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def info_cmd(name: str, as_json: bool) -> None:
    """Show detailed information about a single plugin."""
    client = _make_client()
    try:
        plugin = client.get_plugin(name)
    except PluginNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    meta = plugin.metadata
    payload: dict[str, Any] = {
        "name": meta.name,
        "version": meta.version,
        "description": meta.description,
        "auth_type": meta.auth_type.value,
        "base_url": meta.base_url,
        "openapi_url": meta.openapi_url,
        "operations": [
            {
                "name": op.name,
                "description": op.description,
                "async": op.async_,
                "parameters": op.parameters,
            }
            for op in meta.operations
        ],
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"{payload['name']} v{payload['version']}")
    click.echo(f"  {payload['description']}")
    click.echo(f"  Auth: {payload['auth_type']}")
    if payload["base_url"]:
        click.echo(f"  Base URL: {payload['base_url']}")
    if payload["openapi_url"]:
        click.echo(f"  OpenAPI: {payload['openapi_url']}")
    if payload["operations"]:
        click.echo("  Operations:")
        for op in payload["operations"]:
            params = ", ".join(op["parameters"]) or "<no params>"
            desc = f" — {op['description']}" if op["description"] else ""
            click.echo(f"    - {op['name']}({params}){desc}")


# ---------------------------------------------------------------------- future commands


@click.command(name="generate")
@click.argument("spec_source")
@click.option("--name", "plugin_name", default=None, help="Plugin name override.")
def generate_cmd(spec_source: str, plugin_name: str | None) -> None:
    """Generate a plugin from an OpenAPI spec.

    TODO[Phase 2]: implement using the OpenAPIGenerator. Today this
    raises an error so the parser wiring can be tested.
    """
    raise click.UsageError(f"Generation from '{spec_source}' is not implemented yet (Phase 2).")


@click.command(name="install")
@click.argument("package")
def install_cmd(package: str) -> None:
    """Install a plugin package from PyPI or a local path.

    TODO[Phase 5]: implement.
    """
    raise click.UsageError(f"Install of '{package}' is not implemented yet (Phase 5).")


@click.command(name="update")
@click.argument("package", required=False)
def update_cmd(package: str | None) -> None:
    """Update installed plugins.

    TODO[Phase 5]: implement.
    """
    target = package or "all plugins"
    raise click.UsageError(f"Update of '{target}' is not implemented yet (Phase 5).")


# ---------------------------------------------------------------------- root


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="apiforge", prog_name="apiforge")
def cli() -> None:
    """APIForge — unified interface for many APIs."""


# Register subcommands. Order matters for ``--help`` output: list
# functionality first, future work last.
cli.add_command(list_cmd)
cli.add_command(plugins_cmd)
cli.add_command(info_cmd)
cli.add_command(generate_cmd)
cli.add_command(install_cmd)
cli.add_command(update_cmd)


# ---------------------------------------------------------------------- entrypoint


def main() -> None:
    """Console-script entry point. Catches APIForge errors and exits 1."""
    try:
        cli(standalone_mode=True)
    except APIForgeError as exc:
        click.echo(f"apiforge: {exc}", err=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
