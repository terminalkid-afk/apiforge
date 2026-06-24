# APIForge

> One Python interface for thousands of APIs.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/apiforge/apiforge/actions/workflows/ci.yml/badge.svg)](https://github.com/apiforge/apiforge/actions/workflows/ci.yml)

APIForge is a plugin-based Python framework that gives you a single,
consistent way to talk to many APIs. The first release ships with
plugins for **GitHub**, **Discord**, and **Notion**; the architecture
is designed to grow to thousands.

```python
from apiforge import APIForge

client = APIForge()
client.configure(
    github_token="ghp_...",
    discord_token="...",
    notion_token="...",
)

# All of these look the same — no separate SDK to learn per service.
user    = client.github.get_user("octocat")
msg     = client.discord.send_message(channel_id="...", content="hi")
pages   = client.notion.list_pages()
```

The same client also exposes a CLI:

```bash
apiforge list
apiforge plugins
apiforge info github
```

---

## Why APIForge?

If you integrate with five services, you install five SDKs, learn
five authentication schemes, and maintain five upgrade cycles.
APIForge collapses that into one.

- **One import.** `from apiforge import APIForge`.
- **One auth surface.** Pass tokens once; they reach every plugin.
- **One plugin contract.** Adding a new service is a small, well-defined job.
- **One way to fail.** A small exception hierarchy that you can catch in one place.
- **One direction.** Async-first under the hood, with sync wrappers for ergonomics.

---

## Installation

```bash
pip install apiforge
```

The base package installs the three first-party plugins
(GitHub, Discord, Notion) automatically. Additional plugins are
distributed as separate packages, e.g.:

```bash
pip install apiforge-plugin-stripe
```

Each one registers itself via the standard `apiforge.plugins`
entry-point group — there's nothing to wire up in your code.

---

## Quickstart

### Sync usage

The simplest path. Every method on a plugin is awaitable under the
hood, but the client exposes a transparent sync wrapper, so you don't
need an event loop for one-off scripts:

```python
from apiforge import APIForge

client = APIForge()
client.configure(github_token="ghp_...")

user = client.github.get_user("octocat")
print(user["login"])
```

### Async usage

For servers, batched jobs, or anything that benefits from concurrency:

```python
import asyncio
from apiforge import APIForge

async def main() -> None:
    async with APIForge() as client:
        client.configure(github_token="ghp_...")
        user, repos = await asyncio.gather(
            client.github.get_user("octocat"),
            client.github.list_repos("octocat", limit=5),
        )

asyncio.run(main())
```

### Credentials

APIForge looks for credentials in this order:

1. **Explicit** — `client.configure(github_token="...")`
2. **Environment** — `APIFORGE_GITHUB_TOKEN=...`
3. **Keyring** — the OS secure store (`keyring` package)
4. **Config file** — `~/.config/apiforge/credentials.toml`

```bash
# Store a token in your OS keyring:
python -c "from apiforge import APIForge; APIForge().credentials.store('github', 'ghp_...')"
```

---

## CLI

```bash
apiforge list               # all registered plugins
apiforge plugins            # alias for `list`
apiforge info github        # details on one plugin
apiforge info notion --json # machine-readable

# Coming in later phases:
apiforge generate openapi.yaml --name myplugin  # Phase 2
apiforge install apiforge-plugin-stripe          # Phase 5
apiforge update                                  # Phase 5
```

---

## Writing a Plugin

A plugin is a class that subclasses `BasePlugin` and declares a
`PluginMetadata`:

```python
from apiforge.plugins.base import BasePlugin
from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata


class StripePlugin(BasePlugin):
    metadata = PluginMetadata(
        name="stripe",
        version="0.1.0",
        description="Stripe payments API.",
        auth_type=AuthType.API_KEY,
        base_url="https://api.stripe.com/v1",
        operations=(
            OperationMetadata(name="create_charge", parameters={"amount": "int"}),
        ),
    )

    async def setup(self) -> None:
        ...

    async def create_charge(self, amount: int) -> dict:
        ...
```

Then register it in your package's `pyproject.toml`:

```toml
[project.entry-points."apiforge.plugins"]
stripe = "apiforge_plugin_stripe:StripePlugin"
```

Once installed, `client.stripe.create_charge(...)` works out of the
box. See [Contributing.md](Contributing.md) for the full checklist.

---

## Project Status

APIForge is in **alpha**. The core framework, the credential
manager, the CLI, and the three first-party plugins are stable
enough for everyday use, but the API may still evolve.

See [ROADMAP.md](ROADMAP.md) for what's next.

---

## Documentation

- [Architecture.md](Architecture.md) — the design, the layers, the contracts.
- [Contributing.md](Contributing.md) — how to write and ship a plugin.
- [ROADMAP.md](ROADMAP.md) — Phase 1 through Phase 5.

---

## License

MIT — see [LICENSE](LICENSE).