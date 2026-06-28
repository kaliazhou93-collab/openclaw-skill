# OpenClaw Skills Collection

A curated set of AI agent skills built for [OpenClaw](https://github.com/claw-works/openclaw) — an open-source agentic coding platform.

Each skill is a self-contained module that gives the AI agent a specialized capability.

## Skills

| Skill | Description | Language | Standalone Repo |
|-------|-------------|----------|-----------------|
| [expense-invoice-download](expense-invoice-download/) | Batch download China region expense invoices, auto-rename, deduplicate, validate for Concur submission | Python | [→ repo](https://github.com/kaliazhou93-collab/expense-invoice-download) |
| [personality-receipt](personality-receipt/) | Generate a "personality receipt" — a fun AI-generated personality summary in receipt format | HTML | [→ repo](https://github.com/kaliazhou93-collab/personality-receipt) |
| [personal-color-analysis](personal-color-analysis/) | Personal color season analysis — determine your color palette based on skin/hair/eye tones | Python | [→ repo](https://github.com/kaliazhou93-collab/personal-color-analysis) |

## What is a Skill?

A skill is a structured prompt + tooling package that extends an AI agent's abilities. Each skill folder contains:

- `SKILL.md` — The skill definition (instructions, triggers, output format)
- `scripts/` — Supporting code (Python, shell, etc.)
- `references/` — Reference materials the agent can consult
- `examples/` — Sample outputs

## How to Use

1. Copy a skill folder into your OpenClaw workspace (or Quick Desktop skill directory)
2. The agent will automatically pick up the skill from `SKILL.md`
3. Trigger it via natural language in chat

## License

MIT — see individual skill folders for details.
