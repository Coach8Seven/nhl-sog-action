import os
from datetime import datetime

import requests
from flask import Flask, jsonify, request


NHL_WEB = "https://api-web.nhle.com/v1"
NHL_SEARCH = "https://search.d3.nhle.com/api/v1/search/player"

app = Flask(__name__)


def _get_json(url, params=None):
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def _num(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _first(item, keys, default=None):
    for key in keys:
        if isinstance(item, dict) and item.get(key) is not None:
            return item.get(key)
    return default


def _normalize_season(season):
    if not season:
        return None
    season = str(season)
    if len(season) == 8:
        return season
    year = int(season)
    return f"{year}{year + 1}"


def _find_player(name):
    data = _get_json(
        NHL_SEARCH,
        {"culture": "en-us", "limit": 10, "q": name},
    )
    results = data if isinstance(data, list) else data.get("data", data.get("results", []))
    if not results:
        return None

    for player in results:
        position = str(_first(player, ["positionCode", "position", "positionAbbrev"], "")).upper()
        if position != "G":
            return player
    return results[0]


def _player_id(player):
    return _num(_first(player, ["playerId", "id", "playerID"]))


def _player_name(player):
    return _first(
        player,
        ["name", "fullName", "title", "playerName"],
        f"{_first(player, ['firstName'], '')} {_first(player, ['lastName'], '')}".strip(),
    )


def _game_log(player_id, season=None, game_type=2):
    if season:
        return _get_json(f"{NHL_WEB}/player/{player_id}/game-log/{season}/{game_type}")
    return _get_json(f"{NHL_WEB}/player/{player_id}/game-log/now")


def _extract_games(data):
    if isinstance(data, list):
        return data
    for key in ("gameLog", "games", "data", "logs"):
        if isinstance(data, dict) and isinstance(data.get(key), list):
            return data[key]
    return []


def _format_game(game):
    opponent = _first(game, ["opponentAbbrev", "opponent", "opponentTeamAbbrev", "oppAbbrev"])
    home_road = _first(game, ["homeRoadFlag", "homeRoad", "homeOrAway"])
    shots = _num(_first(game, ["shots", "shotsOnGoal", "sog", "shotsOnNet"]))
    toi = _first(game, ["toi", "timeOnIce", "timeOnIcePerGame"])
    pp_toi = _first(game, ["powerPlayToi", "ppToi", "powerPlayTimeOnIce"])

    return {
        "date": _first(game, ["gameDate", "date"]),
        "gameId": _num(_first(game, ["gameId", "gamePk", "id"]), None),
        "opponent": opponent,
        "homeRoad": home_road,
        "shotsOnGoal": shots,
        "goals": _num(_first(game, ["goals"])),
        "assists": _num(_first(game, ["assists"])),
        "points": _num(_first(game, ["points"])),
        "toi": toi,
        "powerPlayToi": pp_toi,
        "source": "NHL api-web player game log",
    }


def _summary(games, line):
    def hit_rate(items):
        if line is None or not items:
            return None
        hits = sum(1 for item in items if item["shotsOnGoal"] > line)
        return {
            "hits": hits,
            "sample": len(items),
            "rate": round(hits / len(items), 3),
            "line": line,
        }

    def average(items, key):
        vals = [item[key] for item in items if item.get(key) is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 2)

    last5 = games[:5]
    last10 = games[:10]
    return {
        "last5": {
            "averageShotsOnGoal": average(last5, "shotsOnGoal"),
            "hitRateVsLine": hit_rate(last5),
        },
        "last10": {
            "averageShotsOnGoal": average(last10, "shotsOnGoal"),
            "hitRateVsLine": hit_rate(last10),
        },
    }


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "nhl-sog-action"})


@app.get("/player-sog-log")
def player_sog_log():
    player_name = request.args.get("player_name", "").strip()
    season = _normalize_season(request.args.get("season"))
    game_type = _num(request.args.get("game_type"), 2)
    limit = min(max(_num(request.args.get("limit"), 10), 1), 15)
    line_raw = request.args.get("line")
    line = float(line_raw) if line_raw not in (None, "") else None

    if not player_name:
        return jsonify({"error": "player_name is required"}), 400

    player = _find_player(player_name)
    if not player:
        return jsonify({"error": f"No player found for '{player_name}'"}), 404

    player_id = _player_id(player)
    raw_log = _game_log(player_id, season, game_type)
    games = [_format_game(game) for game in _extract_games(raw_log)]
    games = sorted(games, key=lambda item: item.get("date") or "", reverse=True)[:limit]

    return jsonify(
        {
            "player": {
                "id": player_id,
                "name": _player_name(player),
                "position": _first(player, ["positionCode", "position", "positionAbbrev"]),
                "team": _first(player, ["teamAbbrev", "team", "teamName"]),
            },
            "season": season or "current",
            "gameType": game_type,
            "requestedLimit": limit,
            "gamesReturned": len(games),
            "games": games,
            "summary": _summary(games, line),
            "notes": [
                "Hit rate uses shots on goal greater than the supplied line, matching an Over prop.",
                "TOI and power-play TOI are included when available from the NHL game-log endpoint.",
            ],
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)

