# Research: Competitive Landscape & SWOT

*Compiled 2026-08-15 from web research (agent report). FPL assistant tools, 2025–26.*

## (a) Feature matrix (condensed)

| Tool | Price | xPts | Transfer solver | Team import | Rate-my-team | Chips | Price predict | AI chat | UI |
|---|---|---|---|---|---|---|---|---|---|
| [FPL Review](https://fplreview.com/) | Free model + ~£3.50/mo premium | Reference-standard EV, 14-GW | Full multi-week solver | Yes | Via planner | Yes | No | No | Web |
| [Fantasy Football Fix](https://www.fantasyfootballfix.com/) | ~£3.15/mo annual | Opta-based | AI Assistant Manager | Yes | Yes | Partial | Yes (famous) | No | Web+apps |
| [Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/) | ~£3–4/mo | Projections | Manual planner | Yes | Yes | Editorial | Yes | No | Web+community |
| [Fantasy Football Hub](https://www.fantasyfootballhub.co.uk/) | ~$12–15/mo | Opta regression | AI suggestions | Yes | Yes | Yes | Yes | Marketed | Web+app |
| [FPL Copilot](https://fplcopilot.com/) | Core free, Pro paid | xPts tables | 10-GW solver incl. hits | Yes | 0–100 score | Yes | No | Claude chat | Web |
| [fpl.team](https://fpl.team/) | Free 3-GW/2 plans; paid full | Yes | Combinatorial plans | Yes | Via planner | Yes | No | No | Web+apps |
| [FPL Analyzer](https://www.fpl-analyzer.com/) | Free | + Monte Carlo | AI suggestions | Mini-league | Partial | Sims | Risers | Marketed | Web |
| [FPL Central](https://fplcentral.co.uk/) | Free | xP + AI best XV | No | No | No | No | Yes | No | Web |
| [FPLForm](https://fplform.com/) | Free | Per-fixture + play-prob CSV | Ranked transfers, WC/FH | Yes | No | WC/FH | No | No | Web tables |
| [LiveFPL](https://www.livefpl.net/) | Free | No | Visual planner | Yes | No | No | Best-in-class | No | Web+app |
| [FPL Optimized](https://fploptimized.com/) | Free | Uses FPL Review | Sensitivity + Monte Carlo | Yes | No | Via solver | No | No | Web |
| Open-source ([solver](https://github.com/sertalpbilal/FPL-Optimization-Tools), [OpenFPL](https://arxiv.org/abs/2508.09992)) | Free | OpenFPL ensembles | Full multi-period | Scripts | No | Yes | No | No | Notebooks/CLI — **our direct peers** |

Signals worth noting: the official PL/Microsoft **Copilot companion** means AI chat over FPL is
going first-party; Fantasy Football Fix has a documented
[Trustpilot](https://uk.trustpilot.com/review/www.fantasyfootballfix.com) trust problem
(auto-renewal complaints) — goodwill is available to anything free and open; OpenFPL's stated
rationale is that incumbents "have not openly released their code".

## (b) What the best tools do that we don't (yet)

1. **Multi-period transfer solving from *your actual team*** (team-ID import) — the biggest gap;
   from-scratch squad picking is a wildcard tool, useful ~2 weeks a season.
2. **Minutes/starting-probability modeling** — the accuracy differentiator.
3. **Chip planning** (WC/FH/BB/TC timing).
4. **Uncertainty, not just EV** (sensitivity analysis, Monte Carlo scenarios).
5. **Price-change prediction** (daily engagement driver).
6. **Rate-my-team scoring** (highest-traffic casual entry point).
7. **AI chat interfaces.**
8. **Web/mobile UX** — no install, no Python literacy required.
9. **Richer data** (Opta, Understat, elite-manager ownership).

## (c) Market gaps nobody serves well

1. **A maintained, pip-installable, end-to-end open-source pipeline** — OpenFPL has a model but
   no solver product; sertalpbilal has a solver but no bundled projections. Nobody ships
   *projections + full-rules MILP + transfer logic* as one documented, tested package.
   **That's our seam.**
2. **Year-round availability** (FPL Review historically goes dark off-season).
3. **Transparent, reproducible projections** ("show your work").
4. **Honest, free access** (vs freemium caps and dark-pattern billing).
5. **Programmatic/agent access** — CLI/library/JSON for the LLM-agent wave; nobody owns
   "the optimization backend for FPL agents".
6. **Uncertainty-aware planning made legible for normal users.**
7. **Free unrestricted multi-week solving** (every hosted free tier is capped).

## (d) SWOT for FPL-Picker

### Strengths
- Genuinely **open and free** in a freemium-gated market; auditable code answers the
  reproducibility critique.
- **Full-rules MILP** is a real technical moat vs casual tools — same engine class as paid solvers.
- Blended multi-signal scoring with fixture decay already beats most free sites' single-factor scores.
- **Extensible Python codebase**; CLI is a feature for the scripting/agent audience.
- **Zero infrastructure cost** — no pressure to gate features; incumbents' freemium caps are our
  permanent wedge.

### Weaknesses
- **No minutes model** — the single biggest accuracy differentiator we lack.
- **No team-ID import / transfer solver** — 36 weeks a year the user's real question is unanswered.
- **Single-solve model** — no per-GW squad dynamics, FT banking value, chips, or uncertainty.
- **CLI-only** — excludes ~99% of the 11M+ player base; no viral entry point.
- **Depends on FPL's black-box fields** (ep_next, form) — weakens the transparency claim;
  ep_next blending risks double-counting correlated errors.
- **No brand, community, or content** — distribution in this market is community-driven.

### Opportunities
- **Become the reference open-source end-to-end stack** (the gap between OpenFPL and
  sertalpbilal's tools); optionally integrate OpenFPL's published models.
- **Transfer solver + team import is a well-understood MILP extension** — converts us from
  wildcard toy to weekly tool.
- **Off-season and free-tier arbitrage** — be available when others are dark or capped.
- **Agent/API niche** — expose the engine as a library/JSON/MCP endpoint.
- **Uncertainty-aware output** — cheap for us, rare in the market.
- **A thin free web front end** ("rate my team") captures the highest-volume search intent.

### Threats
- **Free tiers of strong incumbents** already cover the casual user — "free" alone isn't a
  differentiator; *open + unrestricted + scriptable* must be.
- **First-party AI** (the PL's Microsoft Copilot companion) could absorb the casual advice market.
- **FPL API fragility** — undocumented, unversioned; yearly rule changes can silently break
  ingestion and constraints.
- **Accuracy reputation risk** — the community actively benchmarks models; publishing our own
  backtests is a defensive necessity.
- **PythonAnywhere free-tier limits** (CPU, outbound whitelist — the FPL API is already blocked
  from cloud IPs) cap solver heaviness and hosting ambitions.

**Bottom line:** the market is saturated on xPts tables and freemium web solvers, but wide open
for a maintained, transparent, unrestricted, end-to-end open-source engine — provided we close
the three gaps that define "serious" in 2025–26: **team import + multi-period transfer/chip
solving, a minutes model, and uncertainty quantification.**
