# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search is a plain keyword match and my query parsing is regex, so some phrasings will miss or parse oddly, and two of the three tools call a model that can occasionally fail. I allow one miss but not more, because a query that matches a listing should work most of the time.
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path is a plain `if` on an empty list, and the error message is written by my own code, so no model call can make it fail. Any miss would be a real bug in the branch, not bad luck.
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->

---

## 3. Something about state

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

Given a query that matches at least one listing, the `id` of the item that `suggest_outfit` received (read from the trace) equals the `id` in `session["selected_item"]`, and the same holds for `create_fit_card` — in 5 of 5 tries.

**Why this target:**
Choosing `search_results[0]` and passing it on is plain code with no model and no randomness, so the same query should give the same result every time. A mismatch would be a wiring bug, such as the wrong list index, not an unlucky run.

---

## 4. Something about the fit card

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

Given 5 different matching listings, each fit card has 2 to 4 sentences and contains the listing's price written as a dollar sign plus two decimals (a listing priced 38.0 appears as "$38.00") and the listing's platform name — in 4 of 5 cards.

**Why this target:**
The price and platform come from the prompt, so the model only has to copy them. Sentence count is the likeliest slip because the model follows length instructions loosely and sentences are fuzzy to count, so I allow one miss and will diagnose it.

---

## 5. Your choice

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

Given a query that matches a listing and an empty wardrobe, `run_agent` completes with `session["error"]` as `None` and `session["outfit_suggestion"]` containing non-whitespace text, and the fit card is still produced — in 4 of 5 tries.

**Why this target:**
The empty-wardrobe branch is a plain `if`, but each try makes two model calls that can occasionally fail or return nothing, so I allow one miss. More than one failure would point to a bug in my code, not model flakiness.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
