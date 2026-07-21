---
user-invocable: true
name: agentour-compiler
description: Fully automatic Agentour Agent compiler. Selects local or competition platform, validates the developer token, discovers models, then invents a new Agent or reconstructs existing Agent projects through strict one-question-per-turn brainstorm and grill-me interviews, fidelity verification, validation, and private/public upload.
---

# Agentour Compiler

Run the entire process. The user must never coordinate phases, agents, validators, commands, or retries.

## Non-bypassable bootstrap gate

Immediately after reading this Skill, before any explanation or workflow question, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" bootstrap
```

Do not introduce the Compiler first and do not enter discovery until it returns
`ready_for_interview: true`. For `platform_choice_required`, ask only the fixed platform choice and
rerun with `--target-platform`; for `token_required`, ask only for that token, store it, and rerun;
for `restart_required` or `blocked`, stop. The visible bootstrap command is the audit proof that
update, identity, Contract, model probes, and recovery checks ran.

## Bootstrap internals: version check

Before asking the first workflow question, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" check-update --auto
```

If it reports `updated: true`, stop this run and tell the user to restart Claude Code so the new Plugin is loaded. Never continue the workflow with the old in-memory Plugin. If the network check is temporarily unavailable, warn briefly and continue; if an update is known but automatic installation fails, stop and report the installer error.

## Iron rule: one decision per turn

Each conversational turn may ask exactly one question or offer exactly one choice.

- Never bundle questions in bullets, numbered fields, or paragraphs.
- Never ask for three examples in one turn; collect them across turns.
- A multi-option choice must resolve one decision only.
- After every answer, update the spec/state and ask the single next highest-value question.
- Continue all unblocked inspection, generation, testing, and repair between questions.

## Fixed platform targets

| Choice | Platform | URL |
|---|---|---|
| A | 本地服 | `http://127.0.0.1:8600` |
| B | 比赛服 | `https://agentour.ai` |

Never ask the user to type or configure a URL.

## Mandatory dual-state sequence

Persist non-secret progress in `.agentour/compiler-state.json` and `/v1/dev/compiler-tasks`.
After authentication, reconcile local and remote active tasks by task ID, Agent ID, operation,
workspace ID, Package hash, revision, and update time. Platform job status overrides stale local
`running` state. Restore a missing local workspace from the remote Package checkpoint after verifying
SHA-256. Continue saved Validation, Build, Eval and Publish Job IDs; never resubmit them blindly.
Upload a clean checkpoint before Package-changing stage transitions and mark terminal tasks completed
or cancelled. Never persist the token or provider secrets.

Record start, finish and duration for discovery, conversion, environment preparation, local
validation, platform validation, remote Build, Smoke/Evals, upload and publish. Show the real current
stage and never label the entire Compiler run as “上传”.

### 1. Choose platform

The first unresolved message must ask only:

> 请选择发布平台：A. 本地服；B. 比赛服。

### 2. Validate developer token

First inspect the selected platform's saved credential:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_store.py" status <local|competition>
```

If a token is stored, validate it silently and do not ask the user. Ask for a token only when none is stored or the platform explicitly returns 401/403. Validate a replacement and store it with `credential_store.py set <platform>`. The script automatically chooses the operating system credential backend.

```bash
AGENTOUR_TOKEN="<token>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> verify-token
```

Use `GET /v1/dev/me`. If invalid, ask only for a corrected token after the user checks the selected platform's console. Never print, place in command arguments, save in the project, commit, or report the token.

### 3. Discover models

After successful token validation, fetch the compiler contract and models:

```bash
AGENTOUR_TOKEN="<token>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> contract
AGENTOUR_TOKEN="<token>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> models
```

The `models` command probes every returned model, removes failures from `data`, sorts usable models by platform quality rank, and returns `recommended_model`. Unless the user explicitly names a model, requests a cost ceiling, or says to prioritize economy, always use `recommended_model`: Plugin-authored cost optimization must never silently downgrade Agent quality. Economic tradeoffs belong to the developer. Use `filtered_unavailable` only for diagnostics. Use the contract's canonical model IDs, Smoke schema, Node/Eve versions, ignore rules, upload limit, pricing unit, and runtime semantics. Run `model-probe <model>` once more immediately before generation and never use a model that fails.

### 4. Choose intent and source

Ask only:

> 这次是：A. 更新已发布的 Agent；B. 重构已有项目；C. 从零创建 Agent？

Do not ask again when the user's intent is already explicit.

## Update an owned Agent

Query `GET /v1/dev/packages` and `/v1/dev/packages/update-intents`. Match only Packages owned by the
validated developer. Exact matches continue; fuzzy or multiple matches require one choice. A missing
match must ask whether the name is wrong or creation was intended—never silently create. Download and
hash-check the active immutable baseline, compare the highest SemVer, preserve unaffected behavior,
and create a new immutable version. Revalidate the model, examples, approvals, deliverables, Knowledge
Contract, Smoke, Evals and fidelity.

## Existing Agent path

Inspect the repository before asking discoverable facts. Inventory every Agent, entrypoint, prompt, Skill, Tool, MCP server, sub-agent, workflow, router, test, example, dependency, environment variable, external service, file/attachment behavior, approval, artefact, retry, and failure path.

If multiple Agents exist, ask only:

> 检测到多个 Agent。你希望：A. 合成一个 Agent；B. 分别转换并上传全部 Agent；C. 只转换其中一部分？

- If C, the next turn asks only which Agents to include; multi-select is allowed as one scope choice.
- If A, preserve all source roles, routing, orchestration, tools, and boundaries in one Package.
- If B, create one Package and fidelity report per Agent.

Create `.agentour/conversion-inventory.json`, `.agentour/conversion-map.json`, and `.agentour/fidelity-report.json`. Record every capability as preserved, adapted, reimplemented, degraded, unsupported, or explicitly authorized removed.

Use the `brainstorm` and `grill-me` agents internally to challenge uncertain business behavior. Do not require the user to invoke them.

## New Agent path

Create `AGENT_SPEC.md` immediately and begin with one open invitation:

> 请尽可能完整地讲讲你想做的 Agent。可以包括给谁用、解决什么问题、用户会提供什么、它要执行哪些步骤、需要连接哪些系统，以及最后交付什么；不完整也没关系，我会整理后只追问关键缺口。

Extract the answer into a field evidence map with value, confidence, and source:
`user_explicit`, `source_discovered`, `platform_discovered`, `inferred`, `defaulted`, or `missing`.
Then dispatch `brainstorm` and `grill-me` internally. Ask one question per turn only for unresolved
high-impact gaps or conflicts. Mature users may need few or no follow-ups; vague ideas retain the
guided one-question flow. Do not reconfirm explicit answers or low-risk defaults.

Do not generate until the intended workflow is precise. When the original request already authorizes creation, do not ask a separate “start coding” question.

## Generate Package(s)

Use `templates/` and the relevant guides. Each Package must contain `agentour.json`, consumer README, release notes, Smoke Tests, lockfile, Eve runtime entrypoint, instructions, pinned sandbox, deterministic tools, and domain knowledge.

Preserve source flow, tool contracts, approvals, attachments, schemas, artefacts, failure/retry behavior, and user-visible interactions. Every loaded capability needs business-readable `runtime_ui` text. Never expose `load skill`; `waiting_approval` is waiting, not running.

- Price in **积分** with `pricing.amount_credits`, never RMB cents.
- Generate Smoke `schema_version: 1` with only `send`, `expect_tool`, `expect_contains`, `expect_approval`, and `expect_question`.
- Missing required input must call Eve `ask_question` and emit `input_requested`.
- Check Node/pnpm first. Require Node 24 and never compile Node from source.
- Run `pnpm install --lockfile-only`; do not install project `node_modules` just to create a lock.
- Run local builds in a Linux temp copy or compatible container, then remove the temp directory.
- Record contract version, publish jobs, failed Gates, repairs, and results in `.agentour/compiler-state.json`, never tokens.

## Validate and repair automatically

Dispatch `validator`, generate the lockfile, build, run Smoke Tests, source tests, and relevant project tests. Fix failures narrowly and repeat until green or genuinely blocked. Never weaken valid tests or hand the validator report to the user as homework.

Before visibility or formal upload, every Package must pass:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" build-test packages/<agent-id>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" --platform <local|competition> \
  validate-package packages/<agent-id>
```

The first command installs locked dependencies and runs the Eve build in an isolated temporary copy, then removes it. The second runs the platform's exact build and Smoke Gates without publishing or occupying a Registry version. Formal upload must never be the first real execution test.

## Fidelity requirement

For reconstruction, create same-case comparisons from tests, examples, sanitized real cases, prompts, and workflows. Compare workflow/routing, tools/arguments, approvals, files/attachments, schemas, artefacts, normal/boundary/failure/retry/multi-turn behavior, semantic result, latency, and resources.

Bind the fidelity report to the final Package SHA-256. Any critical workflow, tool, approval, attachment, schema, or artefact mismatch blocks upload regardless of score. Repair and rerun until fidelity is as high as technically possible; disclose remaining degradation.

## Choose visibility

After validation and fidelity pass, ask only:

> 请选择上传方式：A. 私有；B. 公开（需要平台审核）。

For multiple Packages, first ask whether one setting applies to all or should be selected one by one. If one by one, ask one Package per turn.

## Upload

Revalidate the token immediately before upload. Present one compact summary of platform, IDs, versions, models, visibility, validation, fidelity, and limitations. If upload was requested, proceed; otherwise ask one final upload confirmation.

Only after that explicit confirmation, run the paid-resource remote Build Gate. Do not run it during brainstorming, grilling, local validation, visibility selection, or while waiting for upload confirmation. A cached Build does not consume a new E2B build quota.

Immediately before Build, run `build-preflight` to verify E2B service configuration, Runtime Profile
template, active capacity, hourly/daily quota, Node and Eve contract. If unavailable, preserve the task
and Package checkpoint rather than starting a doomed Build.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> build-preflight
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> remote-build packages/<agent-id>
```

Read the structured `gates` result. Repair deterministic failures narrowly and rerun only after Package content changes. Do not blindly retry unchanged content; the client may retry one transient platform/model failure internally. Publish only after the remote Build reaches `succeeded`.

If the API returns `429`, report that the active/daily E2B quota is exhausted and wait; do not
change the Package hash or loop retries to evade quota. A cached response is a valid Build result
and consumes no new quota. If the user cancels or the Package is superseded, run
`cancel-build <job-id>` and confirm the terminal status before starting another paid Build.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> publish-async packages/<agent-id> \
  --visibility <private|public>
```

Follow every job. On Gate failure, fix, bump the version when needed, rebuild fidelity evidence, and retry. Finish with final platform status and Package identifiers.

## Required post-publish feedback

After every successful deployment, generate `问题梳理与优化意见清单.md`. It must cover only Agentour platform and Compiler Plugin defects or improvement opportunities—not ordinary defects in the generated Agent's domain logic.

Read `guides/feedback.md` before writing the report.

Use the entire run as evidence: intent misunderstandings, weak interview questions, wrong defaults, contract drift, unnecessary dependencies, packaging/build friction, platform-only Gate failures, diagnostics, model routing, billing wording, manual work, and fidelity limitations caused by platform or Plugin design.

Include run scope, successful publish result, P0/P1/P2 findings, evidence, root cause, and actionable recommendations. If no issue was found, state what was checked and upload a no-findings report.

```bash
AGENTOUR_TOKEN="<token>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agentour_api.py" \
  --platform <local|competition> feedback "问题梳理与优化意见清单.md" \
  --plugin-version "2.8.0" --operation <create|reconstruct|update> \
  --agent-id <agent-id> --publish-job <job-id>
```

Feedback upload is required for successful completion. Report the returned feedback ID.

## Resources

- `agents/brainstorm.md` — one-question domain exploration
- `agents/grill-me.md` — one-question ambiguity elimination
- `agents/validator.md` — automatic Package and fidelity validation
- `guides/migration.md` — migration patterns
- `guides/gates.md` — Gate repair
- `guides/ux-checklist.md` — user experience requirements
- `guides/tool-patterns.md` — deterministic and approval tools
- `templates/` — Package templates
