"""A loopback payment mock commits independently of the caller's transaction."""
import sqlite3
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    with tempfile.TemporaryDirectory(prefix="transaction-scope-") as directory:
        provider_path = Path(directory) / "provider.db"
        with sqlite3.connect(provider_path) as provider:
            provider.execute("CREATE TABLE charges (id INTEGER PRIMARY KEY)")

        class PaymentHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                with sqlite3.connect(provider_path) as provider:
                    provider.execute("INSERT INTO charges DEFAULT VALUES")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"paid")

            def log_message(self, *_args):
                pass

        server = HTTPServer(("127.0.0.1", 0), PaymentHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sqlite3.connect(":memory:") as app:
                app.executescript("""
                    CREATE TABLE stock (quantity INTEGER);
                    INSERT INTO stock VALUES (1);
                    CREATE TABLE orders (amount INTEGER CHECK (amount > 0));
                """)
                for attempt in (1, 2):
                    app.execute("BEGIN")
                    try:
                        app.execute("UPDATE stock SET quantity = quantity - 1")
                        request = Request(f"http://127.0.0.1:{server.server_port}/pay", data=b"", method="POST")
                        with urlopen(request, timeout=5) as response:
                            assert response.read() == b"paid"
                        app.execute("INSERT INTO orders VALUES (-100)")
                    except sqlite3.IntegrityError:
                        app.rollback()
                    else:
                        raise AssertionError("constraint failure expected")
                    quantity = app.execute("SELECT quantity FROM stock").fetchone()[0]
                    orders = app.execute("SELECT count(*) FROM orders").fetchone()[0]
                    with sqlite3.connect(provider_path) as provider:
                        charges = provider.execute("SELECT count(*) FROM charges").fetchone()[0]
                    print(f"attempt={attempt} app: stock={quantity} orders={orders}; provider: charges={charges}")
                    assert (quantity, orders, charges) == (1, 0, attempt)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == "__main__":
    main()
