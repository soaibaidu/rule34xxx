#!/usr/bin/env python3
"""
Generate artwork prompts for each card row in srp_bitterroot_collection.csv
- Applies unified style skeleton
- Uses faction + rarity augments (incl. Warlock as mutant-led theocracy)
- Outputs: srp_generated_prompts.csv and srp_generated_prompts.txt
"""

import pandas as pd
import re
from pathlib import Path

# ---------- Config ----------
INPUT_CSV = "srp_bitterroot_collection.csv"
OUT_CSV   = "srp_generated_prompts.csv"
OUT_TXT   = "srp_generated_prompts.txt"

# Faction keyword augments & default environments
FACTION = {
    "EspenLock": {
        "keywords": (
            "analog consoles, CRT monitors, cassette drives, chunky machinery, "
            "flickering lights, industrial plastic casings, warning labels, low-tech futurism"
        ),
        "env": [
            "dim retro-tech lab",
            "cassette-tech control room",
            "neonless corridor of humming CRTs",
            "rooftop array of antennas",
        ],
        "mood": "precise, mechanical",
    },
    "STAG": {
        "keywords": (
            "exposed concrete, fortified structures, monolithic geometry, "
            "armored machinery, harsh utilitarian design"
        ),
        "env": [
            "brutalist military checkpoint",
            "concrete fortress gate",
            "armored motor pool",
            "bunker courtyard",
        ],
        "mood": "oppressive, methodical",
    },
    # Cult of Warlock (mutant theocracy)
    "COW": {
        "keywords": (
            "militant clergy, ritual banners, sacred armor and flowing robes, "
            "crusader zeal, authoritarian hierarchy, mutants as ascendants with "
            "greenish-yellow leathery skin"
        ),
        "env": [
            "cathedral-fortress courtyard",
            "shadowed ritual hall",
            "banner-lined cloister",
            "fortress nave with candlelight",
        ],
        "mood": "zealous, reverent, unsettling",
    },
    "Survivors": {
        "keywords": (
            "scavenged gear, patched clothing, sun-bleached fabrics, "
            "improvised weapons and tools, weathered faces, survivalist ingenuity, "
            "nomadic camp resilience"
        ),
        "env": [
            "ruined highway rest stop",
            "burnt forest edge camp",
            "barren plains shanty",
            "abandoned roadside outpost",
        ],
        "mood": "stoic, pragmatic, resilient",
    },
}

# Artifact presentation variants (mixed styles)
ARTIFACT_STYLES = [
    ("journal sketch", "sketchbook illustration with graphite lines and ink smudges, aged and faded"),
    ("propaganda poster", "weathered propaganda print with distressed inks and water damage"),
    ("saintly icon", "oil-painted religious icon with cracked varnish and gilded edges"),
    ("degraded photograph", "grainy, partially blurred photo with torn edges and sun-faded tones"),
]

# Rarity layer mapping
RARITY = {
    "common": "Common (functional, modest, subdued, everyday; muted tones)",
    "uncommon": "Uncommon (refined, distinctive, slightly higher contrast and embellishment)",
    "rare": "Rare (striking, dramatic lighting, richer palettes, elevated presence)",
    "legendary": "Legendary (awe-inspiring, monumental, iconic composition)",
    "artifact": "Artifact (mixed media—sketch/poster/icon/photo—aged, unique, mythic)",
    "special collectible": "Artifact (mixed media—sketch/poster/icon/photo—aged, unique, mythic)",
}

# ---------- Helpers ----------
def get_safe(row: pd.Series, key: str, default: str = "") -> str:
    """Read a column safely as string."""
    val = row.get(key, default)
    if pd.isna(val):
        return default
    return str(val)

def normalize(s: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", s.strip())

def infer_env(faction_key: str, row_index: int) -> str:
    envs = FACTION[faction_key]["env"]
    # deterministic but varied selection by row index
    return envs[row_index % len(envs)]

# ---------- Main ----------
def main():
    src = Path(INPUT_CSV)
    if not src.exists():
        raise FileNotFoundError(f"Input CSV not found: {src.resolve()}")

    df = pd.read_csv(src)
    generated = []

    for idx, row in df.iterrows():
        name = get_safe(row, "Name")
        if not name:
            continue

        raw_faction = get_safe(row, "Faction")
        rarity_raw = get_safe(row, "Rarity").lower()
        subtype = get_safe(row, "Subtype")
        card_type = get_safe(row, "Type")
        # Prefer Subtype if present; else Type; else "unit"
        type_or_subtype = subtype or card_type or "unit"

        # Determine faction key
        rf_low = raw_faction.lower()
        if "espen" in rf_low:
            faction_key = "EspenLock"
        elif "stag" in rf_low:
            faction_key = "STAG"
        elif "cow" in rf_low or "warlock" in rf_low:
            faction_key = "COW"
        elif "survivor" in rf_low:
            faction_key = "Survivors"
        else:
            faction_key = None  # could be Artifact/Special/other

        # Artifact / Special detection
        is_artifact = (
            "artifact" in rarity_raw
            or "special" in rarity_raw
            or rf_low in ["special", "artifact"]
        )

        if is_artifact:
            style_idx = idx % len(ARTIFACT_STYLES)
            style_name, style_desc = ARTIFACT_STYLES[style_idx]
            environment = f"presentation as a {style_name} of uncertain origin"
            keywords = "lost relic, mythic artifact, half-remembered story, whispered rumor"
            rarity_layer = RARITY["artifact"]
            mood = "mythic, uncertain, revered"
            prompt = f"""{name}, depicted as a {type_or_subtype} with {environment}.
Style: cinematic digital painting blended with {style_desc}.
Mood: {mood}.
Faction Augments: {keywords}.
Rarity Layer: {rarity_layer}."""
        else:
            if faction_key in FACTION:
                environment = infer_env(faction_key, idx)
                keywords = FACTION[faction_key]["keywords"]
                mood = FACTION[faction_key]["mood"]
            else:
                environment = "appropriate setting based on lore"
                keywords = "thematic elements consistent with world"
                mood = "atmospheric, grounded"

            rarity_layer = RARITY.get(rarity_raw.lower(), RARITY["common"])

            # Cult of Warlock mutant clause for characters/units/specialists/soldiers/priests
            lower_kind = type_or_subtype.lower()
            mutant_clause = ""
            if faction_key == "COW" and any(k in lower_kind for k in ["unit", "character", "specialist", "soldier", "priest"]):
                mutant_clause = (
                    " Mutant-led theocracy: subjects often show greenish-yellow "
                    "leathery skin and exalted presence."
                )

            prompt = f"""{name}, depicted as a {type_or_subtype} in a {environment}.
Style: cinematic digital painting with high detail and strong atmosphere.
Mood: {mood}.
Faction Augments: {keywords}.{mutant_clause}
Rarity Layer: {rarity_layer}"""

        generated.append({
            "Card ID": get_safe(row, "Card ID"),
            "Name": name,
            "Faction": raw_faction,
            "Rarity": get_safe(row, "Rarity"),
            "Type/Subtype": type_or_subtype,
            "Generated Prompt": normalize(prompt),
        })

    out_df = pd.DataFrame(generated, columns=["Card ID","Name","Faction","Rarity","Type/Subtype","Generated Prompt"])
    out_df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    # Also write a readable text dump (nice for manual QA)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for _, r in out_df.iterrows():
            f.write(f"[{r['Card ID']}] {r['Name']} — {r['Faction']} / {r['Rarity']}\n")
            f.write(f"{r['Generated Prompt']}\n\n")

    print(f"✅ Wrote {len(out_df)} prompts")
    print(f"CSV: {Path(OUT_CSV).resolve()}")
    print(f"TXT: {Path(OUT_TXT).resolve()}")

if __name__ == "__main__":
    main()
