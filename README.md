# Weather MCP Server

A minimal Model Context Protocol (MCP) server that exposes weather tools backed by the US National Weather Service (api.weather.gov). It uses FastMCP helpers from the `mcp` package and `httpx` for async HTTP.

Maintainer: Ernesto Crespo <ecrespo@gmail.com>

## Overview
This server provides two MCP tools:
- get_alerts(state): Returns active NWS alerts for a US state (two‑letter code).
- get_forecast(latitude, longitude): Returns a short formatted forecast for a given location by calling NWS `/points/{lat,lon}` and then following the `properties.forecast` URL.

Transport: stdio (the MCP host launches `python weather.py`).

## Stack
- Language: Python 3.13
- MCP framework: `mcp.server.fastmcp.FastMCP`
- HTTP client: `httpx` (async)
- Package/dependency manager: `uv` (uses `pyproject.toml` + `uv.lock`)
- Container: Multi‑stage Dockerfile (Debian slim Python 3.13)

## Requirements
- Python 3.13+
- `uv` installed (see https://docs.astral.sh/uv/)
- Network access to https://api.weather.gov

## Setup (Local, uv)
1) Sync environment (respects uv.lock):
   uv sync --frozen

2) Run the server (stdio transport):
   uv run python weather.py

3) Install into an MCP host (Claude Desktop via MCP CLI):
   uv run mcp install weather.py --name "WeatherMCPServer"

Notes:
- Tools are async; registered via `@mcp.tool()` decorators in `weather.py`.
- The host will exec `weather.py` and communicate over stdio.

## Docker
Build:
- docker build -t weather-mcp-server .

Run (ad‑hoc execution of stdio server):
- docker run --rm -it weather-mcp-server

Image behavior:
- Uses a builder stage to create a virtualenv via `uv sync --frozen`.
- Final stage runs as non‑root user `mcpuser` and starts `python3 weather.py` by default.

## Configuration and Environment
- Networking: Outbound HTTPS to `https://api.weather.gov` must be allowed.
- User-Agent: Requests send `User-Agent=weather-app/1.0` (constant `USER_AGENT` in `weather.py`).
  - TODO: Allow overriding USER_AGENT via environment variable for proper contact info per NWS guidelines.
- Timeout: `httpx.AsyncClient(..., timeout=30.0)` is used in `make_nws_request`.
- Error handling: Any exception during fetch returns `None`; tools return human‑readable messages such as "Unable to fetch ..." or "No active alerts ...".
- Logging: A `utils/LoggerSingleton` exists but is not wired into the server. If needed, import and use `from utils.LoggerSingleton import logger`.
- Docker runtime env set by image: `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `PATH=/app/.venv/bin:$PATH`.

## Entry Points and Scripts
- Entry point: `weather.py` (runs FastMCP server with stdio transport).
- pyproject scripts: None defined.
  - TODO: Consider adding `scripts`/`tool` entries or `uvx`/Makefile tasks for common actions (run, test, lint).

## Testing
Prefer mocking the network to avoid flakiness and NWS rate limits. The easiest seam is `weather.make_nws_request`; provide a replacement async function that returns canned responses.

Option A: Quick standalone test (no external deps)

Create `test_simple.py`:

  import asyncio, weather
  async def fake_make_nws_request(url: str):
      if "/alerts/active/area/" in url:
          return {"features": [{"properties": {"event": "Test Alert", "areaDesc": "Test Area", "severity": "Severe", "description": "This is only a test.", "instruction": "Do nothing."}}]}
      if "/points/" in url:
          return {"properties": {"forecast": "https://api.weather.gov/gridpoints/MTR/88,126/forecast"}}
      if "/forecast" in url:
          return {"properties": {"periods": [{"name": "Tonight", "temperature": 60, "temperatureUnit": "F", "windSpeed": "5 mph", "windDirection": "NW", "detailedForecast": "Clear."}]}}
      return None
  async def main():
      weather.make_nws_request = fake_make_nws_request  # type: ignore
      assert "Test Alert" in await weather.get_alerts("CA")
      assert "Temperature" in await weather.get_forecast(37.77, -122.42)
      print("test_simple: OK")
  if __name__ == "__main__":
      asyncio.run(main())

Run it:
- uv run python test_simple.py

Option B: pytest (recommended)
- Without modifying pyproject (ephemeral tools):
  uvx pytest -q
- With dev dependencies (if you choose to add them): add pytest, pytest-asyncio, respx, httpx under a dev group.

Example pytest test skeleton:

  import weather, pytest
  @pytest.mark.asyncio
  async def test_tools_smoke():
      async def fake(url: str):
          if "/alerts/" in url:
              return {"features": []}
          if "/points/" in url:
              return {"properties": {"forecast": "f"}}
          return {"properties": {"periods": [{"name": "Now", "temperature": 1, "temperatureUnit": "F", "windSpeed": "1 mph", "windDirection": "N", "detailedForecast": "Cold."}]}}
      weather.make_nws_request = fake  # type: ignore
      assert "No active alerts" in await weather.get_alerts("XX") or "Event:" in await weather.get_alerts("XX")
      out = await weather.get_forecast(0, 0)
      assert "Temperature" in out

Cleanup: remove temporary test files after running to keep repo clean.

## Project Structure
- weather.py — MCP server exposing tools and stdio runner.
- utils/LoggerSingleton.py — Optional logger helper (console + best‑effort file logging).
- pyproject.toml — Project metadata and dependencies.
- uv.lock — Locked dependency versions for uv.
- Dockerfile — Multi‑stage container build to run the server.
- LICENSE — Project license.
- README.md — This file.

## License
This project includes a LICENSE file in the repository root. See LICENSE for details.

## Troubleshooting
- SSL/Network failures: You will see messages like "Unable to fetch ...". Ensure outbound HTTPS and DNS are available. If behind a proxy, configure httpx via standard env vars (e.g., HTTPS_PROXY, NO_PROXY).
- API changes: If api.weather.gov modifies response schemas, update `format_alert` and property lookups; keep test mocks in sync.
- High latency: Adjust the timeout value in `make_nws_request` if needed.

## Roadmap / TODOs
- Parameterize USER_AGENT via environment variable and document required format for NWS contact info.
- Wire in LoggerSingleton if richer logging is desired and verify file logging paths for containerized environments.
- Add dev/test tooling (pytest, pytest-asyncio, respx) as an optional dependency group.
- Add simple run/test scripts (e.g., via pyproject scripts or Makefile).

