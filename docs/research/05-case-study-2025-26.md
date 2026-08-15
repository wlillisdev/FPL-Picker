# Case Study: The 2025/26 Season

*Compiled 2026-08-15 from three research studies (players, teams, season narrative). The
calibration evidence base for FPL-Picker's prediction model. Facts sourced from web research;
figures flagged by the researchers as single-source should be re-verified against FBref/Opta
before being hard-coded.*

## 1. The season in one paragraph

Arsenal won the league (85 pts, best defence: 27 GA, plus a record 19 corner goals); Man Utd
finished 3rd after sacking Amorim for Carrick in January; champions Liverpool collapsed to 5th
(Salah: 4 league goals at £14.5m — the biggest premium bust ever); Sunderland finished 7th as a
promoted side (+13 pts over xPts — huge regression candidate); West Ham, Burnley, Wolves went
down. FPL was redefined by the new **defensive-contribution (DefCon) points**: six of the nine
top FPL scorers were defenders, and the FPL champion — Erik Ibsen, a first-season rookie — won
by 38 points on the back of **pre-season DefCon backtesting**, boring captaincy (Haaland 22/38),
**zero point hits all season**, and one legendary conviction hold (João Pedro's 19-pt GW29 haul
while 600k+ managers sold).

## 2. Player-level findings

### The 200 club (only four players)
| Player | Pos | Pts | Start price | Note |
|---|---|---|---|---|
| Haaland | FWD | 239 | £14.0m | 27G; most-captained every single GW |
| Bruno Fernandes | MID | 235 | ~£9.0m | 24 assists, all 6 Utd pens, 12 double-digit hauls |
| Gabriel | DEF | 209 | £6.0m | 18 CS; 3rd defender ever to 200 |
| Semenyo | MID | 202 | £7.0m | 75 pts after January £64m move to City |

### Value: price was almost *inversely* related to value
Every top-5 points-per-million player by position cost under £8.5m. Standouts: Truffert
(£4.5m DEF, 165 pts — best PPM in the game), Guéhi (£4.5m, 179 pts), Igor Thiago (£6.0m FWD,
22 goals on 20.57 xG — sustainable, penalty-backed), Elliot Anderson (~£5.5m MID, ~180 pts,
~50 DefCon pts), Roefs (£5.0m promoted-team GK, 136 pts on save volume).

### DefCon changed squad structure
+2 pts for 10 CBIT (DEF) / 12 tackles+recoveries+CBIT (MID). Senesi ~50 pts at a 70% hit rate;
Tarkowski 44; Anderson ~50 (≈30% of his total). **Prior-season shadow data predicted DefCon
output almost perfectly** — it's a quasi-deterministic floor, stable within ~6 GWs. Crucially,
**DefCon and clean sheets anti-correlate by team style**: elite possession sides' CBs (Gabriel,
Guéhi: only 22 DefCon pts each) score via CS+bonus; low-block CBs score via volume defending.

### Busts had visible warning signs by GW6–10
Salah (age-33, early xG deficit that was decline not luck, role friction under Slot), Palmer
(August injury recurrence), Isak (no pre-season, never completed 90'), Wirtz & Gyökeres
(league-adaptation tax on record signings). Pattern: **premium new signings and aging premiums
carry systematic risk the price doesn't reflect.**

### Captaincy math
Haaland took 59% of elite captaincies (avg 6.78 when captained) but Bruno averaged **8.85**
per captaincy with the best haul rate (12 double-digit games). Volume-default vs
fixture-picked efficiency — the champion used Haaland as default and Bruno situationally (7×,
including the title-sealing final day).

### The timing edge (most important finding)
**Every major breakout (Thiago, Semenyo, Anderson, Senesi, Truffert, Roefs) was identifiable
by GW4–7** from shot volume, DefCon hit-rate, penalty duty, or save volume — while prices
lagged by months. Every major bust flagged in the same window via minutes/injury/xG signals.
A model that re-weights sharply toward current-season data after ~5 GWs beats the August
template on both entries and exits.

## 3. Team-level findings

- **Set pieces are a persistent, modelable edge**: ~25% of all PL goals; Arsenal a record 19
  corner goals; Spurs' corner threat survived three head coaches. Encode `sp_goals_share` and
  taker identity.
- **The European tax is real**: four of six CL teams cratered domestically (Liverpool 5th,
  Chelsea 10th, Newcastle 12th, Spurs 17th) while no-Europe teams with decent squads overshot
  (Utd 3rd, Bournemouth 6th, Sunderland 7th). Encode European load × squad depth.
- **Finishing/keeper variance must be regressed separately**: Palace scored 13.9 goals *under*
  xG (their attackers were traps, their defence fine); Sunderland's +13 xPts overshoot was
  keeper overperformance. Both are 2026/27 mean-reversion calls.
- **Home/away splits dominate mid-table clean sheets** (Villa/Fulham 6 home CS vs 3 away;
  Leeds 6 vs 2). Venue-conditional CS probabilities beat season averages.
- **Manager changes have a signed pattern**: first panic hires were net negative (Postecoglou,
  Rosenior, Edwards); *subsequent* stabilizers bounced (Carrick → 3rd, De Zerbi survival,
  Pereira → Gibbs-White surge). Lame-duck managers (Glasner's announced exit) decay league form.
- **Attacking concentration beats team quality**: Bowen delivered 187 pts at relegated West
  Ham; Thiago 22 goals at 9th-place Brentford. Encode share of team xGI held by top 1–2 players.
- **Two viable GK archetypes**: elite-CS (Raya, 19 CS) and save-volume mid-table (Roefs,
  Pickford, Henderson). Model shots-faced and CS probability separately.
- **Promoted teams span a huge range** (Sunderland 7th vs Burnley 22 pts) — widen priors, weight
  manager continuity + spend, don't default to pessimism. DefCon + save points made £4.0–5.0m
  promoted-team assets viable for the first time.

## 4. How the champion played it (strategy validation)

Ibsen's season, verified against our strategy rules:
- **GW1 built on rule-change research** (Tarkowski + Caicedo from day one) — edge came from
  modeling a rule change before the market priced it.
- **Wildcard GW2** to fix a broken experimental draft (his stated regret — validates "don't
  overthink GW1; WC1 is cheap because it expires").
- **Captaincy**: Haaland 22, Bruno 7, nobody else more than twice; sat through a 4-blank-in-5
  Haaland stretch without chasing.
- **Zero hits in 38 gameweeks** (enabled by 5-FT banking).
- **The conviction hold**: kept João Pedro in GW29 while 600k+ sold → 19 points → world #1 from
  GW29 to the end. Elite consensus had sold him at GW10; *timing* conviction, not conviction
  itself, is the skill.
- **Chip line**: WC GW32 → Bench Boost DGW33 (**112 pts**) → Free Hit BGW34 → Triple Captain
  Haaland DGW36 (33 of his 92). Identical to the top-50 modal line.
- Final day: two transfers (Bowen, Porro) both hauled; captained Bruno (14).

Field-level chip data: DGW33 drew 2.3m+ chips (BB most popular); DGW36 drew a 3rd-highest-ever
1.1m+ TCs, 83% on Haaland.

## 5. Carried into 2026/27 (current season)

- Promoted: Coventry, Ipswich, Hull. Salah has left the game entirely (Trabzonspor).
- Big moves: Rogers → Chelsea (£117m), Anderson → Man City (£116m), Guimarães → Arsenal,
  Semenyo/Guéhi already at City.
- **Manager carousel makes early 2026/27 high-variance**: Maresca now at City (Pep stepped
  down), Iraola at Liverpool, Howe left Newcastle in pre-season, new bosses at Bournemouth and
  Palace. Bournemouth flagged by previews as the "clearest early avoid" (Europe debut + new
  manager + hard openers). Sunderland regression is the consensus call.
- GW1 template: Haaland £15.5m (~75% owned, consensus captain), Bruno £12.0m, João Pedro £7.5m
  (most-owned player), Szoboszlai £7.0m, Mbeumo surging, DefCon defenders baked into the
  template. Arsenal remain the defensive/set-piece anchor.

## 6. Feature list distilled for the model

Team-level: xG/xGA with separate finishing- and keeper-variance regression terms ·
set-piece xG share + taker identity · penalty rate per team + nailed-taker flag · attacking
concentration index · European load state × squad depth · manager stability/change-type ·
home/away defensive splits · rotation index · promoted-team wide priors · cup-run DGW/BGW
structure.

Player-level: DefCon floor from prior-season CBIT/tackle volume · minutes/starts trend ·
opponent-adjusted npxG/xA with age- and context-gated regression of finishing deltas ·
penalty/set-piece duty as discrete step-change events · save-volume for keepers ·
premium-new-signing adaptation haircut (~10–14 GWs) · sharp re-weight to current-season data
after ~GW5.

Strategy (validated by the champion's season): boring template captaincy + differentials in
the outfield ten · zero-hit discipline is viable and title-winning · chip choreography around
the DGW/BGW map (WC → BB best DGW → FH worst blank → TC anchor's double) · rule changes are
the single biggest exploitable edge when modeled before the market prices them.
