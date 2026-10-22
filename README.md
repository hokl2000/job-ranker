# Job ranker – finds Danish job ads and scores my chance of getting hired

A small Python tool that searches Danish job sites, filters the ads, reads the full job description and lets Claude score each ad by **the candidate's chance of being hired** – not just how interesting it looks. The result is a sorted spreadsheet.

Built with Claude as my coding partner, as part of my own AI training plan. Every design decision below came from testing the tool on real job ads and fixing what went wrong.

## How it works

```
find_jobs.py                                    rank_job.py
1. Search Jobindex (8 job titles) + kk.dk  ──▶  5. Claude scores the ad in 5 parts
2. Filter titles (wanted / unwanted words)       (requirements 40, seniority 20,
3. Skip ads already scored (seen.txt)            track 15, commute 15, other 10)
4. Read the full ad (Jobindex summary +       6. Python adds up the parts
   the employer's own ad page)                7. Deal-breaker: unreachable = 0
                                             ──▶ jobs_found.csv, best first
```

**Code does the fixed work, AI does the judgement.** Searching, filtering, de-duplicating, adding up scores and applying deal-breakers are plain Python – predictable and testable. Claude is only asked one narrow question per ad, and must answer in a fixed JSON format.

## Design decisions (and the test that led to each)

| Decision | Why – what the test showed |
|---|---|
| Own system prompt instead of the default | Cut the input from ~23,600 to ~750 tokens per call. |
| Full profile, facts stated directly | A nature-partnership job scored 45 with a thin profile and 78 with the full one. Given only dates, the model said "4 years" instead of 5. |
| Part-scores, added up by Python | One job got the reason "exact match" but a total of 35. With part-scores it got 63, and every point can be traced. |
| Deal-breakers in code, not in the score | A job 2 hours away still scored 45, because "transport 0" only costs 15 points. Now unreachable = 0. |
| Read the employer's full ad | The first version sent Jobindex's menus and cookie banner (5,447 characters, no ad text) to the model. It was scoring from the title alone. |
| Ad text is treated as data | Following links means reading pages I don't control. The prompt says to ignore instructions in the ad, Claude runs with no tools, and suspicious phrases are flagged for a human check. |
| Polite scraping | Only pages allowed by the sites' robots.txt, first result page only, 3 seconds between requests. |
| Fossil fuel filter | Employers that extract, refine or sell oil or gas are skipped – a personal deal-breaker. |

**Measured, not assumed:** the same ad scored between 60 and 72 across runs, so differences smaller than ~10 points are noise. Adding a fixed scoring rubric did *not* reduce that spread (tested over 3 runs per ad) – the ranking was stable, single scores were not.

## Setup

1. Install [Claude Code](https://code.claude.com/docs/en/setup) and log in (`claude`). The tool calls it with `claude -p`.
2. Python 3.10+ (only the standard library is used – nothing to install).
3. Copy `profile_example.txt` to `profile.txt` and fill in your own profile. `profile.txt` is private and is not uploaded.
4. Run:
   ```
   python find_jobs.py
   ```
   Open `jobs_found.csv` in Excel. Search words, filters and the max number of ads per run (`MAX_ADS`) are at the top of `find_jobs.py`.

To score ads you paste yourself, put them in `ads.txt` (one ad per block, empty line between ads) and run `python rank_job.py`.

## Limitations

- Employer ad pages that are built in the browser with JavaScript can't be read; the Jobindex summary is used instead.
- kk.dk titles come from the link, so æ/ø/å appear as ae/oe/aa.
- Scores vary by up to ~10 points between runs – use them to sort, not as exact truth.

## tool_loop.py – an AI agent

`find_jobs.py` + `rank_job.py` is a fixed pipeline: Python decides every step and Claude scores each ad.
`tool_loop.py` is an agent: you give it a question, and Claude decides which tools to call to answer it.

- **Tools:** `list_ads()` (the scored job list) and `get_ad(number)` (fetches one ad's text)
- **Protocol:** Claude answers each turn in JSON (`call_tool` or `final`), forced by a JSON schema
- **Python holds the memory and the brakes:** max 8 turns, max 5 web fetches
- **Safeguards:** Claude gives a row number, never a URL (least privilege); ad text is treated as data, not instructions; cut text is marked so the model knows it is incomplete

Run: `python tool_loop.py` (needs `jobs_found.csv` from `find_jobs.py`).

## Second backend: the official Anthropic SDK (tested, never run live)

`tool_loop.py` can talk to Claude in two ways, chosen by `BACKEND` in its settings:

- `"cli"` (default): `claude -p` via the Claude Code CLI on a Claude Pro login. This is the backend that actually runs.
- `"sdk"`: Anthropic's official Python SDK with its built-in tool use (tools with `input_schema`, `stop_reason == "tool_use"`, `tool_result` blocks sent back).

The SDK backend is **never run live**: it needs an API key, and API usage is billed separately from Claude Pro. Instead it is unit-tested with a fake client that returns scripted responses:

    python test_tool_loop.py

The test needs no API key, no internet and no `anthropic` package. It reads `jobs_found.csv`, so run `find_jobs.py` first. Real use would add `import anthropic` and `client = anthropic.Anthropic()`.