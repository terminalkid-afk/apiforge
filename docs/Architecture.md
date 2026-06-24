# APIForge — Architecture

This document explains **how** APIForge is put together and **why**
each piece is shaped the way it is. The goal is that by the end you
can answer two questions:

1. *Where does new code go?*
2. *What contracts does it have to honor?*

---

## Bird's-eye view

```
                         ┌─────────────────────────────────────┐
                         │           User Code                 │
                         │   from apiforge import APIForge     │
                         └────────────────┬────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────────┐
                         │          APIForge (client)          │
                         │  - HTTP client (shared)             │
                         │  - Credential manager               │
                         │  - Config                           │
                         │  - Plugin cache                     │
                         └────────────────┬────────────────────┘
                                          │
            ┌─────────────────┬───────────┴───────────┬─────────────────┐
            ▼                 ▼                       ▼                 ▼
    ┌──────────────┐  ┌──────────────┐       ┌──────────────┐   ┌──────────────┐
    │  Plugin: GH  │  │  Plugin: DC  │  ...  │  Plugin: NT  │   │ Plugin: YOU  │
    │  (BasePlugin)│  │  (BasePlugin)│       │  (BasePlugin)│   │ (BasePlugin) │
    └──────┬───────┘  └──────┬───────┘       └──────┬───────┘   └──────┬───────┘
           │                 │                       │                 │
           └─────────────────┴───────────┬───────────┴─────────────────┘
                                         │
                                         ▼
                       ┌──────────────────────────────────┐
                       │  HTTP transport (httpx.AsyncClient)│
                       └──────────────────────────────────┘
                                         │
                                         ▼
                              Upstream service APIs
```

The same `APIForge` instance is the **only** object a plugin ever
needs to reach into to get an HTTP client, a credential, or the
current config. There is no global state.

---

## The five layers

### 1. The Client (`apiforge.core.client`)

`APIForge` is the user-facing façade. It owns three long-lived
resources and shares them with every plugin:

- `httpx.AsyncClient` — connection-pooled HTTP transport.
- `CredentialManager` — secrets resolution.
- `APIForgeConfig` — knobs like timeout, retries, user-agent.

Plugins are looked up by attribute (`client.github`). The first
attribute access instantiates the plugin, runs `setup()`, and
caches it.

### 2. Credentials (`apiforge.core.credentials`)

`CredentialManager` resolves secrets through a strict priority chain:

```
explicit  →  environment  →  keyring  →  config file
(highest)                                   (lowest)
```

Why this order? Because the **explicit** layer is what tests use:
they construct the manager, call `set("github", "fake")`, and the
plugin sees a credential without ever touching the developer's
environment. End users get the same ergonomics with `client.configure()`.

The **keyring** layer is the security sweet spot — tokens never sit
in plaintext on disk, and they survive shell sessions. It is optional:
if the `keyring` package isn't installed or no backend is available
(common on headless Linux), the manager silently moves on.

### 3. Discovery (`apiforge.core.discovery`)

`PluginRegistry` walks `importlib.metadata` entry points in the
`apiforge.plugins` group. Third-party packages register themselves
by listing the entry point in their own `pyproject.toml`. No code in
APIForge has to know about them in advance.

The registry holds **classes**, not instances. Instantiation is the
client's job because the constructor needs a reference to the parent
client.

### 4. The Plugin Contract (`apiforge.plugins.base`)

`BasePlugin` defines what every plugin looks like from the outside:

- A `metadata` class attribute (`PluginMetadata`) — the plugin's
  self-description.
- An async `setup()` hook — first-use initialization.
- An async `teardown()` hook — resource cleanup.
- An optional credential accessor — `get_credential("name")` /
  `require_credential("name")`.
- A reference to the parent client — `self._client`.

Plugins don't subclass anything else. They don't have to override
anything besides `setup()` and `metadata`.

### 5. Plugin Metadata (`apiforge.core.metadata`)

`PluginMetadata` is the *only* thing every plugin MUST publish, and
it's a strict Pydantic schema. This means:

- The CLI can list and inspect plugins without importing them.
- A future OpenAPI generator can produce a complete `PluginMetadata`
  block mechanically.
- A future MCP generator can read operations without parsing Python.

It is the public contract between plugins and the rest of the system.

---

## Async, with a sync escape hatch

Every operation in `BasePlugin` is `async def`. This is deliberate:

- A single plugin making N requests can pipeline them with
  `asyncio.gather`.
- Mixing async and sync code in one library usually means the sync
  path is the slow one.
- Modern Python users overwhelmingly expect async APIs.

But the documented example —

```python
client.github.get_user("octocat")
```

— is sync. That's the `SyncProxy` in `apiforge.core.client`: a thin
object that returns awaitable wrappers. We use `asyncio.run` per
call, which is fine for scripts and small projects. For high-volume
async use, drop down to `await` directly.

---

## Plugin discovery: entry points, not filesystem walks

There are two common ways to discover plugins in Python:

1. **Filesystem scan** — look for `*.py` under a directory.
2. **Entry points** — ask `importlib.metadata` for declared plugins.

We use entry points. Reasons:

- A plugin can live in any package on `sys.path`, including a
  zip-imported one. Filesystem scanning misses both.
- Entry points declare metadata (name, version), which the registry
  uses to dedupe.
- Vendoring a plugin into the main package becomes trivial: list
  it in `pyproject.toml`, no code change.

The cost is small: every third-party plugin needs a `pyproject.toml`
entry. The convention is documented in [Contributing.md](Contributing.md).

---

## The MCP and OpenAPI seams

Two future-facing subsystems are deliberately abstract today:

### MCP adapters (`apiforge.mcp.adapter`)

`BaseMCPAdapter` is the contract a plugin uses to expose itself as
an MCP tool. Plugins ship an adapter next to the plugin class.
The adapter knows how to:

- Render the plugin's operations as MCP tool definitions.
- Dispatch incoming tool calls back to the right plugin method.

A default adapter that reads Python type hints is the Phase 4 work.

### OpenAPI generator (`apiforge.generators`)

`OpenAPIGenerator` is an abstract base class. Its subclasses parse
an OpenAPI spec and produce a Python plugin module. A
`StubOpenAPIGenerator` ships today so the CLI parser wiring can be
exercised; the real parser is Phase 2.

The CLI commands `apiforge generate`, `apiforge install`, and
`apiforge update` are already wired. They raise
`NotImplementedError` with a clear "Phase N" message. This means
`apiforge generate --help` works today, the user gets a precise
error if they try to use the command, and Phase 2 only has to fill
in implementations.

---

## Configuration: layering

```
.─────────────────────────────────────────.
│  CLI flag (future) / APIForge.configure │
├─────────────────────────────────────────┤
│  Environment variable (APIFORGE_*)      │
├─────────────────────────────────────────┤
│  .env file                              │
├─────────────────────────────────────────┤
│  pydantic-settings defaults             │
'─────────────────────────────────────────'
```

Each layer overrides the one below it. `pydantic-settings` does the
heavy lifting. We do not use Python's own `configparser` because
TOML is more idiomatic for Python 3.12+ and Pydantic handles nested
validation for us.

---

## Why these dependencies?

| Library          | Why                                                                 |
|------------------|---------------------------------------------------------------------|
| `httpx`          | Sync + async in one package, type-hinted, HTTP/2 capable.           |
| `pydantic` v2    | The validation engine behind every model in the project.            |
| `pydantic-settings` | Layered configuration out of the box.                            |
| `click`          | Subcommand-friendly, well-documented, decorator-based.              |
| `rich`           | (Future) pretty CLI output; listed so the dep tree is stable.       |
| `keyring`        | OS secure storage; treated as optional.                              |

We deliberately avoid heavy frameworks (no Django, no FastAPI, no
SQLAlchemy). APIForge is a *library*, not a server. Every dependency
is a "we use it heavily" dependency, not a "we might use it" one.

---

## Testing strategy

```
tests/
├── conftest.py             shared fixtures
├── test_core/
│   ├── test_client.py      client surface
│   ├── test_credentials.py credential resolution
│   └── test_discovery.py   registry + metadata
└── test_plugins/
    └── test_first_party.py GitHub / Discord / Notion with respx
```

- **Unit tests** cover every public class.
- **Plugin tests** use `respx` to mock the upstream HTTP API, so we
  don't need a live connection.
- **Authentication tests** walk the priority chain and verify that
  secrets are redacted in any output.

Coverage is enforced in CI (`--cov=apiforge`). See
`.github/workflows/ci.yml`.

---

## Versioning

APIForge follows [Semantic Versioning](https://semver.org/). The
0.y.z range is the alpha series: anything may change, but the
documented public API (`APIForge`, the plugin base class,
`PluginMetadata`) is the most stable. Breaking those is reserved
for 1.0.
