"""
run_web_terminal.py
-------------------
Launches the Institutional Derivatives Web Terminal in your default browser
with built-in Real-Time Financial API bridge (Yahoo Finance / NSE Live).
"""

import json
import os
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

PORT = 8055

TICKER_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "MIDCPNIFTY": "NIFTY_MID_SELECT.NS",
    "SENSEX": "^BSESN",
}

class TerminalRequestHandler(SimpleHTTPRequestHandler):
    """Serves static terminal files + real live spot price API."""

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path == "/api/live_spot":
            self._handle_live_spot_api(parsed_url.query)
            return

        # Default static file handling
        super().do_GET()

    def _handle_live_spot_api(self, query_string: str):
        params = urllib.parse.parse_qs(query_string)
        symbol = params.get("symbol", ["NIFTY"])[0].strip().upper()
        ticker = TICKER_MAP.get(symbol, f"{symbol}.NS")

        live_data = {"status": "offline", "symbol": symbol, "spot": None, "message": "Offline"}

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?interval=1m&range=1d"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                payload = json.loads(response.read().decode())
                meta = payload["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                t_stamp = meta.get("regularMarketTime")

                if price:
                    import datetime
                    t_str = datetime.datetime.fromtimestamp(t_stamp).strftime("%H:%M:%S IST") if t_stamp else "Live"
                    live_data = {
                        "status": "ok",
                        "symbol": symbol,
                        "spot": round(float(price), 2),
                        "time": t_str,
                        "source": "Yahoo Finance Real Feed"
                    }
        except Exception as exc:
            live_data = {
                "status": "offline",
                "symbol": symbol,
                "spot": None,
                "message": f"Real API unreachable: {exc}"
            }

        payload_bytes = json.dumps(live_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload_bytes)))
        self.end_headers()
        self.wfile.write(payload_bytes)

def open_browser():
    webbrowser.open(f"http://localhost:{PORT}/web_terminal.html")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 70)
    print(f"🚀 F&O Quantitative Terminal Pro running at:")
    print(f"   http://localhost:{PORT}/web_terminal.html")
    print(f"   Real Live API endpoint: http://localhost:{PORT}/api/live_spot?symbol=NIFTY")
    print("=" * 70)
    threading.Timer(1.0, open_browser).start()
    server = HTTPServer(("127.0.0.1", PORT), TerminalRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

if __name__ == "__main__":
    main()
