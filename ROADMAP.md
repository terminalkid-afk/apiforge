# Roadmap

APIForge is delivered in five phases. Each phase is a coherent
deliverable; we don't promise a date for any of them.

---

## Phase 1 — Manual plugins ✅ (current)

The framework, the credential manager, the plugin registry, the CLI
(`list`, `plugins`, `info`), and three first-party plugins
(GitHub, Discord, Notion).

The interfaces that future phases need are already in place — the
`BaseMCPAdapter`, the `OpenAPIGenerator` ABC, the future-CLI command
stubs — even though the implementations are not.

**Status:** Alpha. The public API is `0.1.x` and may evolve.

---

## Phase 2 — OpenAPI plugin generation

Take an OpenAPI 3.x spec (URL or file) and produce a plugin module:

```bash
apiforge generate https://petstore3.swagger.io/api/v3/openapi.json \
    --name petstore --output petstore_plugin.py
```

Deliverables:

- `OpenAPIGenerator` implementation backed by `openapi-spec-validator`
  and `prance`.
- A "draft" mode: the generated plugin is hand-editable, and the
  generator writes back the edits on re-run.
- CLI command: `apiforge generate`.
- Documentation: how to feed a real spec end-to-end.

Why this phase comes second: it lets us grow the plugin catalog
exponentially without writing every plugin by hand. Real-world APIs
ship OpenAPI specs; we should turn that into a feature.

---

## Phase 3 — Automatic SDK generation

Once Phase 2 lands, the next step is to generate *more than just the
plugin skeleton*: a typed Python SDK with Pydantic response models
for every operation.

This phase overlaps with codegen efforts in the Python ecosystem
(we'll evaluate `openapi-python-client`, `fastapi-code-generator`,
and a from-scratch parser). The decision will be made when Phase 2
ships.

Deliverables:

- Generated `apiforge.plugins.<name>.models` per plugin.
- Strict type checking for every operation response.
- `apiforge generate --typed` flag.

---

## Phase 4 — MCP server generation

For every plugin, emit an MCP server description that any MCP-aware
agent can consume:

```bash
apiforge mcp generate github notion --output ./servers
```

Deliverables:

- A default `BaseMCPAdapter` that reads Python type hints and
  produces JSON Schema.
- `MCPGenerator.generate()` returning a complete manifest.
- A runnable server using the official MCP SDK.
- Documentation: how to author a custom adapter when the default
  isn't enough.

This phase is the one that makes APIForge useful as infrastructure
for AI agents — the same way OpenAPI descriptions are infrastructure
for code generation.

---

## Phase 5 — Plugin marketplace

A canonical registry and installation path for third-party plugins:

```bash
apiforge install apiforge-plugin-stripe
apiforge update
apiforge search payments
```

Deliverables:

- A registry index (a static JSON file or a tiny service).
- `apiforge install` / `apiforge update` wired to PyPI under a
  naming convention.
- A review process for new entries — the security model needs to be
  designed carefully because plugin code runs in users' processes.
- A documentation site, likely generated from the per-plugin
  `metadata` and `docstring` blocks.

This is the most ambitious phase and depends on having a healthy
ecosystem in the earlier phases.

---

## Cross-cutting work

Independent of the phase order, the following are ongoing:

- **Async-native operations.** Plugins should use streaming where
  it makes sense (SSE, websockets).
- **Observability.** OpenTelemetry hooks for tracing HTTP calls
  across plugins.
- **Performance.** Connection pool tuning; per-plugin rate limiters
  with backoff.
- **Security.** Token scoping, secret rotation helpers, audit logs.

---

## What we will *not* do

- We will not ship a hosted service. APIForge is a library.
- We will not replace the official SDKs of services that already have
  great ones (e.g. Stripe's Python SDK). We complement; we don't
  compete.
- We will not introduce a runtime plugin sandbox in Phase 5. Plugins
  run in the host process; users opt in.
