import re
import sys
from collections import Counter
from pathlib import Path

body = Path(sys.argv[1]).read_text(encoding="utf-8").split("## What actually happened", 1)[1]
openers = Counter()

for section in body.split("\n### ")[1:]:
    name = section.splitlines()[0]
    wardrobe = re.search(r"- Wardrobe: (\w+)", section).group(1)
    if name.startswith(("impossible", "state")):
        print(name)
    for block in section.split("**Try ")[1:]:
        number = block.split("**", 1)[0]
        trace = block.split("Trace:", 1)[-1] if "Trace:" in block else ""
        if name.startswith("impossible"):
            stopped = "- stopped early: yes" in block
            skipped = not re.search(r"\[\d+\] suggest_outfit", trace)
            print(f"  try {number}: stopped early={stopped}, no suggest_outfit step={skipped}")
        if name.startswith("state"):
            ids = re.findall(r"id=(lst_\d+)", trace)
            print(f"  try {number}: ids seen {ids} -> {'all equal' if len(ids) == 3 and len(set(ids)) == 1 else 'CHECK'}")
        outfit = re.search(r"Outfit suggestion:\n\n```\n(.*?)\n```", block, re.S)
        if outfit and wardrobe == "example":
            openers[outfit.group(1).strip().split()[0].strip(",.!").lower()] += 1

print("\nFirst words of example-wardrobe outfits:")
print(", ".join(f"{w} ({n})" for w, n in openers.most_common(10)))