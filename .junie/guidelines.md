Project: weather-mcp-server
Maintainer: Ernesto Crespo <ecrespo@gmail.com>

Scope
- This repository implements a minimal MCP server exposing weather tools backed by the US National Weather Service (api.weather.gov) using the mcp FastMCP helper and httpx.
- Python 3.13 is required. Dependencies are managed with uv, and a multi-stage Dockerfile is provided for production.

Build and configuration
1) Local environment (uv)
- Install uv if you don’t have it: see https://docs.astral.sh/uv/
- Sync the environment (respects uv.lock):
  uv sync --frozen
- Run the server (stdio transport):
  uv run python weather.py
- Install into Claude Desktop (MCP CLI):
  uv run mcp install weather.py --name "WeatherMCPServer"
  Notes:
  - The server uses stdio transport; MCP host will exec weather.py.
  - Tools are async and exposed via FastMCP decorators.

2) Docker
- Build:
  docker build -t weather-mcp-server .
- Run (stdio is typical when the host process launches it; for ad‑hoc runs, you can exec the image):
  docker run --rm -it weather-mcp-server
  The default CMD starts python3 weather.py as the non-root user mcpuser and uses the virtualenv copied from the builder stage.

Runtime behavior and configuration
- Networking: Outbound HTTPS to https://api.weather.gov is required for live calls.
- User-Agent: Requests send User-Agent=weather-app/1.0. Update USER_AGENT in weather.py if you need proper contact info per NWS guidelines.
- Timeouts: httpx.AsyncClient uses a 30s timeout in make_nws_request.
- Error handling: Any exception during HTTP fetch returns None; tool functions convert that into human-readable failures such as "Unable to fetch..." or "No active alerts...".
- Logging: A LoggerSingleton exists in utils/ but the current server does not wire it in. If you need logging, import utils.LoggerSingleton.logger and use it. The logger attempts to write to a best-effort directory and always logs to console.

Testing
General guidance
- Prefer mocking the network to avoid flaky tests and NWS rate limits. The easiest seam is weather.make_nws_request; provide a replacement async function that returns canned structures matching the API surface used by tools.
- For structured testing, pytest + pytest-asyncio (or any async test framework) works well. You can run pytest without adding it to pyproject by using uvx (temporary runner), or add it as a dev dependency if you prefer.

Option A: Quick standalone test (no external deps)
- Create a temporary test script that monkeypatches weather.make_nws_request and calls the tools with asyncio. Example sketch:

  # test_simple.py
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

- Run it:
  uv run python test_simple.py
- Clean up the temporary test file when done to keep the repo clean.

Option B: pytest (recommended for real suites)
- Without modifying pyproject (uses ephemeral tools):
  uvx pytest -q
- With dev dependencies (if you choose to add them): add to pyproject.toml under [project-optional-dependencies] or a dev segment (uv supports groups), e.g., pytest, pytest-asyncio, respx, and httpx.
- Example pytest test skeleton:

  import asyncio, types, weather, pytest
  @pytest.mark.asyncio
  async def test_tools_smoke():
      async def fake(url: str):
          return {"features": []} if "/alerts/" in url else {"properties": {"forecast": "f"}} if "/points/" in url else {"properties": {"periods": [{"name": "Now", "temperature": 1, "temperatureUnit": "F", "windSpeed": "1 mph", "windDirection": "N", "detailedForecast": "Cold."}]}}
      weather.make_nws_request = fake  # type: ignore
      assert "No active alerts" in await weather.get_alerts("XX") or "Event:" in await weather.get_alerts("XX")
      out = await weather.get_forecast(0, 0)
      assert "Temperature" in out

Adding new tests
- Keep tests deterministic by mocking make_nws_request or by using a library like respx to stub httpx calls.
- For tools with branching logic, cover both success and failure paths (e.g., empty features for alerts; None responses to ensure error strings are returned).
- Prefer small, isolated async tests. If you need to share fixtures, use pytest fixtures and pytest-asyncio.

Development tips
- Type hints: The codebase uses Python 3.13 and annotations like dict[str, Any]. Keep type hints up to date; consider mypy if you add types extensively.
- Formatting/lint: No tool is configured. Follow PEP 8/PEP 257. If you add formatters/linters (ruff/black), consider adding a minimal config and running via uvx ruff/black.
- FastMCP usage: Tools are defined via @mcp.tool() decorators and the server is started with mcp.run(transport='stdio'). Avoid side effects at import-time beyond tool registration.
- Network schema: The forecast tool calls /points/{lat,lon} and then follows properties.forecast; only a subset of the NWS schema is used. When extending, gate access to keys defensively and handle None gracefully.
- Error surfaces: Keep user-facing strings stable (“Unable to fetch …”, “No active alerts …”) so hosts relying on text heuristics aren’t broken.
- Logging: If enabling file logging in containerized or restricted environments, ensure the LoggerSingleton’s directory selection is appropriate; otherwise rely on console logs which are always enabled.

Troubleshooting
- SSL/Network failures: You will get "Unable to fetch ..." messages. Validate outbound access and DNS; if running behind a proxy, configure httpx via environment variables (HTTPS_PROXY, NO_PROXY).
- API changes: If api.weather.gov modifies response structures, adjust format_alert and the properties lookups; keep mocks in tests in sync.
- High latency: Adjust the timeout in make_nws_request.
