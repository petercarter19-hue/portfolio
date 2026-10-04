"""Dedicated startup, with no product app.py at the deployment root."""
from contextlib import ExitStack
import os
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
from tools.cloud_demo.runtime import Config, create_application

def main():
    config = Config.from_environment()
    port = int(os.environ.get('PORT', '8000'))
    if not 1 <= port <= 65535:
        raise ValueError('Invalid listener port')
    from waitress import serve
    with ExitStack() as stack:
        application = create_application(SOURCE, config, stack)
        # Waitress resolves '*' through host None, which the retained offline
        # fixture guard permits. IPv4 wildcard binding does not allow outbound
        # DNS or connections and does not change the shared fixture guard.
        serve(application, host='*', ipv6=False, port=port, threads=2,
              max_request_body_size=4_000_000, expose_tracebacks=False,
              clear_untrusted_proxy_headers=False)

if __name__ == '__main__':
    main()
