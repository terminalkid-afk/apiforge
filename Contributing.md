# Contributing to APIForge

Thanks for your interest in improving APIForge! This document walks
you through the plugin development workflow, the codebase layout,
the conventions we use, and how to send a pull request.

---

## Code of conduct

Be respectful, assume good faith, and remember there is a person on
the other side of the screen. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/).

---

## Setting up your environment

```bash
git clone https://github.com/apiforge/apiforge.git
cd apiforge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,test]"
```

Run the tests:

```bash
pytest
```

Lint:

```bash
ruff check apiforge tests
ruff format --check apiforge tests
```

Type-check:

```bash
mypy apiforge
```

All three checks run in CI; see `.github/workflows/ci.yml`.

---

## Code layout

```
apiforge/
├── core/                ← client, config, credentials, discovery, metadata
├── plugins/             ← first-party plugins (GitHub, Discord, Notion)
├── mcp/                 ← MCP adapter base + generator (Phase 4)
├── generators/          ← OpenAPI generator (Phase 2)
└── cli/                 ← the `apiforge` command

tests/
├── test_core/
└── test_plugins/
```

The rule of thumb:

- Cross-cutting concerns go in `core/`.
- Each service has its own plugin directory under `plugins/`.
- Adapters and generators are interface-first today; they grow
  alongside the plugins they serve.

---

## Adding a new plugin

The fastest path: copy an existing plugin (`apiforge/plugins/github/`)
and adapt it. The full checklist:

### 1. Create the package

```
apiforge/plugins/<name>/__init__.py
```

For a standalone distribution, the directory name should be
`<name>.py` or a package. The class name must be unique.

### 2. Define metadata

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
            OperationMetadata(
                name="create_charge",
                description="Charge a customer.",
                parameters={"amount": "int", "currency": "str"},
            ),
        ),
    )
```

`PluginMetadata` is strict — extra fields are rejected. The fields
you should fill in:

- `name` — unique, lowercase, matches the entry-point name.
- `version` — semver.
- `description` — one sentence, used in `apiforge list`.
- `auth_type` — one of `token`, `api_key`, `oauth2`, `basic`, `none`.
- `base_url` — the upstream root; some plugins don't have one.
- `operations` — at minimum the operations you implement.
- `openapi_url` — if the upstream publishes a spec.

### 3. Implement operations

```python
async def create_charge(self, amount: int, currency: str) -> dict:
    token = self.require_credential()
    response = await self.http.post(
        f"{self.metadata.base_url}/charges",
        json={"amount": amount, "currency": currency},
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()
```

Conventions:

- All operations are `async def`.
- Use `self.http`, not your own client — we share the pool.
- Use `self.require_credential()` if a credential is mandatory.
- Use `self.get_credential()` if it's optional (e.g. for read-only
  endpoints).
- Don't catch `HTTPStatusError` — let it propagate so the CLI can
  show the upstream status.

### 4. Wire the entry point

In your `pyproject.toml`:

```toml
[project.entry-points."apiforge.plugins"]
stripe = "apiforge_plugin_stripe:StripePlugin"
```

If you're adding to APIForge itself, edit the top-level
`pyproject.toml` instead.

### 5. Add tests

Cover at minimum:

- The plugin's happy path, with `httpx` mocked via `respx`.
- The credential-missing path, if your plugin requires one.
- Auth headers — assert the right `Authorization` header is sent.

See `tests/test_plugins/test_first_party.py` for examples.

### 6. Document

Add a one-paragraph section to the README under "Plugins".
Reference the upstream API docs.

---

## Adding an MCP adapter (Phase 4 preview)

When the MCP generation machinery lands, your plugin will need to
declare an adapter:

```python
from apiforge.mcp.adapter import BaseMCPAdapter


class StripeMCPAdapter(BaseMCPAdapter):
    def tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "stripe__create_charge",
                "description": "Charge a customer.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "integer"},
                        "currency": {"type": "string"},
                    },
                    "required": ["amount", "currency"],
                },
            }
        ]


class StripePlugin(BasePlugin):
    metadata = PluginMetadata(name="stripe", version="0.1.0", ...)
    MCP_ADAPTER_CLASS = StripeMCPAdapter
```

The contract is stable today; the generator walks the registry
looking for `MCP_ADAPTER_CLASS`.

---

## Style

- **Python 3.12+** syntax — `type` aliases, `match`, generics.
- **Type hints everywhere** public. Internal helpers can use less
  formal types where it helps readability.
- **Pydantic models** for any data that crosses a boundary (config,
  metadata, request/response shapes).
- **Ruff** for linting and formatting. Run `ruff format` before
  committing.
- **mypy --strict** is the type-check setting.

---

## Pull request checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Ruff is clean (`ruff check apiforge tests`)
- [ ] mypy is clean (`mypy apiforge`)
- [ ] New code is type-hinted
- [ ] New public surface is documented (docstrings + README update
      if user-facing)
- [ ] If you added a plugin, the entry point is wired in
      `pyproject.toml`
- [ ] CHANGELOG entry (we'll add one once we're out of 0.0.x)

---

## Release process

We use `hatch` for builds. To cut a release:

```bash
# Bump version, update CHANGELOG.
# Tag and push:
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
```

CI builds the wheel and sdist; we publish from CI with PyPI trusted
publishing.

---

## Questions?

Open a GitHub Discussion. Bug reports go in Issues. Security
disclosures: see `SECURITY.md` (TODO — please open an issue for now
and we'll route it).
