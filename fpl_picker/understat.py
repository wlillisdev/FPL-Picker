"""Understat ingestion: the xG-ecosystem features OpenFPL trains on.

Understat embeds its data in page scripts as hex-escaped JSON
(``var playersData = JSON.parse('\\x7B...')``). We fetch the league and team
pages, decode those blobs, and merge per-match player stats (shots, key
passes, xGChain, xGBuildup) and team stats (xG, xGA, deep completions, PPDA)
into our snapshot so the samples builder can fill the Understat-only feature
columns instead of leaving them NaN.

Live fetching can't be verified from sandboxed environments (understat.com is
often blocked); the parsing and merging layers are fully unit-tested and the
fetcher is best-effort with clear errors. Run with ``--with-understat`` from
a normal home connection.
"""

import codecs
import json
import re

import requests

BASE = "https://understat.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

# Understat team names -> FPL short names for the current era.
TEAM_ALIASES = {
    "manchester city": "MCI", "manchester united": "MUN", "newcastle united": "NEW",
    "tottenham": "TOT", "wolverhampton wanderers": "WOL", "nottingham forest": "NFO",
    "west ham": "WHU", "brighton": "BHA", "sheffield united": "SHU",
    "leeds": "LEE", "leicester": "LEI", "luton": "LUT",
}


def decode_blob(page_text, var_name):
    """Extract and decode a ``var X = JSON.parse('...')`` blob from a page."""
    match = re.search(var_name + r"\s*=\s*JSON\.parse\('([^']+)'\)", page_text)
    if not match:
        raise ValueError(f"Could not find {var_name} in page")
    return json.loads(codecs.decode(match.group(1), "unicode_escape"))


def _get(url, timeout=30):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_understat(season_start_year, timeout=30, sleep=0.3, fetch=None):
    """Fetch Understat league data for a season (e.g. 2026 for 2026/27).

    Returns {"teams": {understat_team_name: [per-match dicts]},
             "players": {understat_player_id: {"name":…, "team":…,
                          "matches": [per-match dicts]}}}.
    ``fetch`` is injectable for tests.
    """
    import time

    fetch = fetch or _get
    league_page = fetch(f"{BASE}/league/EPL/{season_start_year}", timeout=timeout)
    teams_data = decode_blob(league_page, "teamsData")
    players_data = decode_blob(league_page, "playersData")

    teams = {}
    for team in teams_data.values():
        rows = []
        for m in team.get("history", []):
            ppda, ppda_allowed = m.get("ppda", {}), m.get("ppda_allowed", {})
            rows.append(
                {
                    "date": (m.get("date") or "")[:10],
                    "us_xg": m.get("xG"),
                    "us_xga": m.get("xGA"),
                    "us_deep": m.get("deep"),
                    "us_deep_allowed": m.get("deep_allowed"),
                    "us_ppda_att": ppda.get("att"),
                    "us_ppda_def": ppda.get("def"),
                    "us_ppda_allowed_att": ppda_allowed.get("att"),
                    "us_ppda_allowed_def": ppda_allowed.get("def"),
                }
            )
        teams[team["title"]] = rows

    players = {}
    for p in players_data:
        page = fetch(f"{BASE}/player/{p['id']}", timeout=timeout)
        try:
            matches = decode_blob(page, "matchesData")
        except ValueError:
            continue
        rows = [
            {
                "date": (m.get("date") or "")[:10],
                "us_shots": m.get("shots"),
                "us_key_passes": m.get("key_passes"),
                "us_xgchain": m.get("xGChain"),
                "us_xgbuildup": m.get("xGBuildup"),
            }
            for m in matches
        ]
        players[str(p["id"])] = {
            "name": p.get("player_name", ""),
            "team": p.get("team_title", ""),
            "matches": rows,
        }
        time.sleep(sleep)
    return {"teams": teams, "players": players}


def _norm(name):
    import unicodedata

    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def match_team(us_name, fpl_teams):
    """Map an Understat team name to an FPL team id (None if no match)."""
    norm = _norm(us_name)
    alias = TEAM_ALIASES.get(norm)
    for team in fpl_teams:
        if alias and team["short_name"] == alias:
            return team["id"]
        if norm == _norm(team.get("name", "")):
            return team["id"]
    for team in fpl_teams:  # loose containment fallback
        tn = _norm(team.get("name", ""))
        if tn and (tn in norm or norm in tn):
            return team["id"]
    return None


def match_player(us_player, elements, team_id):
    """Map an Understat player to an FPL element id via surname + team."""
    tokens = set(_norm(us_player["name"]).split())
    candidates = []
    for e in elements:
        if team_id is not None and e["team"] != team_id:
            continue
        full = _norm(f"{e.get('first_name', '')} {e.get('second_name', '')}")
        web = _norm(e.get("web_name", ""))
        etokens = set(full.split()) | set(web.split())
        overlap = len(tokens & etokens)
        if overlap:
            candidates.append((overlap, e["id"]))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def merge_into_snapshot(data, understat):
    """Merge Understat per-match stats into the snapshot's history/team logs.

    Player matches merge into ``data['history']`` rows by kickoff date;
    team logs are stored as ``data['understat_teams']`` keyed by FPL team id
    for the samples builder. Returns (players_matched, players_total).
    """
    bootstrap = data["bootstrap"]
    history = data.get("history") or {}

    team_ids = {
        us_name: match_team(us_name, bootstrap["teams"])
        for us_name in understat["teams"]
    }
    data["understat_teams"] = {
        str(team_ids[us_name]): rows
        for us_name, rows in understat["teams"].items()
        if team_ids[us_name] is not None
    }

    matched = 0
    for us in understat["players"].values():
        team_id = team_ids.get(us["team"]) or match_team(us["team"], bootstrap["teams"])
        element_id = match_player(us, bootstrap["elements"], team_id)
        if element_id is None:
            continue
        rows = history.get(str(element_id))
        if not rows:
            continue
        by_date = {m["date"]: m for m in us["matches"] if m.get("date")}
        hit = False
        for row in rows:
            date = (row.get("kickoff_time") or "")[:10]
            if date in by_date:
                row.update({k: v for k, v in by_date[date].items() if k != "date"})
                hit = True
        matched += hit
    return matched, len(understat["players"])
