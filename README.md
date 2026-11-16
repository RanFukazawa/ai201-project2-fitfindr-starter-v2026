# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is a thrifting agent. A user describes what they want in plain language, such as "vintage graphic tee under $30, size M", and the agent searches the listings, picks the best match, suggests one or two outfits that pair it with the user's wardrobe, and writes a short social-post caption for the find. If nothing matches, the agent stops early and returns a message naming what the user could change (the price limit, the size, or the keywords) instead of calling the model with nothing.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches the listings in `data/listings.json` and returns the 
items that match the user's description, optionally filtered by size and a price 
ceiling.
- **Inputs:**
  - `description` (str): keywords for what the user wants, e.g. `"vintage graphic tee"`. 
  Matched case-insensitively by keyword overlap; items with zero overlap are dropped.
  - `size` (str or None): a size to filter by, or `None` to skip. Matching is case-
  insensitive and token-based, not substring: the listing's size is split on `/` with 
  parentheticals removed, so `"M"` matches `"S/M"` but `"S"` does not match `"US 9"` 
  and `"L"` does not match `"XL"`. Listings marked "One Size" match any requested size.
  - `max_price` (float or None): maximum price, inclusive, or `None` to skip.
- **Returns:** A list of listing dicts, best match first (highest keyword score), 
capped at `config.SEARCH_RESULT_LIMIT`. Each dict has `id` (str), `title` (str), 
`description` (str), `category` (str), `style_tags` (list of str), `size` (str), 
`condition` (str), `price` (float), `colors` (list of str), `brand` (str or None; 
None for most listings), and `platform` (str).
- **When it has nothing:** Returns an empty list `[]`. Never `None`, never an exception.

### `suggest_outfit`
 
- **What it does:** Suggests one or two outfits that pair a thrifted item with pieces 
from the user's wardrobe, using the model.
- **Inputs:**
  - `new_item` (dict): a listing dict (the fields above) for the item being considered.
  - `wardrobe` (dict): a dict with an `items` key holding a list of wardrobe items. The 
  list may be empty.
- **Returns:** A non-empty string with one or two outfit suggestions. When the wardrobe has 
items, the suggestions name specific pieces the user already owns. When `wardrobe["items"]` 
is empty, it returns general styling advice for the item instead.
- **When it has nothing:** An empty wardrobe is not an error: it returns general styling 
advice as a non-empty string. It never raises and never returns `""`.

### `create_fit_card`
 
- **What it does:** Writes a short, social-post-style caption about the find, using 
the model.
- **Inputs:**
  - `outfit` (str): the outfit suggestion string returned by `suggest_outfit`.
  - `new_item` (dict): the listing dict for the item.
- **Returns:** A string of two to four sentences that reads like a real post rather 
than a product description. It mentions the item, its price (formatted like `$38.00`), and its platform once 
each, and is specific about the vibe.
- **When it has nothing:** If `outfit` is empty or whitespace-only, it skips the model 
call and returns a descriptive message string (e.g. explaining that an outfit is needed 
to write a caption). It never raises.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in 
`session["error"]` that tells the user what they could change (loosen the price, 
drop the size, or use broader keywords), return the session, and do not call 
`suggest_outfit` or `create_fit_card`. Otherwise, take the first result, store 
it in `session["selected_item"]`, and go on to `suggest_outfit`, then 
`create_fit_card` with its output.
 
**Where it lives:** `agent.py::run_agent`
 
**How the query is parsed:** With regular expressions (no model call), in the helper 
`agent.py::_parse_query`, which `run_agent` calls and whose result is stored in 
`session["parsed"]`. Three patterns run over the lowercased query:
- `max_price`: a price phrase such as `under $30`, `below 30`, `less than $25`, 
`up to $40`, or a bare `$30`. The number becomes a float. If no price is found, 
`max_price` is `None`.
- `size`: the word `size` followed by a token, such as `size M`, `size XXS`, or 
`size S/M`. The token is uppercased. If no `size ...` phrase is found, `size` 
is `None`. A bare "M" with no word "size" in front of it is not detected.
- `description`: whatever remains after the price and size phrases are removed 
and extra punctuation and whitespace are cleaned up. For example, 
`"vintage graphic tee under $30, size M"` becomes description 
`"vintage graphic tee"`, size `"M"`, max_price `30.0`.

**What moves through the session:** Fields are filled in this order, and each 
tool reads its input back out of the session rather than from a local variable:
1. `query`: the user's raw text, set when the session is created.
2. `parsed`: the `description`, `size`, and `max_price` pulled out by the regexes.
3. `search_results`: the full list returned by `search_listings`, stored even 
when it is empty. **The branch checks this field.** If it is empty, `error` is 
set as well and the run ends.
4. `selected_item`: the first search result.
5. `outfit_suggestion`: the string returned by `suggest_outfit` (uses `selected_item` 
and `wardrobe`).
6. `fit_card`: the caption returned by `create_fit_card` (uses `outfit_suggestion` 
and `selected_item`).
7. `error`: stays `None` on a full run. On the empty-search path it holds the message, 
and `outfit_suggestion` and `fit_card` stay `None`.

`wardrobe` is set at the start and only read. The loop also calls 
`trace.check_iterations(count)` on each pass so it stops at `config.MAX_ITERATIONS`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

Outfit:   Hey gorgeous! That butterfly tee is going to look so cute in your collection. For a classic casual vibe, style it with your baggy straight-leg jeans, dark wash and chunky white sneakers. Layer on your vintage black denim jacket for that cool Y2K edge. Or, try tucking it into your wide-leg khaki trousers and pair with your black combat boots for a sweet mix of textures.

Fit card: Scored this Y2K Baby Tee — Butterfly Print for just $18.00 on depop and I am completely obsessed with the nostalgic vibe. I cannot wait to wear it with baggy jeans and chunky sneakers for an effortless weekend look. It also looks so cute tucked into wide-leg trousers with combat boots for that perfect mix of sweet and edgy textures.

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[
 {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'},
 {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'},
 {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'},
 {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'},
 {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'},
 {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}
]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"

Pair your new Vintage Levi's 501 Jeans with the white ribbed tank top for a timeless, effortless base. Layer the slightly cropped vintage black denim jacket on top and finish the look with your chunky white sneakers for a fresh, casual streetwear vibe. For another great option, tuck the white ribbed tank top into the jeans, cinch them with the brown leather belt, and pull on your black combat boots to give the classic denim an edgy, downtown finish.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"

The hunt for the ultimate everyday denim is officially over thanks to these Vintage Levi's 501 Jeans — Medium Wash. I threw them on with my favorite white sneakers and the fit is honestly unreal for casual off-duty days. Snagging them for only $38.00 feels like an absolute steal. I just listed them on depop so someone else can give them a good home.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I gave Claude the `create_fit_card` docstring and asked it to write the function.
- *What came back:* A working function with a guard for a blank `outfit` and a prompt that tells the model to use the listing's real price and platform. When I ran it on the Levi's jeans, though, the caption was written as a seller: it said I had listed the jeans on depop and was clearing out my wardrobe. Nothing in the prompt said who was speaking. The price also printed as `$38.0`.
- *What I changed:* I added a line saying the person just found the item secondhand and the caption is from the buyer's point of view, and a rule not to open with a greeting. I switched the price to two decimals (`$38.00`) and rewrote criterion 4 to say so, since "the format used in the data" no longer matched. The rerun is better, but the sample caption above still ends with a sentence about listing the item on depop, so the prompt only partly fixed it. In unit 4's before and after runs, none of the 90 fit cards contained seller phrases like "listed them", "clearing", "selling", "listing it", or "good home", so the
buyer's-voice line appears to have held. That was a search for those five phrases, not a full read of every card.

**Moment 2**

- *What I asked for:* I asked Claude to help me build `run_agent` following my branch rule. After working through the regex approach with it, I asked for the parser code itself.
- *What came back:* Two helper functions for `agent.py`, plus the loop. `_parse_query` uses regexes to pull `description`, `size`, and `max_price` out of the query. `_no_results_message` builds the empty-search message from what the user actually asked for, so it only suggests raising the price limit if a price was set and only suggests changing the size if a size was set. `run_agent` calls both, and every tool call reads its input from the session.
- *What I changed:* I tested `_parse_query` on its own before connecting it, on six queries including one with no price or size and a bare `$20 sweater`. All six came out as expected. Then I ran both paths through `run_agent`: the happy path completed all three tools, and `selected_item` and `search_results[0]` were the same item (`lst_002`). The ballgown query stopped before `suggest_outfit`, left `fit_card` as `None`, and returned a message naming the price and size. I also updated the Planning Loop section so it says parsing lives in `_parse_query`, not inline in `run_agent`.

**Moment 3 (unit 4)**

- *What I asked for:* I pasted my `run_agent` after wiring in the MCP call and asked
  Claude what to fix.
- *What came back:* Three problems. The import pointed at `mcp_server` instead of
  `mcp_client`, and `parsed` was undefined because its line was commented out. The
  third was quieter: `results = session["search_results"]` ran before
  `results = call_tool(...)`, so the session kept the empty list from `new_session`
  while the local variable held the real results. The run looked fine because the
  rest of the code used the local variable.
- *What I changed:* I fixed the import, uncommented `parsed`, and assigned
  `session["search_results"] = call_tool(...)` first, with `results` as an alias
  afterwards. I checked it with a one-liner printing `len(session["search_results"])`
  and the selected id. It printed `10 lst_002`, where the bug would have shown 0.

**Moment 4 (unit 4)**

- *What I asked for:* Help fixing the greeting defect from my diagnosis, then I
  pasted my edited prompts.
- *What came back:* Claude suggested a positive instruction about how to begin
  instead of repeating "no greetings". It also spotted that I'd put the new line in
  the empty-wardrobe prompt, which was my control, not the wardrobe prompt, and that
  a stray fourth quote mark would have been a `SyntaxError`.
- *What I changed:* I moved the sentence to the wardrobe prompt, fixed the quotes,
  and wrote my threshold (5 of 35 or fewer) before running. Greetings went from 16
  of 35 to 0 of 35. All 35 outfits now start with "Pair", because the model took the
  first example verb literally.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item in the session matches the item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: 2-4 sentences, exact $xx.xx price, platform | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Empty wardrobe still completes with advice and a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Source for all blocks: `results/run_2026-10-10_2149_before.md`, written by
`run_eval.py::main`. Each try ran `agent.py::run_agent`; the trace lines come
from its `trace.step()` calls, and the fit card text from `tools.py::create_fit_card`.

**Criterion 1: matching query completes (try 1)**

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 match(es)
[3] selected_item
      out: id=lst_002 Y2K Baby Tee — Butterfly Print
[4] suggest_outfit
      in:  id=lst_002 Y2K Baby Tee — Butterfly Print
      out: You are going to look so cute in that baby tee! Pair it with your baggy straight-leg jeans, dark wash and step…
[5] create_fit_card
      in:  id=lst_002 Y2K Baby Tee — Butterfly Print
      out: Found this absolute dream of a Y2K Baby Tee — Butterfly Print while scrolling on depop and I am obsessed. It w…
```

**Criterion 2: impossible query stops early (try 1)**

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

stopped early: yes — No listings matched 'designer ballgown'. Try to raise your price limit above $5.00, or drop or change the size (XXS), or use broader keywords.
```

**Criterion 3: same item reaches both tools (try 1, query `graphic hoodie`)**

```
[3] selected_item
      out: id=lst_015 Vintage Graphic Hoodie — Faded Black
[4] suggest_outfit
      in:  id=lst_015 Vintage Graphic Hoodie — Faded Black
[5] create_fit_card
      in:  id=lst_015 Vintage Graphic Hoodie — Faded Black
```

**Criterion 4: fit card format (try 1 of row 4: the Levi's jeans scenario)**

```
Finally scored the holy grail vintage Levi's 501 jeans on depop for just $38.00 and I am honestly never taking them off. They have that exact broken-in medium wash I have been hunting for forever. Already planning to wear them tucked into my favorite white tank with chunky sneakers today and then switch to an oversized crewneck and combat boots tomorrow.
```

Checked with `check_cards.py`: 3 sentences, price `$38.00` present, platform `depop` present.

**Criterion 5: empty wardrobe completes (try 1, query `denim jacket under $50`)**

```
Outfit suggestion:
A light wash cropped denim jacket is such a versatile staple for your wardrobe. For an easy everyday streetwear look, throw it on over a slip dress and pair it with chunky platform sneakers. If you want a more vintage vibe, layer it with a graphic tee and high waisted wide leg trousers, finishing the outfit with some retro canvas sneakers.

Fit card:
I finally tracked down this Denim Jacket — Light Wash, Cropped on poshmark for $42.00 and I am already obsessed with it. I cannot wait to throw it on over a slip dress with chunky platform sneakers for an easy everyday streetwear look. It is seriously going to be my most worn piece this season.
```

Note: in the denim jacket query, try 5 of both denim scenarios wrote the price in words ("forty two dollars" and "forty-two dollars") instead of `$42.00`. That doesn't change any verdict, because criterion 4's five listings all passed and criterion 5 doesn't check the price format. I'm keeping it as a finding for the diagnosis.

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries ran all five trace steps and produced a fit card. None contained a fallback phrase. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five traces end at `branch`, with no `suggest_outfit` step and a message naming the price, size, and keywords. |
| 3 | The item in the session matches the item passed on | 5 of 5 | MET (5/5) | In all five tries, `id=lst_015` is on the selected-item, `suggest_outfit`, and `create_fit_card` lines. |
| 4 | Fit card: 2-4 sentences, exact $xx.xx price, platform | 4 of 5 | MET (5/5) | The first run of each of the five fit-card scenarios had 2 to 4 sentences, the exact price, and the platform (checked with `check_cards.py`). |
| 5 | Empty wardrobe still completes with advice and a fit card | 4 of 5 | MET (5/5) | All five tries completed with an outfit and a fit card, and none contained a fallback phrase. |

**Diagnoses**

I missed no criterion, so there is no miss to diagnose. I'd rather be honest about how much that says.

*How strong the tests were.* Criterion 3 is the weakest. The id printed in the trace comes from the same `item` variable that is passed to the tool, so the two can't disagree unless the trace line itself is edited. It measures the log, not what the tool received, and a wiring bug elsewhere would still pass. If I tightened one criterion, it would be this one: have `suggest_outfit` itself record the `id` it received and compare that with the session. Criterion 4's target of 4 of 5 was lower than the agent's behavior: all 45 fit cards in the run had 2 to 4 sentences, so the sentence-count slip I predicted never happened. Criterion 1 ran one query five times, so it never tested the reason I gave for allowing a miss (some phrasings won't match). Criterion 2 ran one impossible query through plain code, so all five tries were identical by construction.

*What the outputs show beyond the five criteria.* Reading all 45 tries turned up two defects. I think they are one pattern.

1. **Greetings in outfit text (the model's output).** 16 of 35 outfits for the example wardrobe opened with a greeting such as "Hey babe" or "Hey bestie". 0 of 10 for the empty wardrobe did. Both prompts say "no greetings", so the model ignored an explicit instruction, and mostly in one prompt. My hypothesis, not tested: the wardrobe prompt lists pieces the customer owns and calls them "the customer", which may invite a chatty "Hey babe, you need these" voice that the general prompt doesn't.
2. **The price written in words (the model's output).** 2 of 45 fit cards wrote "forty two dollars" and "forty-two dollars" instead of `$42.00`. Both were try 5 of the denim jacket query. The prompt says to use the price exactly as written, but the code never checks that the reply contains it. `create_fit_card` only substitutes its fallback when the reply is blank. This didn't change a verdict, because the denim query sits under criterion 5, which doesn't check price format, and criterion 4's five listings all passed.

*Pattern.* Both defects are the model not following an instruction in its own output, and the code has nothing behind the prompt to catch it. The tools and the loop's branch worked, and the session held the right item every time. The weak point is trusting the model's reply, not any step in my code.


---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
     in:  vintage graphic tee under $30
     out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
     in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
     out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
     →    10 match(es)
[3] selected_item
     out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
     in:  id=lst_002 Y2K Baby Tee — Butterfly Print
     out: Hey gorgeous! That butterfly tee is going to look so cute in your collection. For a classic casual vibe, style…
[5] create_fit_card
     in:  id=lst_002 Y2K Baby Tee — Butterfly Print
     out: Scored this Y2K Baby Tee — Butterfly Print for just $18.00 on depop and I am completely obsessed with the nost…
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5'
[1] parse_query
     in:  designer ballgown size XXS under $5
     out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
     in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
     out: [] (empty)
     →    0 match(es)
[3] branch
     →    search returned []: stopping before suggest_outfit

No listings matched 'designer ballgown'. Try to raise your price limit above $5.00, or drop or change the size (XXS), or use broader keywords.
```

**Model unavailable (bad key, extra)**

```
$ AI201_CACHE=0 python app.py ask 'braided leather belt under $20'
[1] parse_query
     in:  braided leather belt under $20
     out: {'description': 'braided leather belt', 'size': None, 'max_price': 20.0}
[2] search_listings (via MCP)
     in:  {'description': 'braided leather belt', 'size': None, 'max_price': 20.0}
     out: 1 items: Leather Belt — Brown, Braided
     →    1 match(es)
[3] selected_item
     out: Leather Belt — Brown, Braided ($12.0, thredUp)
[4] model unavailable
     →    model call failed: stopping, no outfit or fit card

I found Leather Belt — Brown, Braided ($12.00 on thredUp), but couldn't reach the model to write the outfit and caption. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. Once that's fixed, run the same query again.
```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->
In `run_agent`, I replaced the direct call `search_listings(description, size, max_price)` with `call_tool("search_listings", {...})`, imported from `mcp_client.py`. I registered the same function in `mcp_server.py` with typed inputs matching my Tool Inventory. Nothing behaved differently afterwards. The call returned the same list of listing dicts, and the tee query still selected `lst_002` first, as it did with the direct call. The empty search came back as `[]`, not `None`, so the branch still fired and stopped before `suggest_outfit`. The only visible change is the trace line, which now reads `search_listings (via MCP)`.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** In `tools.py::suggest_outfit`, I added one sentence to the
wardrobe prompt (the `else` branch only): "Start the first sentence with a verb
such as 'Pair' or 'Layer'." The line before it already said "no greetings", and I
left that in. I did not touch the empty-wardrobe prompt, so it acted as a control.

**Which failure it was meant to fix:** Greetings in the outfit text (the model's
output). In the before run, 16 of 35 outfits for the example wardrobe opened with
a greeting such as "Hey babe", against 0 of 10 for the empty wardrobe. Both
prompts said "no greetings", so the model ignored an explicit instruction, mostly
in the wardrobe prompt.

**Threshold, set before the after run:** I will call this change helped if
example-wardrobe greetings drop from 16 of 35 to 5 of 35 or fewer, and
empty-wardrobe greetings stay at 0 of 10. A greeting means the outfit starts with
`hey`, `hi`, `hello`, or `yo`. 6 to 9 would be partial or inconclusive, and 10 or
more would be no clear effect.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item in the session matches the item passed on | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: 2-4 sentences, exact $xx.xx price, platform | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Empty wardrobe still completes with advice and a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

| Count over the whole run | Before | After |
|---|---|---|
| Example-wardrobe outfits opening with a greeting | 16 of 35 | 0 of 35 |
| Empty-wardrobe outfits opening with a greeting (control) | 0 of 10 | 0 of 10 |
| Example-wardrobe outfits starting with "Pair" | 7 of 35 | 35 of 35 |
| Fit cards missing the exact price | 2 of 45 | 1 of 45 |
| Fit cards outside 2-4 sentences | 0 of 45 | 0 of 45 |
| Fallback sentences used | 0 | 0 |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->
Yes, on the failure I targeted, with a side effect. I set the threshold before the
run: helped if example-wardrobe greetings dropped from 16 of 35 to 5 of 35 or fewer,
with the empty wardrobe staying at 0 of 10. After the change, greetings were 0 of 35
and the empty wardrobe stayed at 0 of 10 (counts from `compare_runs.py`, same rule
as before: the outfit starts with hey, hi, hello, or yo). All five criteria were MET
again, so nothing regressed. The prompt already said "no greetings" before and the
model ignored it, so a concrete instruction about how to begin worked where a ban did
not. The side effect: all 35 example-wardrobe outfits now start with "Pair", where
before the openers varied. The model most likely took my first example verb too
literally, so I traded one defect for a uniform opener. This does not test my other
hypothesis, that the persona and the owned-item list invite the chatty voice, because
I changed neither. The price written in words ("forty two dollars") is not fixed: it
appeared in 1 of 45 cards after the change and 2 of 45 before, both on the denim
jacket query, and that difference is not from this edit.


---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->
No criterion was missed in either run, so nothing below is a missed target. These
are problems I found that the five criteria don't catch.

- **Every example-wardrobe outfit now starts with "Pair."** 35 of 35, up from 7 of
  35. I'd ask for a verb without naming one, or list several verbs, then re-count
  the openers. I stopped because the milestone allows one change and I'd already
  made mine.
- **The price sometimes comes out in words** ("forty two dollars"): 2 of 45 cards
  before, 1 of 45 after, both on the denim jacket query. `create_fit_card` only
  falls back on a blank reply and never checks that the exact `$xx.xx` is in it. I'd
  add that check with one retry. I didn't, because at about 4% a single re-run
  couldn't show whether it worked.
- **Criterion 3 measures the log, not what the tool received.** The id in the trace
  comes from the same variable that's passed to the tool, so they can't disagree. To
  tighten it, I'd record the id inside `suggest_outfit` and compare that with the
  session.
- **Criteria 1 and 2 each ran one query.** Criterion 1 never tested the phrasing
  misses that justified its 4 of 5 (plurals, a size, "levis" without the
  apostrophe). Criterion 2 tried one impossible query. I'd add more phrasings to
  `scenarios.py`.
- **A failed MCP call isn't handled.** Only the two model steps are inside
  `try/except ModelUnavailable`. If `mcp_server.py` can't start, `call_tool` raises
  `MCPError` from the search step and the user sees a stack trace. I'd wrap that
  call and put a message in `session["error"]`. I only triggered the three failures
  the milestone named.
- **Rate-limit exhaustion isn't handled.** After five retries `generate()` raises
  `RuntimeError`, which my handler doesn't catch.
- **Only `search_listings` is on MCP.** The two model tools are still direct calls,
  which is what the milestone asked for. Moving them would reset `generate.py`'s
  pacing counters on every call, because each call starts a fresh server process.
- **Query parsing has limits:** a bare "M" without the word "size" isn't detected,
  `size US 9` captures only `US`, and `W30 L30` only matches as the full string.

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**


---

### Capstone

**What This Extends**

FitFindr, my thrifting agent from units 3 and 4: the planning loop in `agent.py::run_agent`, the three tools, and `search_listings` called through MCP. What is new is a failure-handling layer around that loop, so that a failure in the MCP search step or in the model steps ends the run with a clear message and a log record instead of a stack trace.

**The Shape**

Shape B, harden against failure. Today `run_agent` handles an empty search and `ModelUnavailable` (a bad API key). Two other failures I found in unit 4 and left unfixed: if `mcp_server.py` cannot start, `call_tool` raises `MCPError` from the search step and the user sees a stack trace, and when the model's rate limit is used up, `generate()` raises a `RuntimeError` after five retries that my handler doesn't catch. I am adding one layer in `run_agent` that catches these, puts an actionable message in `session["error"]`, stops the run cleanly, and records the failure. The run path (Path B, local) and the structured log are required in every shape, so I am building them alongside it.

Out of scope:
- I am not moving `suggest_outfit` or `create_fit_card` onto MCP. Each MCP call starts a fresh server process, which would reset the pacing counters in `generate.py`.
- I am not changing the prompts: no fix for the "Pair" openers and no price-in-words check or retry.
- I am not touching `_parse_query` or its limits (bare "M", `size US 9`, `W30 L30`).

**Running It**

Path B, local with logs. I did not try to host it. The service runs on my machine from one command, `PORT=5001 python serve.py` (macOS reserves port 5000 for AirPlay Receiver, so I use 5001). The exact command, the environment it needs and a test request are in [RUNNING.md](RUNNING.md). It only calls the Gemini API and loads no local model, so there are no model files to download.

**Instrumentation**

Every request to `/ask` writes one JSON line to `logs/runs.jsonl`, written by `serve.py::log_run` (and echoed to the console). What each record holds:

- `completed` and `stopped` records: `timestamp` (UTC), `status`, `query`, `selected_id`, `output` (the fit card, or null), `error` (the user-facing message, or null), `model_calls`, `prompt_tokens`, `output_tokens`, and `seconds` (time inside `run_agent`, measured with `time.perf_counter()` while holding the lock). `completed` means the fit card was written. `stopped` means `run_agent` returned with `session["error"]` set, which covers an empty search, an unreachable MCP server, a bad key and an exhausted rate limit.
- `rejected` records (a request with no query, answered with a 400): `timestamp`, `status` and `error` only. No query was sent, so there is none to record.
- `crashed` records (an exception escaped `run_agent`, answered with a 500): `timestamp`, `status`, `query`, `error` as `ExceptionType: message`, and `seconds`. No `crashed` record appeared in any run.

`model_calls` and the token counts are the difference in `generate.py`'s module counters before and after the run. That is only accurate because `serve.py` runs one request at a time.

Two limits of this log. All handled failures are logged as `stopped`, so the log alone cannot say whether a stopped run was an empty search, an MCP failure or a rate limit without reading `error` (there is no `error_type` field). And the log stores the user-facing message, not the exception text: the MCP exception text (`unhandled errors in a TaskGroup`) only appears in the trace.

An earlier version of my instrumentation was itself a failure shown only as an absence. I imported the `generate()` function instead of the `generate` module in `serve.py`, so reading the call counters raised an `AttributeError` before the `try` block. Two requests returned a 500 and wrote no log record at all. I found it from the server's traceback, not from the log.

Ten entries from `logs/runs.jsonl` (uncached runs, `AI201_CACHE=0`; the first line of the file, a cache hit with zero tokens, is left out):

```
{"timestamp": "2026-11-16T06:39:20+00:00", "status": "completed", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": "I still cannot believe I scored this Y2K Baby Tee — Butterfly Print for only $18.00 on depop. It instantly unlocked the ultimate off duty model nostalgia. I am so ready to live in this look all season long.", "error": null, "model_calls": 2, "prompt_tokens": 553, "output_tokens": 100, "seconds": 3.31}
{"timestamp": "2026-11-16T06:39:23+00:00", "status": "completed", "query": "90s track jacket in size M", "selected_id": "lst_004", "output": "Scored this amazing 90s Track Jacket — Navy/White Stripe on poshmark for only $45.00 and I am already obsessed. It gives off the absolute best effortless nineties streetwear vibe whether I throw it over a simple tank or layer it up. Can't wait to wear this piece on repeat all season long.", "error": null, "model_calls": 2, "prompt_tokens": 579, "output_tokens": 141, "seconds": 2.24}
{"timestamp": "2026-11-16T06:39:25+00:00", "status": "completed", "query": "silk slip dress in midi length under $40", "selected_id": "lst_013", "output": "I am still not over scoring this gorgeous 90s Silk Slip Dress — Floral, Midi Length for just $30.00 while browsing depop. Styling it with an oversized sweatshirt and chunky sneakers gives off the most effortless contrast. Honestly, building out dreamy outfits secondhand is becoming my entire personality.", "error": null, "model_calls": 2, "prompt_tokens": 583, "output_tokens": 131, "seconds": 2.09}
{"timestamp": "2026-11-16T06:39:27+00:00", "status": "completed", "query": "denim jacket under $50", "selected_id": "lst_007", "output": "Finally tracked down the ultimate light wash, cropped Denim Jacket on Poshmark for just $42.00. I am so obsessed with how it looks layered over an oversized grey crewneck and wide-leg khakis for that effortless streetwear vibe. It is honestly the only piece missing from my transitional wardrobe rotation right now.", "error": null, "model_calls": 2, "prompt_tokens": 572, "output_tokens": 141, "seconds": 2.33}
{"timestamp": "2026-11-16T06:40:41+00:00", "status": "completed", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": "I cannot believe I scored this Y2K Baby Tee — Butterfly Print on depop for only $18.00. I am so excited to style it with baggy straight-leg jeans, chunky white sneakers, and a brown leather belt for the ultimate nostalgic look. When it gets chilly, I am just going to throw on my vintage black denim jacket to finish the outfit.", "error": null, "model_calls": 2, "prompt_tokens": 558, "output_tokens": 132, "seconds": 3.35}
{"timestamp": "2026-11-16T06:40:43+00:00", "status": "completed", "query": "90s track jacket in size M", "selected_id": "lst_004", "output": "Just scored this vintage 90s Track Jacket — Navy/White Stripe on Poshmark for $45.00 and I am already obsessed with it. I cannot wait to throw it on over a white ribbed tank with baggy jeans and chunky sneakers for the ultimate effortless sporty vibe. It also looks so good paired with wide-leg trousers and combat boots for a cool streetwear contrast.", "error": null, "model_calls": 2, "prompt_tokens": 584, "output_tokens": 156, "seconds": 2.23}
{"timestamp": "2026-11-16T06:40:46+00:00", "status": "completed", "query": "silk slip dress in midi length under $40", "selected_id": "lst_013", "output": "Stumbled across the ultimate 90s Silk Slip Dress — Floral, Midi Length while scrolling through depop and honestly could not hit buy fast enough for just $30.00. I am so ready to throw an oversized crewneck right over it with chunky sneakers for that effortless grunge look, or lean into total 90s romance with a vintage denim jacket and combat boots. Finding pieces that transition this easily between sweet and edgy is literally the best feeling.", "error": null, "model_calls": 2, "prompt_tokens": 579, "output_tokens": 160, "seconds": 2.96}
{"timestamp": "2026-11-16T06:41:40+00:00", "status": "completed", "query": "denim jacket under $50", "selected_id": "lst_007", "output": "Scored this light wash, cropped Denim Jacket on Poshmark for only $42.00 and I am obsessed. I am already planning to lean into the ultimate double denim look with baggy dark wash jeans or throw it over an oversized crewneck for a grungier streetwear vibe. Finding pieces this versatile secondhand is honestly the best feeling.", "error": null, "model_calls": 2, "prompt_tokens": 566, "output_tokens": 139, "seconds": 43.59}
{"timestamp": "2026-11-16T06:39:25+00:00", "status": "stopped", "query": "platform sneakers size 8", "selected_id": null, "output": null, "error": "No listings matched 'platform sneakers'. Try to drop or change the size (8), or use broader keywords.", "model_calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.44}
{"timestamp": "2026-11-16T06:42:03+00:00", "status": "stopped", "query": "designer ballgown size XXS under $5", "selected_id": null, "output": null, "error": "No listings matched 'designer ballgown'. Try to raise your price limit above $5.00, or drop or change the size (XXS), or use broader keywords.", "model_calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.55}
```

The 43.59 second entry (the eighth line) is an outlier: every other uncached run took between 1.99 and 3.35 seconds. I did not capture the console output for that request, so I cannot confirm why. A real rate-limit pushback with a retry wait, like the one I saw later in trial 2 of the test, would produce this shape.

Failed runs. A rejected request (no query in the body, answered with a 400), from the real server:

```
{"timestamp": "2026-11-16T06:38:05+00:00", "status": "rejected", "error": "no query in the request body"}
```

Two simulated failures from capstone trial 1 (`results/capstone_trial_1_log.jsonl`, written by `serve.py::log_run` while `capstone_eval.py` injected the fault). The first is an MCP search failure and the second a rate limit that ran out of retries. In the second, `seconds` is 0.45 because the harness records the retry sleeps without performing them, so it does not show how long a user would really wait (see criterion 2):

```
{"timestamp": "2026-11-16T07:17:43+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": null, "output": null, "error": "I couldn't reach the search service, so I haven't looked for listings yet. That's a problem on my side, not with your query. Run the same query again, and if it keeps happening, check that `python mcp_server.py` starts.", "model_calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.43}
{"timestamp": "2026-11-16T07:17:46+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": null, "error": "I found Y2K Baby Tee — Butterfly Print ($18.00 on depop), but the model's rate limit ran out before I could write the outfit and caption. Wait about a minute and run the same query again.", "model_calls": 5, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.45}
```

**What It Costs**

Measured per run, averaged over 15 uncached runs of `serve.py`: **573.0 prompt tokens + 138.1 output tokens = 711.1 tokens, 2 model calls, and 5.27 seconds (median 2.41 seconds).** The mean is pulled up by the one 43.59 second run; the other 14 took between 1.99 and 3.35 seconds.

How I measured it: I started `AI201_CACHE=0 PORT=5001 python serve.py`, sent requests with `curl` in two batches (five queries per batch), and read the `model_calls`, token and `seconds` fields from `logs/runs.jsonl`. I kept every entry with `model_calls` above 0, which gave 15 runs. The `platform sneakers size 8` query matches no listing, makes no model call, and is excluded. The token counts are the service's own counter in `generate.py`, not an estimate from the pricing page. It counts only the candidate (output) tokens the service reports, so if the model also bills hidden thinking tokens they are not in my numbers.

The dollar figure uses list prices, which are not something I measured. `gemini-3.5-flash-lite` is listed at $0.30 per million input tokens and $2.50 per million output tokens (Google's Gemini API pricing page, ai.google.dev/gemini-api/docs/pricing; TODO: check these two rates on that page before submitting).

```
input:   573.0 tokens x $0.30 / 1,000,000 = $0.000172
output:  138.1 tokens x $2.50 / 1,000,000 = $0.000345
one run                                   = $0.000517  (about $0.0005)

100 people a day, one request each:
  tokens:   100 x 711.1 = 71,110 tokens a day
  dollars:  100 x $0.000517 = $0.052 a day  (about $1.55 over 30 days)
  compute:  100 x 5.27 s = 527 s a day, about 9 minutes
            (100 x 2.41 s = 241 s, about 4 minutes, using the median)
```

Caveats: this assumes one request per person per day and only queries that find a listing (an empty search costs nothing), the sample was five queries, and if my key is on Google's free tier the real spend was $0, so the dollar figure is what it would cost at list price. Because `serve.py` handles one request at a time, those compute seconds run back to back.

**Run Log and Verdicts**

Five criteria, three trials each. Each trial is a separate run of `python capstone_eval.py N` (N = 1, 2, 3) with nothing changed in between, and the table is the output of `python capstone_eval.py --summary`. Every request goes through the real `serve.py::ask` route using Flask's test client, and the real `serve.py::log_run` writes the log, redirected to `results/capstone_trial_N_log.jsonl`. The criteria were committed before any result (commit `add capstone criteria`).

How the failures were triggered: an empty body, the real MCP client asking the real server for a tool that does not exist (`search_listingz`), and a fake model client that answers "API key not valid" or "429 ... retry in 29.7s". The fake client sits at the API boundary, so the real `generate()` retry loop and the real handlers run. The retry sleeps are recorded, not performed. Because these faults are deterministic, criteria 1, 2, 3 and 5 came out identical in all three trials by construction. Criterion 4 uses the live model.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Every failing request leaves exactly one log record | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 2. Rate-limit retry waits total 30 s or less | 2 of 2 | 0/2 | 0/2 | 0/2 | MISSED |
| 3. Failure message is true to the session | 5 of 5 | 3/5 | 3/5 | 3/5 | MISSED |
| 4. Original behaviour still works | 5/5 + 1/1 | 6/6 | 6/6 | 6/6 | MET |
| 5. No failing request ends in a crash | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |

**Real output from one trial.** All blocks are from trial 1 unless marked. Produced by `capstone_eval.py::run_trial`, which calls `serve.py::ask`; log lines are written by `serve.py::log_run`.

Criterion 1: the 10 failing requests each added one record. Four of the ten records (an empty body, an MCP failure, a bad key, a rate limit):

```
{"timestamp": "2026-11-16T07:17:43+00:00", "status": "rejected", "error": "no query in the request body"}
{"timestamp": "2026-11-16T07:17:43+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": null, "output": null, "error": "I couldn't reach the search service, so I haven't looked for listings yet. That's a problem on my side, not with your query. Run the same query again, and if it keeps happening, check that `python mcp_server.py` starts.", "model_calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.43}
{"timestamp": "2026-11-16T07:17:45+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": null, "error": "I found Y2K Baby Tee — Butterfly Print ($18.00 on depop), but couldn't reach the model to write the outfit and caption. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. Once that's fixed, run the same query again.", "model_calls": 1, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.47}
{"timestamp": "2026-11-16T07:17:46+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": null, "error": "I found Y2K Baby Tee — Butterfly Print ($18.00 on depop), but the model's rate limit ran out before I could write the outfit and caption. Wait about a minute and run the same query again.", "model_calls": 5, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.45}
```

Criterion 2: the retry waits that `generate.py::generate` asked for in the two rate-limit requests (trial 1 console output):

```
Criterion 2, retry waits requested (seconds):
  [30.7, 30.7, 30.7, 30.7, 30.7] -> total 153.5
  [30.7, 30.7, 30.7, 30.7, 30.7] -> total 153.5
```

And one real rate-limit pushback from Gemini during trial 2's live run of criterion 4 (console output and the log record, from `generate.py::generate` and `serve.py::log_run`):

```
  [rate limit] service pushed back. Waiting 38s (attempt 1 of 5). This is the limiter doing its job, not a bug.
{"timestamp": "2026-11-16T07:19:02+00:00", "status": "completed", "query": "silk slip dress in midi length under $40", "selected_id": "lst_013", "output": "Still can't believe I scored this 90s Silk Slip Dress — Floral, Midi Length on depop for just $30.00. I am so obsessed with layering it over a basic tee with sneakers for that effortless model off duty look, or throwing a chunky sweater over top with combat boots. It is seriously the ultimate versatile wardrobe staple for every season.", "error": null, "model_calls": 3, "prompt_tokens": 577, "output_tokens": 139, "seconds": 40.04}
```

Criterion 3: the message check for the five situations (`capstone_eval.py::_message_problems`), and the trace and log record for the fit-card-only rate limit (`agent.py::run_agent`, `serve.py::log_run`):

```
Criterion 3, message problems:
  mcp_down     OK
  rate_outfit  OK
  rate_card    PROBLEM: message says the outfit was not written, but outfit_suggestion is set
  key_outfit   OK
  key_card     PROBLEM: message says the outfit was not written, but outfit_suggestion is set
```

```
[4] suggest_outfit
      in:  id=lst_002 Y2K Baby Tee — Butterfly Print
      out: Pair it with baggy jeans.
  [rate limit] service pushed back. Waiting 31s (attempt 1 of 5). This is the limiter doing its job, not a bug.
  [rate limit] service pushed back. Waiting 31s (attempt 2 of 5). This is the limiter doing its job, not a bug.
  [rate limit] service pushed back. Waiting 31s (attempt 3 of 5). This is the limiter doing its job, not a bug.
  [rate limit] service pushed back. Waiting 31s (attempt 4 of 5). This is the limiter doing its job, not a bug.
  [rate limit] service pushed back. Waiting 31s (attempt 5 of 5). This is the limiter doing its job, not a bug.
[5] model rate limited
      →    retries exhausted: stopping, no outfit or fit card
{"timestamp": "2026-11-16T07:17:48+00:00", "status": "stopped", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": null, "error": "I found Y2K Baby Tee — Butterfly Print ($18.00 on depop), but the model's rate limit ran out before I could write the outfit and caption. Wait about a minute and run the same query again.", "model_calls": 6, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.46}
```

Criterion 4: one live matching query and the empty search (the other four matching queries also completed; see `results/capstone_trial_1.json`):

```
{"timestamp": "2026-11-16T07:17:34+00:00", "status": "completed", "query": "vintage graphic tee under $30", "selected_id": "lst_002", "output": "I am still not over scoring this Y2K Baby Tee — Butterfly Print for only $18.00 on depop. It is giving major nostalgic energy, especially when I pair it with baggy straight-leg jeans and a vintage black denim jacket. Honestly, finding pieces this good secondhand completely makes my week.", "error": null, "model_calls": 2, "prompt_tokens": 573, "output_tokens": 134, "seconds": 3.03}
{"timestamp": "2026-11-16T07:17:43+00:00", "status": "stopped", "query": "designer ballgown size XXS under $5", "selected_id": null, "output": null, "error": "No listings matched 'designer ballgown'. Try to raise your price limit above $5.00, or drop or change the size (XXS), or use broader keywords.", "model_calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.46}
```

Criterion 5: HTTP status of each of the 10 failing requests in trial 1, from `results/capstone_trial_1.json`.

```
TODO: run this and paste its output here:
python -c "import json; d=json.load(open('results/capstone_trial_1.json')); [print(r['kind'], r['status']) for r in d['failures']]"
```

**Verdicts and diagnoses**

| # | Verdict | How I decided |
|---|---|---|
| 1 | MET | 10 of 10 requests wrote exactly one record with a non-completed status and a non-empty `error`, in all three trials. |
| 2 | MISSED | 0 of 2 in all three trials: each rate-limit request asked for 153.5 seconds of waiting against a target of 30. |
| 3 | MISSED | 3 of 5 in all three trials: the two fit-card-step situations (`rate_card`, `key_card`) fail the check. |
| 4 | MET | All five matching queries completed with an `error` of null and a non-empty fit card, and the ballgown query stopped with `model_calls` 0, in all three trials. |
| 5 | MET | 10 of 10 in all three trials: no 500, the 8 requests with a query got a 200 with `error` set, and the 2 empty bodies got a 400. |

*Criterion 2 (MISSED, 0 of 2 in every trial).* Stage: the retry loop in `generate.py::generate`, which takes its wait from `_retry_delay`. Mechanism: `_retry_delay` honours the retry hint the service sends (plus one second) and uses it whenever it is larger than the 1-2-4-8-16 backoff, capped at 65 seconds. The loop then sleeps that long before each of its five attempts. With a 29.7 second hint every wait is 30.7 seconds, and five of them make 153.5 seconds. My criterion put 30 seconds on the whole retry sequence, but the wait is per attempt times the number of attempts, and a single wait already exceeds 30 seconds whenever the service's hint is over 29 seconds. This is not only a harness artifact: during the live run in trial 2, Gemini really did push back, asking for a 38 second wait on the first attempt, and that one request took 40.04 seconds even though it then succeeded. The 153.5 seconds is the worst case, where the limit never clears. One limit of my test: the harness records the sleeps instead of performing them, so the `seconds` field in those log entries (0.45) understates what a user would wait, and I did not measure a real 153-second wait.

*Criterion 3 (MISSED, 3 of 5 in every trial).* Stage: the two model handlers (`except ModelUnavailable` and `except RateLimited`) in `agent.py::run_agent`. Mechanism: one `try` block wraps both `suggest_outfit` and `create_fit_card`, and each handler builds its message from fixed text ("to write the outfit and caption") without looking at the session. When the failure happens in `create_fit_card`, the outfit has already been written to `session["outfit_suggestion"]`, so the message says something false, and the trace note ("no outfit or fit card") is false in the same way. The user acts on this message by re-running, and `app.py` prints only the error, so they never see the outfit that exists. The two failures are one problem with two symptoms (a bad key and a rate limit, both at the fit-card step). Limit of my check: `_message_problems` looks for the phrases "write the outfit" and "caption", so it only catches claims it knows about.

*The two misses are different problems.* Criterion 2 is a timing problem in `generate.py`, and criterion 3 is a wording problem in `agent.py`, so this is not one fault with several symptoms.

*Criteria met, and how strong that is.* Criterion 1 passed, but its failing requests are only failures I had already handled. Criterion 5 also passes by construction: the set contains no failure I did not handle, and `QuotaGuard` (the session request budget error in `generate.py`) is still unhandled and not in the set. The fault injection is also narrow: the MCP failure is a missing tool, not a server that crashes or hangs, and the bad key and rate limit come from a fake client, not from Google. Criterion 4 is the only criterion that touched the live model. I did not revise any criterion.

**The Improvement**

TODO: what I changed (one change only), which diagnosis above pointed at it, and the second run log in the same format, side by side with the first table. Run all three trials again after the change.

**What's Still Broken**

TODO: for each criterion still missed after the improvement: what I'd do and why I stopped. Add the one thing I'd do first with another unit.

**How I Used AI**

TODO: two specific moments for this unit: what I asked, what I got, what I changed.