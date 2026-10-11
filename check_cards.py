import re
from pathlib import Path

RESULTS = sorted(Path("results").glob("run_*_before.md"))[-1]
text = RESULTS.read_text(encoding="utf-8")
body = text.split("## What actually happened", 1)[1]

FALLBACK_CARD = "Can't wait to style it"
FALLBACK_OUTFIT = "Try pairing this piece with simple basics"


def sentence_count(card):
    masked = re.sub(r"\$\d+\.\d+", "$PRICE", card)
    return len(re.findall(r"[.!?]+(?=\s|$)", masked))


print(f"Reading {RESULTS}\n")
for section in body.split("\n### ")[1:]:
    print(section.splitlines()[0])
    for block in section.split("**Try ")[1:]:
        number = block.split("**", 1)[0]
        card_match = re.search(r"Fit card:\n\n```\n(.*?)\n```", block, re.S)
        if not card_match:
            print(f"  try {number}: no fit card")
            continue
        card = card_match.group(1)
        item = re.search(r"- selected_item: .*?\(\$([\d.]+), (\w+)\)", block)
        price_str = f"${float(item.group(1)):.2f}"
        platform = item.group(2)
        n = sentence_count(card)
        has_price = price_str in card
        has_platform = platform.lower() in card.lower()
        card_fb = FALLBACK_CARD in card
        outfit_fb = FALLBACK_OUTFIT in block
        ok = 2 <= n <= 4 and has_price and has_platform and not card_fb and not outfit_fb
        print(
            f"  try {number}: {n} sentences | price {price_str} "
            f"{'yes' if has_price else 'NO'} | platform {platform} "
            f"{'yes' if has_platform else 'NO'}"
            f"{' | CARD FALLBACK' if card_fb else ''}"
            f"{' | OUTFIT FALLBACK' if outfit_fb else ''}"
            f" -> {'looks ok' if ok else 'CHECK'}"
        )
    print()