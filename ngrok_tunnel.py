"""Ngrok Tunnel runner using the official ngrok Python SDK."""

import asyncio
import os
import subprocess
import sys
import webbrowser

try:
    import ngrok
except ImportError:
    print("Installing official ngrok library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ngrok"])
    import ngrok

AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "3J0iQRFRrNURPNhkJ1atiTpZ9hX_67zfVdRmdJTGt8Tuwu3Yn")
PORT = 5173


async def main():
    print("\n" + "=" * 60)
    print("      AlgoScan / StockAI Pulse - Ngrok Live Tunnel")
    print("=" * 60 + "\n")
    print("Connecting to ngrok secure edge servers...")

    try:
        listener = await ngrok.forward(
            PORT,
            authtoken=AUTHTOKEN,
            session_metadata="algoscan-stockai-pulse",
        )

        public_url = listener.url()

        print("\n" + "=" * 60)
        print("  🎉 NGROK TUNNEL IS LIVE!")
        print(f"  👉 URL: {public_url}")
        print("=" * 60 + "\n")

        # Copy to clipboard on Windows
        try:
            subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard '{public_url}'"],
                capture_output=True,
                check=False,
            )
            print("  (Copied URL to your clipboard!)")
        except Exception:
            pass

        print("  Opening URL in your browser...\n")
        webbrowser.open(public_url)

        print("Tunnel is running. Keep this window open.")
        print("Press Ctrl+C to stop sharing.\n")

        # Keep running
        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        print("\nStopping ngrok tunnel...")
    except Exception as exc:
        print(f"\n[Error] Could not start ngrok tunnel: {exc}")
        print("Please check that your start.bat is running.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
