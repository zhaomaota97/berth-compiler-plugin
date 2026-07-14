# Berth Compiler Plugin for Claude Code

Full-auto Claude Code Plugin for inventing new Berth Agents or reconstructing existing Agent projects with high behavioral fidelity.

## Install

```text
/plugin marketplace add berth-platform https://github.com/zhaomaota97/berth-compiler-plugin
/plugin install berth-compiler@berth-platform
```

At startup the Plugin checks the Marketplace version and installs a newer release automatically. Restart Claude Code after an upgrade so the new Plugin code is loaded. Model discovery probes every platform model and filters failed models before Agent generation.

Start a new Claude Code session, then run:

```text
/berth-compiler
```

## Workflow

The Plugin strictly asks one question or one choice per turn:

1. Choose **本地服** (`http://127.0.0.1:8600`) or **比赛服** (`http://61.29.254.146`).
2. Enter a `bt_` developer token; it is validated with `GET /v1/dev/me` and never written to files.
3. The Plugin fetches enabled models from `GET /v1/models`.
4. Choose existing-Agent reconstruction or new-Agent invention.
5. Internal brainstorm and grill-me agents conduct a multi-round, one-question interview.
6. The Plugin generates Package(s), validates, repairs, and verifies fidelity.
7. Choose private or public upload, then the Plugin publishes and follows the job.

If a source repository contains multiple Agents, the Plugin inventories them and asks whether to merge all into one Package, convert all separately, or select a subset.

A successful build is not considered proof of equivalence. Critical workflow, tool, approval, attachment, schema, or artefact mismatches block publication.
