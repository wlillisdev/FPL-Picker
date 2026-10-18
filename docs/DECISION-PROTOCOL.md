# Decision protocol

Fourteen rules and a pre-deadline checklist. Every gate is a yes/no question
with a stated action on failure. No gate may be skipped, re-ordered, or
overridden by judgement.

This exists because of a specific pattern, not as general advice. Five
decisions in the 2026/27 season went wrong, and in three of them the
disqualifying information was already written down before the decision was
made. The failure was never research. It was that nothing made the research
binding.

| # | Error | Gate that stops it |
|---|---|---|
| 1 | Bought a £8.0m midfielder after noting his club had put 5 of 48 home shots on target. Blanked. | R1, R2 |
| 2 | Bought a £7.9m midfielder after noting "subbed at half-time, seven games in 22 days, rotation is live". Unused substitute, 0 minutes. | R1, R3, R4, R5 |
| 3 | Captained a 14%-owned player over a 74%-owned one on differential logic. Cost 11 points. | R6, R7 |
| 4 | Revised a wildcard squad six times in 24 hours; four of the final fifteen were never verified. | R8, R9 |
| 5 | Priced a squad from blogs rather than the API, twice going over budget. | R10, R11 |

## The fourteen rules

**R1 — The Caveat Veto.** If your own notes contain an unrefuted reason a
player may fail, you may not buy him this gameweek. The caveat must be killed
with a specific dated data point, or the player is dead. Not discounted, not
weighed. Dead.

**R2 — Team-Output Floor.** No attacking buy whose club's shots-on-target
rate in the relevant venue split is below the league median over six games.

**R3 — Half-Time Substitution Disqualifier.** A player substituted at or
before half-time in his most recent competitive start is unbuyable this
gameweek, whatever reason was given for it.

**R4 — Congestion Lock.** If a club has six or more fixtures in 22 days, none
of its players may be bought unless you can cite two instances this season of
that player starting the league game within 72 hours of a European fixture.

**R5 — Premium Nailedness Escalator.** At £7.5m and above the minutes bar
rises to five starts from five and 85% of available minutes. A premium price
buys a nailed role; paying premium for a rotation risk is paying twice.

**R6 — Armband Follows Projection.** The captain is the highest-projected
player you own. The only override is a projected gap under 0.5 points *with*
equal or better minutes security.

**R7 — Ownership Is a Tiebreaker, Never a Reason.** When you own both
players, the field term cancels exactly: captaining A over B is worth
`score(A) - score(B)` regardless of who else owns them. If ownership or the
word "differential" appears in captaincy reasoning before the projection gate
has passed, the decision is void and restarts.

**R8 — Two-Revision Cap.** A wildcard squad gets one draft and at most two
revisions, each requiring new external information. Beyond that, submit the
last fully verified version.

**R9 — 15/15 Verification.** No squad is submitted while any of the fifteen
lacks a written verification record. One unverified player voids the squad.

**R10 — Single Source of Truth.** Prices come only from `bootstrap-static`
(`now_cost / 10`), pulled the same day. Blog, tweet and article prices are
inadmissible. See `tools/fetch_snapshot.py` and `tools/prices.py`.

**R11 — Written Budget Arithmetic.** Post-move bank is computed in writing
before confirming, never eyeballed in the UI.

**R12 — Hit Budget and Certainty Test.** At most two non-certainty hits per
season. Any hit justified by a projection rather than a certainty (injury,
suspension, confirmed non-starter, left the club) needs 8+ points over four
gameweeks and 4+ over two.

**R13 — Freeze After Information.** Once the press conferences are in and the
team is saved, no edit without new expected-minutes information.

**R14 — Log Before Results.** Write the decision and the reasoning before the
deadline, and review it afterwards against the reasoning rather than the
score. This is the only rule that makes the others self-correcting.

## Pre-deadline checklist

### Stage 1 — Data source lock
- Pulled today's `bootstrap-static` and recorded `now_cost / 10` for everyone
  involved? **No: stop. Nothing is priced from a secondary source.**
- Post-move bank computed in writing and at least £0.0m? **No: void.**
- Every price in your notes traceable to that pull? **No: delete and re-pull.**

### Stage 2 — Minutes gate, per incoming player
Any single failure rejects the player. No averaging.
- Started 4 of the last 5 league games while fit and available?
- Played 75% or more of available league minutes over that window?
- **Not** substituted at or before half-time in his last competitive start?
- No European or cup fixture within 72 hours before kickoff, or two prior
  instances this season of him starting after one?
- Five or fewer fixtures in the next 22 days?
- Can you name his competitor for the role and say why he isn't displaced, in
  one sentence, with a minutes figure?
- If £7.5m or more: 5 of 5 starts and 85% of minutes?

### Stage 3 — Output gate, per incoming player
- Club's shots-on-target rate at or above league median over six games?
- Three or more attacking returns, or top-quartile xGI per 90 for his
  position, over his last six appearances?
- Projected edge over the man he replaces of 2.0+ points for one gameweek, or
  1.0+ per gameweek sustained over four? **Below that you are inside model
  error of 1.18–1.92 points per player per gameweek. Hold the transfer.**
- Is the case built on something other than his last single match?

### Stage 4 — The caveat gate
- Read your own notes start to finish. Any unrefuted reason he might fail?
  **Yes: the purchase is forbidden this gameweek.**
- Pre-mortem: write "it is Monday, he returned 2 points, why?" and list three
  causes. Any cause you cannot rule out with a data point rejects him.
- Blind test: strip the names, write only the numbers for your target and the
  two next-best at that price. Does your target still win? **No: buy the one
  that did.**

### Stage 5 — Hit gate
- Covered by a free transfer? Skip ahead.
- Is the reason a certainty rather than a projection? Proceed.
- Otherwise: 8+ points over four gameweeks and 4+ over two, and two or fewer
  non-certainty hits taken this season? **No: roll the transfer.**

### Stage 6 — Captaincy
- Armband on the highest-projected player from one model fixed in advance?
  **Yes: done.**
- If not, is the gap under 0.5 points? **No: move the armband. No discussion.**
- If under 0.5: does your choice have equal or better minutes security?
  **No: move it.**
- Did ownership enter the reasoning before those gates passed? **Yes: void,
  restart.**
- Vice-captain is the highest-projected player with the most secure minutes,
  not the second-highest ceiling?

### Stage 7 — Lineup mechanics
- XI legal, all eleven expected to start?
- Bench order re-set this gameweek rather than inherited?
- Bench order survives the formation constraint — if the first sub can't come
  on without breaking the minimum three defenders, is the right player
  positioned?
- Auto-subs fire on **zero minutes only**. A one-minute cameo or a 90-minute
  blank is never replaced. The bench is not blank insurance.
- Second goalkeeper last on the bench unless he is starting.
- In a double gameweek, the sub most likely to play twice goes first.

### Stage 8 — Timing and freeze
- Press conferences done? **No: don't transfer yet.** The only exception is a
  player you will buy regardless of team news who is near-certain to rise —
  information is worth more than £0.1m.
- Team saved, then captain, vice and goalkeeper re-verified after saving?
- **Freeze.** No further edit without new expected-minutes information.
- Decision and reasoning logged before results.

### Stage 9 — Wildcard and Free Hit addendum
- Draft saved to a timestamped file?
- Every one of the fifteen passed stages 1–4 individually, with the evidence
  written next to the name?
- Revision number two or lower?
- Each revision triggered by new external information rather than by
  re-weighing the same facts?
- Final arithmetic at API prices fits the budget, computed in writing?

## What the evidence actually supports

Worth recording, because several of these contradict conventional advice and
contradict things this project previously believed.

- **Differential captaincy is a straight loss when you own both players.** The
  field's ownership cancels out of the comparison entirely. Simon March, a
  former world champion, puts it as "almost never" justified when a high-EO
  option exists.
- **Adding variance lowers expected rank** above the median, because the
  field's points distribution is concave there. Variance only helps when the
  objective is a low-probability threshold far above you.
- **Being on the template is not a weakness.** The one peer-reviewed study
  (O'Brien, Gleeson and O'Sullivan, *PLoS ONE* 2021, ~1m managers) finds top
  managers converge on templates and that skill persists across seasons,
  attributed to long-term planning and consistency rather than weekly
  cleverness.
- **Elite managers' modal hit count for a whole season is zero.** Transfer
  *count* is similar across rank bands; what differs is how much they pay.
- **Elites use chips 3–4x more than the field and earlier.** Hoarding chips
  for the run-in is the field's behaviour.
- **Triple Captain in a single gameweek is worth about 6–9 points.** It wants
  a double gameweek.
- **Watching a player is often harmful.** You watch to justify a decision
  already made; the blind numeric comparison is more reliable.

Evidence quality, stated plainly: exactly one peer-reviewed source exists.
The top-50 and top-1,000 figures are descriptive, small-sample and
single-publisher. The captaincy algebra is a derivation, not a citation. The
numeric thresholds above are deliberately tighter than any published
heuristic, because the documented failure mode here is override, not
ignorance.
