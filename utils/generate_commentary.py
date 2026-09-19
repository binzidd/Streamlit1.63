"""
Generate AI earnings commentary using the Anthropic SDK.
Earnings-reviewer managed-agent pattern:
  transcript-reader (extracts figures) -> model-updater -> note-writer (Write holder)

Data is pre-extracted (CBA FY26 PA real figures).
Commentary is generated with claude-opus-4-8 and written to data/commentary.json.
"""

import anthropic
import json
import pathlib
import sys

# ---------------------------------------------------------------------------
# CBA FY26 Pre-Announced Actuals
# ---------------------------------------------------------------------------
ACTUALS = {
    "operating_income_m": 30224,
    "nii_m": 25586,
    "other_income_m": 4638,
    "opex_m": 13755,
    "pre_provision_m": 16469,
    "lie_m": 788,
    "cash_npat_m": 10982,
    "nim_pct": 2.05,
    "cti_pct": 45.5,
    "roe_pct": 14.0,
    "cet1_pct": 12.0,
    "eps_cents": 656.9,
    "dps_cents": 505,
}

# ---------------------------------------------------------------------------
# Forward guidance / key observations
# ---------------------------------------------------------------------------
GUIDANCE = [
    "NIM down 3bps h/h to 2.05% as deposit competition and fixed-rate mortgage roll-off weigh on margins",
    "Business Banking NPAT up 11% driven by volume growth and disciplined repricing",
    "New Zealand division NPAT down 7% on higher provisions and macro headwinds",
    "Retail Banking LIE up 39% from ultra-low base; consumer delinquencies ticking up in arrears",
    "CET1 ratio fell 30bps to 12.0%, comfortably above APRA's 11.25% unquestionably strong benchmark",
    "CTI improved 20bps to 45.5% — cost discipline delivering despite ongoing tech investment cycle",
]

# ---------------------------------------------------------------------------
# Chapter definitions (7 chapters, index 0-6)
# ---------------------------------------------------------------------------
CHAPTERS = [
    {
        "id": 0,
        "title": "Five Years of Income Growth",
        "focus": (
            "Highlight CBA's compound income trajectory over five years. Operating income reached "
            "A$30.2B in FY26 PA, up from ~A$22B in FY21. Emphasise the NII engine — 84.7% of "
            "revenue — and the durability of the franchise through rate cycles."
        ),
        "key_stat": "A$30.2B",
        "key_label": "Cash Operating Income",
        "bg": "white",
    },
    {
        "id": 1,
        "title": "Four Businesses One Result",
        "focus": (
            "Decompose the group result into its four divisions: Retail Banking, Business Banking, "
            "Institutional Banking & Markets, and New Zealand. Business Banking is the standout at "
            "+11% NPAT. Contrast with NZ at -7% and the resilience of Retail despite rising LIE."
        ),
        "key_stat": "+11%",
        "key_label": "Business Banking NPAT growth",
        "bg": "slate",
    },
    {
        "id": 2,
        "title": "Revenue Streams Over Time",
        "focus": (
            "Analyse the NII vs non-interest income split. NII of A$25.6B represents 84.7% of "
            "total income — an unusually high share vs global peers. Other income at A$4.6B covers "
            "fees, trading and insurance. Note the structural NIM pressure from deposit repricing."
        ),
        "key_stat": "84.7%",
        "key_label": "NII share of income",
        "bg": "white",
    },
    {
        "id": 3,
        "title": "Pick a Division",
        "focus": (
            "Give investors an interactive breakdown of divisional NIMs and returns. Business "
            "Banking leads with a 3.39% NIM, well above the group's 2.05%. Retail NIM is under "
            "pressure from fixed-rate roll-off. IBM is a rate-sensitive wild-card. NZ is compressed "
            "by competition and provisioning."
        ),
        "key_stat": "3.39%",
        "key_label": "Business Banking NIM best-in-class",
        "bg": "navy",
    },
    {
        "id": 4,
        "title": "Where Every Dollar Goes",
        "focus": (
            "Break down the expense waterfall: opex of A$13.8B against A$30.2B income gives a "
            "45.5% CTI — 20bps better than prior year. Technology and compliance remain the biggest "
            "cost drivers but productivity gains are showing. Pre-provision profit of A$16.5B is "
            "record territory."
        ),
        "key_stat": "45.5%",
        "key_label": "CTI minus 20bps",
        "bg": "white",
    },
    {
        "id": 5,
        "title": "The Markets Verdict",
        "focus": (
            "Contextualise CBA's ~20x forward PE premium versus ANZ, NAB and WBC at 13-15x. "
            "The premium reflects perceived earnings quality, franchise dominance and a reliable "
            "dividend track record (505c DPS, 78% payout). Discuss whether the premium is "
            "sustainable given NIM headwinds and rising credit costs."
        ),
        "key_stat": "~20x",
        "key_label": "PE premium to peers",
        "bg": "dark",
    },
    {
        "id": 6,
        "title": "CBA by the Numbers",
        "focus": (
            "Summarise the headline scorecard: cash NPAT A$11.0B, ROE 14.0% (+50bps), EPS 656.9c, "
            "DPS 505c, CET1 12.0% (-30bps). Position CBA as the highest-quality Australian bank "
            "but acknowledge the valuation debate heading into the full-year result."
        ),
        "key_stat": "14.0%",
        "key_label": "Cash ROE plus 50bps",
        "bg": "navy",
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a senior sell-side equity analyst writing earnings commentary in Bloomberg editorial "
    "style. Be precise and numbers-first. Lead with the data point, follow with the implication. "
    "Avoid filler phrases like 'it is worth noting' or 'it should be highlighted'. "
    "Return ONLY valid JSON with exactly these keys: "
    "headline (string, max 65 chars), "
    "body (string, exactly 2 sentences, max 200 chars total), "
    "pull_quote (string, max 80 chars), "
    "sentiment (one of: positive, cautious, neutral). "
    "No markdown, no code fences, no extra keys. Raw JSON only."
)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the JSON in them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


def _fallback_entry(chapter: dict) -> dict:
    """Return a placeholder entry when the API call fails."""
    return {
        "headline": chapter["title"],
        "body": chapter["focus"][:200],
        "pull_quote": f"{chapter['key_stat']} — {chapter['key_label']}",
        "sentiment": "neutral",
        "key_stat": chapter["key_stat"],
        "key_label": chapter["key_label"],
        "bg": chapter["bg"],
    }


def generate_all(force: bool = False) -> dict:
    """
    Generate commentary for all 7 chapters.

    Args:
        force: If True, regenerate even if data/commentary.json already exists.

    Returns:
        dict keyed by chapter id (str) with commentary fields.
    """
    output_path = pathlib.Path(__file__).parent.parent / "data" / "commentary.json"

    # Return cached result unless forced
    if output_path.exists() and not force:
        print(f"commentary.json already exists — pass --force to regenerate.")
        with open(output_path) as f:
            return json.load(f)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    actuals_block = json.dumps(ACTUALS, indent=2)
    guidance_block = "\n".join(f"- {g}" for g in GUIDANCE)

    results: dict[str, dict] = {}

    for chapter in CHAPTERS:
        user_prompt = (
            f"CBA FY26 Pre-Announced Actuals:\n{actuals_block}\n\n"
            f"Key guidance observations:\n{guidance_block}\n\n"
            f"Chapter: {chapter['title']}\n"
            f"Focus: {chapter['focus']}\n"
            f"Key stat: {chapter['key_stat']} ({chapter['key_label']})\n\n"
            f"Write the earnings commentary JSON for this chapter."
        )

        try:
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text
            clean_text = _strip_fences(raw_text)
            parsed = json.loads(clean_text)

            # Enrich with display metadata
            parsed["key_stat"] = chapter["key_stat"]
            parsed["key_label"] = chapter["key_label"]
            parsed["bg"] = chapter["bg"]

            results[str(chapter["id"])] = parsed
            print(f"  Chapter {chapter['id']}: {parsed['headline']}")

        except Exception as exc:
            print(f"  Chapter {chapter['id']} FALLBACK ({type(exc).__name__}: {exc})")
            results[str(chapter["id"])] = _fallback_entry(chapter)

    # Write to data/commentary.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} chapters to {output_path}")
    return results


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    result = generate_all(force=force_flag)
    print(json.dumps(result, indent=2))
