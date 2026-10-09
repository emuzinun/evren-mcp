# evren-mcp

[![CI](https://github.com/emuzinun/evren-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/emuzinun/evren-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)

**English** · [Türkçe](README.tr.md)

An [MCP](https://modelcontextprotocol.io) server that connects the **EVREN AI
platform** (Türkiye's defence-industry AI platform) to Claude Code. Ask
*"train a small model on this dataset — how much will it cost?"* and Claude
shows the price, waits for your approval, starts the job, and reports the
results and your leaderboard change.

**What's different:** no credit-spending job starts without a quote that was
shown to you and approved by you. The server also enforces a per-job and a
daily credit cap of its own.

> [!IMPORTANT]
> **Unofficial project.** This is an independent community project. It is not
> developed, endorsed or supported by the Presidency of Defence Industries
> (SSB) or the EVREN AI Platform. The name "EVREN" is used only to describe
> compatibility. The server runs only with **your own** API key; everything it
> does is subject to the EVREN Platform User Agreement on your account. Under
> articles 4.9–4.11 of that agreement, datasets and models you upload may be
> used by the platform for model training.

## Example

```text
You:    Fine-tune a small model on my drone dataset. What will it cost?
Claude: (list_datasets → estimate_training)
        Quote T-51B553 — estimated 0.54 CR, worst case 1.82 CR.
        Spent today: 0 / 20 CR. Valid for 10 minutes. Start it?
You:    Yes.
Claude: (start_training T-51B553) Job started: exporting data → training.
        …
Claude: (get_training) Completed. Actual cost 0.14 CR, mAP50 0.356,
        +15 points.
```

The costs, metric and points above are from a real run on 06.10.2026; the
dialogue is abridged.

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs a suitable Python automatically; Python 3.11+)
- [Claude Code](https://docs.claude.com/en/docs/claude-code) or another MCP client
- An EVREN account and a **Platform** API key (panel → API keys → Platform)

## Install

1. Put your key in a file that only you can read, e.g. `~/.evren-mcp/.env`:

   ```dotenv
   EVREN_PLATFORM_API_KEY=your-platform-key
   ```

2. Register the server with Claude Code (use the full path to the file):

   ```bash
   claude mcp add evren --scope user -e EVREN_ENV_FILE=/full/path/to/.env \
     -- uvx --from git+https://github.com/emuzinun/evren-mcp evren-mcp
   claude mcp list   # evren … ✔ Connected
   ```

   On Windows use a path such as `C:/Users/you/.evren-mcp/.env`.

<details>
<summary>From a local clone (for development)</summary>

```bash
git clone https://github.com/emuzinun/evren-mcp.git && cd evren-mcp
uv sync
cp .env.example .env   # fill in EVREN_PLATFORM_API_KEY
claude mcp add evren --scope user -e EVREN_ENV_FILE=<full-path>/.env \
  -- uv run --directory <full-path> evren-mcp
```

</details>

Ask Claude *"call evren diagnostics"* to check the setup: it shows your
settings with the key masked.

## Tools

User-facing messages are in Turkish.

| Tool | What it does | Cost |
|---|---|---|
| `list_datasets` | Datasets and their versions | free |
| `search_universe` | Search public datasets/models | free |
| `get_credits` | Balance and recent ledger | free |
| `get_standing` | Points, tier, gap to the top 10 | free |
| `estimate_training` | Cost estimate + quote valid for 10 min | free |
| `start_training` | Starts training from a quote | **credits** |
| `get_training` / `list_trainings` | Status, metrics, explained errors, point change | free |
| `stop_training` | Stops a running job (irreversible) | refund |
| `evaluate_model` | Scores a model on a split | ~0.04 CR |
| `download_model` | Downloads weights (`best.pt`) | free |
| `check_dataset_zip` | Checks a zip locally; nothing is sent | free |
| `upload_dataset` | Uploads a zip to a new **private** dataset | free |
| `diagnostics` | Settings (key masked), client capabilities | free |

**Prompts** (slash commands in Claude Code): `egit` — guided training,
`durum` — balance, points and running jobs.
**Resources:** `evren://kurallar` (credit earning rules),
`evren://gunluk` (local training journal).

## Approval gate

```text
estimate_training ──► quote (settings fingerprint, est./worst cost, 10 min)
        │
   you approve
        │
start_training(quote) ──► quote valid & unused? ──► per-job cap ──► daily cap ──► POST
                                 no → refused          (worst case)   (platform ledger, UTC day)
```

1. A quote is single-use and expires after 10 minutes; the server forgets
   quotes when it restarts, so an old price can never start a job.
2. The per-job cap is checked against the platform's worst-case estimate.
3. The daily cap uses today's spending from the platform's own credit ledger,
   plus open quotes and just-started jobs (for 10 minutes), so parallel calls
   cannot both slip under the cap.
4. If the platform gives an unclear answer to a start request, the request is
   **not** resent (that could charge twice); the server looks for the job in
   the job list instead.
5. Claude Code additionally asks for permission on each tool call.

## Settings

Environment variables, or the file named by `EVREN_ENV_FILE` (default: `.env`
in the working directory). Process environment wins over the file.

| Variable | Default |
|---|---|
| `EVREN_PLATFORM_API_KEY` | (required) |
| `EVREN_ENV_FILE` | `./.env` |
| `EVREN_PROJECT_ID` | first project |
| `EVREN_MAX_JOB_CR` | 5 |
| `EVREN_MAX_DAILY_CR` | 20 |
| `EVREN_JOURNAL_PATH` | `~/.evren-mcp/journal.jsonl` |
| `EVREN_DOWNLOAD_DIR` | `~/.evren-mcp/models` |
| `EVREN_MAX_UPLOAD_MB` | 2048 |

## Security and privacy

- The key is sent only over HTTPS to the API host; download links on other
  hosts never receive it. It is masked in every output and error message.
- Requests are throttled to 20/min with burst smoothing, so the platform's
  rate limits are never pushed (its terms forbid bypassing them).
- The training journal and downloaded models stay on your machine.
- See [SECURITY.md](SECURITY.md) to report a vulnerability.

## Deliberately missing

Deleting, making things public, labeling, accepting terms of use, and key
management. These stay manual, in the platform's web panel.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Design notes (Turkish):
[docs/tasarim.md](docs/tasarim.md), measured platform behaviour:
[docs/canli-dogrulama.md](docs/canli-dogrulama.md).

## License

[MIT](LICENSE)
