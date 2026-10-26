#!/usr/bin/env python3
"""
APAAR-Sutra Local Webhook Receiver Test Server
Listens for incoming webhook events from APAAR-Sutra, verifies the X-Signature header,
and outputs the parsed event payload.
"""

import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys

DEFAULT_SECRET = "whsec_demo_secret_2026"


class WebhookHandler(BaseHTTPRequestHandler):
    secret: str = DEFAULT_SECRET

    def do_POST(self):
        # 1. Read request headers
        event_type = self.headers.get("X-APAAR-Event", "unknown")
        signature_hdr = self.headers.get("X-Signature", "")
        delivery_id = self.headers.get("X-Delivery-ID", "N/A")

        # 2. Read body bytes
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        # 3. Verify HMAC signature
        expected_sig = "sha256=" + hmac.new(
            self.secret.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(signature_hdr, expected_sig)

        print("\n" + "=" * 60)
        print(f"🔔 INCOMING WEBHOOK EVENT: {event_type}")
        print(f"Delivery ID: {delivery_id}")
        print(f"Header Signature:   {signature_hdr}")
        print(f"Computed Signature: {expected_sig}")
        print(f"Signature Valid:    {'✅ YES' if is_valid else '❌ INVALID SIGNATURE'}")

        if not is_valid:
            print("⚠️ Rejected webhook with 401 Unauthorized due to signature mismatch.")
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid HMAC signature"}')
            return

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
            print(f"Payload Content:\n{json.dumps(payload, indent=2)}")
        except Exception:
            print(f"Raw body: {body_bytes.decode('utf-8', errors='replace')}")

        print("=" * 60 + "\n")

        # Respond with 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"received": true, "status": "acknowledged"}')

    def log_message(self, format, *args):
        # Suppress default noisy access logs
        return


def run_receiver(port: int = 9000, secret: str = DEFAULT_SECRET):
    WebhookHandler.secret = secret
    server_address = ("", port)
    httpd = HTTPServer(server_address, WebhookHandler)
    print(f"🚀 APAAR-Sutra Webhook Test Receiver listening on http://localhost:{port}")
    print(f"🔑 Secret configured: '{secret}'")
    print("Waiting for incoming events (Press Ctrl+C to stop)...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down receiver...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APAAR-Sutra Webhook Local Receiver")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on (default 9000)")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Webhook subscription secret")
    args = parser.parse_args()

    run_receiver(port=args.port, secret=args.secret)
