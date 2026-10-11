import re
import sys
from pathlib import Path

GREETING = re.compile(r"^(hey|hi|hello|yo)\b", re.I)


def analyse(path):
    body = Path(path).read_text(encoding="utf-8").split("## What actually happened", 1)[1]
    out = {
        "example outfits": 0, "example greetings": 0,
        "empty outfits": 0, "empty greetings": 0,
        "fit cards": 0, "missing exact price": 0,
        "outside 2-4 sentences": 0, "fallbacks used": 0,
    }
    for section in body.split("\n### ")[1:]:
        wardrobe = re.search(r"- Wardrobe: (\w+)", section).group(1)
        kind = "example" if wardrobe == "example" else "empty"
        for block in section.split("**Try ")[1:]:
            outfit = re.search(r"Outfit suggestion:\n\n```\n(.*?)\n```", block, re.S)
            card = re.search(r"Fit card:\n\n```\n(.*?)\n```", block, re.S)
            if outfit:
                text = outfit.group(1).strip()
                out[f"{kind} outfits"] += 1
                out[f"{kind} greetings"] += bool(GREETING.match(text))
                out["fallbacks used"] += "Try pairing this piece with simple basics" in text
            if card:
                item = re.search(r"- selected_item: .*?\(\$([\d.]+), (\w+)\)", block)
                price = f"${float(item.group(1)):.2f}"
                text = card.group(1)
                out["fit cards"] += 1
                out["missing exact price"] += price not in text
                masked = re.sub(r"\$\d+\.\d+", "$P", text)
                n = len(re.findall(r"[.!?]+(?=\s|$)", masked))
                out["outside 2-4 sentences"] += not 2 <= n <= 4
                out["fallbacks used"] += "Can't wait to style it" in text
    return out


for path in sys.argv[1:]:
    print(path)
    for key, value in analyse(path).items():
        print(f"  {key}: {value}")
    print()