# Darukaa.Earth submission notes

Copy these fields into the required Word document.

## GitHub repository

<paste public or private repo URL>

If the repository is private, grant access to:

- ankita.dasgupta@darukaa.com
- harsh.kumar@darukaa.com
- utkarsh.gauniyal@darukaa.com
- guneet.mutreja@darukaa.com

## Live demo

<paste deployed URL, e.g. Railway/Render/Fly>

Local: `http://127.0.0.1:8000` after `python -m src.api.main`

## README

See `README.md` in the repository root (architecture, schema, setup, CI/CD).

## How to review quickly

1. Open the UI and click **Incomplete report** — the system must ask for SOC, rainfall, and land use.
2. Click **Hackathon example** (SOC 0.3%, low rainfall, monoculture wheat, semi-arid) — expect agroforestry / water-harvesting / diversification with FAO–IPCC–journal citations, not “use sustainable practices.”
3. Inspect the right-hand **Retrieved evidence** and **Causal graph** panes.
4. Optionally POST the same profile to `/api/assess`.

No API key is required. Optional `LLM_API_KEY` only polishes wording.
