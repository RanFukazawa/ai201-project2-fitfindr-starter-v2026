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


---

# Capstone criteria

Written for the capstone extension (a failure-handling layer around
`run_agent`) before any capstone results existed.

**The failure set.** Where a criterion says "failing requests", it means these
10 requests to `/ask`, sent in every trial: 2 with an empty body, 3 where the
MCP search server can't be reached, 3 with an invalid API key, and 2 where the
model's rate limit is exhausted (a simulated 429 whose message includes a
"retry in 29.7s" hint, the way Gemini sends one).

---

## 1. Every failing request leaves exactly one log record

In each trial, the 10 failing requests add exactly 10 new lines to
`logs/runs.jsonl`, and every one of those lines has a `status` other than
`completed` and a non-empty `error`. Target: 10 of 10 requests in each of the
3 trials.

**Why this target:**
Earlier in this milestone a bug in my counter code returned a 500 and left no
log entry at all, a failure that existed only as an absence. One missing line
means I can't diagnose that run. The log write is plain code with no model in
it, so I allow no misses, not even one in ten.

---

## 2. Rate-limit exhaustion doesn't keep the user waiting past 30 seconds

For each of the 2 rate-limit requests in a trial, the total time the retry loop
in `generate.py` waits before giving up (the sum of the sleeps it requests) is
30 seconds or less. Target: 2 of 2 in each of the 3 trials.

**Why this target:**
The documented host command, `gunicorn serve:app`, kills a worker after 30
seconds by default, so a longer wait means the user never sees my message.
`generate.py` also honours the service's retry hint (up to 65 s per attempt,
five attempts), so a real rate limit could keep someone waiting minutes. I
picked 30 s because of that worker timeout, not a stricter number, because
some waiting is legitimate: the limit is per minute.

---

## 3. The failure message is true to what is in the session

Across 5 situations (MCP unreachable; rate limit at the outfit step; rate limit
at the fit-card step; invalid key at the outfit step; invalid key at the
fit-card step), the message may say the outfit or caption was not written only
when the matching session field (`outfit_suggestion`, `fit_card`) is `None`,
and may name a listing only when `session["selected_item"]` is set. Target: 5
of 5 situations.

**Why this target:**
The messages are fixed text in my code, with no model involved, so a mismatch
is deterministic and a real bug, not bad luck. There are only five situations,
so allowing one miss would excuse a message that tells the user something
false. A wrong message matters because the user acts on it: if it says nothing
was written when an outfit exists, they re-run and pay for it again.

---

## 4. The original behaviour still works

Five queries that matched in unit 4 (`vintage graphic tee under $30`,
`90s track jacket in size M`, `silk slip dress in midi length under $40`,
`denim jacket under $50`, `graphic hoodie`) each complete with `error` set to
`None` and a non-empty `fit_card`, and `designer ballgown size XXS under $5`
still stops before `suggest_outfit` with `model_calls` 0 in the log. Target: 5
of 5 matching queries and 1 of 1 empty search, in each trial.

**Why this target:**
I changed the code around the search and model calls in `run_agent`, so this
checks that I didn't break what it extends. In unit 4, 45 of 45 matching tries
completed, so a miss would point to my change, not to normal model flakiness.
That is why this target is 5 of 5, not the 4 of 5 I used in unit 3.

---

## 5. No failing request ends in a crash

For each trial's 10 failing requests: none returns HTTP 500, and none lets an
exception propagate out of `run_agent`. The 8 requests that carry a query
return HTTP 200 with `session["error"]` set; the 2 empty-body requests return
400. Target: 10 of 10 requests in each of the 3 trials.

**Why this target:**
Before this unit, an unreachable MCP server and an exhausted rate limit both
ended in a stack trace. Each handler I added is a plain `try/except`, so any
miss is a bug in the handler, not chance. A 500 is the one outcome the user
can do nothing about. A weak point: the set contains only failures I handled,
so passing doesn't mean no crash is possible. `QuotaGuard` in `generate.py` is
still unhandled and isn't in the set.