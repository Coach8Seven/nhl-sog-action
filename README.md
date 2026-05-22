# NHL Shots On Goal GPT Action Helper

This helper gives your NHL custom GPT reliable last 5 and last 10 shots on goal data.

## What It Does

Endpoint:

`GET /player-sog-log`

Accepts:

- `player_name`: player name, such as `Connor McDavid`
- `season`: optional season, such as `20252026`; omit for current season
- `game_type`: `2` for regular season, `3` for playoffs
- `limit`: number of games to return, usually `10`
- `line`: SOG prop line, such as `3.5`

Returns:

- date
- opponent
- home/road
- shots on goal
- goals/assists/points
- TOI when available
- PP TOI when available
- last 5 average shots
- last 10 average shots
- hit rate versus the supplied SOG line

## Local Test

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
python app.py
```

Test:

```bash
curl "http://localhost:8000/player-sog-log?player_name=Connor%20McDavid&limit=10&line=3.5"
```

## Deploy

Deploy this folder to Render, Railway, Fly.io, or another public HTTPS host.

Start command:

```bash
gunicorn app:app
```

After deployment, copy your public URL and replace this line in `openapi.yaml`:

```yaml
servers:
  - url: https://YOUR-DEPLOYED-DOMAIN.example.com
```

## Add To Your Custom GPT

1. Edit your NHL custom GPT.
2. Open the Actions section.
3. Create a new action.
4. Authentication: `None` for private testing.
5. Paste the updated `openapi.yaml`.
6. Test `getPlayerSogLog`.

