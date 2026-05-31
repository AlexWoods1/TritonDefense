# SPDX-License-Identifier: MPL-2.0
"""MJPEG video stream server for the live detection feed.

Serves the latest annotated camera frame over HTTP as a ``multipart/x-mixed-replace``
MJPEG stream, so the web UI iframe can show the live feed at the same URL the App
Lab video brick used (``http://<host>:4912/embed``).

The stream frame rate is configurable via the ``fps`` argument (see
``TRITON_STREAM_FPS`` in ``main.py``) and can be changed at runtime with
:meth:`VideoStreamServer.set_fps`.
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

# Port the original video brick served on; the web UI iframe points here.
DEFAULT_PORT = 4912

# Frames per second pushed to connected clients. Adjustable per instance.
DEFAULT_FPS = 15

# JPEG encode quality (0-100); lower trades image quality for bandwidth.
DEFAULT_JPEG_QUALITY = 80

# Iframe document: an <img> tag that consumes the MJPEG stream and fills the frame.
_EMBED_HTML = b"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:#161b22;}
img{width:100%;height:100%;object-fit:contain;display:block;}
</style></head>
<body><img src="/stream" alt="Live detection feed"></body></html>
"""


class VideoStreamServer:
    """Serve the latest annotated frame as an MJPEG stream over HTTP."""

    def __init__(
        self,
        frame_source,
        port=DEFAULT_PORT,
        fps=DEFAULT_FPS,
        jpeg_quality=DEFAULT_JPEG_QUALITY,
    ):
        # ``frame_source`` is a callable returning the latest BGR frame or None.
        self._frame_source = frame_source
        self.port = int(port)
        self._fps = max(1.0, float(fps))
        self._jpeg_quality = int(jpeg_quality)
        self._httpd = None
        self._thread = None

    @property
    def fps(self):
        return self._fps

    def set_fps(self, value):
        """Adjust the stream frame rate (frames per second)."""
        self._fps = max(1.0, float(value))

    def _encode(self, frame):
        ok, buf = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality]
        )
        return buf.tobytes() if ok else None

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            # HTTP/1.0 keeps the long-lived MJPEG response simple (no keep-alive
            # / chunked-encoding negotiation).
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass  # silence default per-request logging

            def do_GET(self):
                if self.path.startswith("/stream"):
                    self._serve_stream()
                elif self.path.startswith("/embed") or self.path == "/":
                    self._serve_embed()
                else:
                    self.send_error(404)

            def _serve_embed(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_EMBED_HTML)))
                self.end_headers()
                self.wfile.write(_EMBED_HTML)

            def _serve_stream(self):
                self.send_response(200)
                self.send_header("Cache-Control", "no-cache, private")
                self.send_header("Pragma", "no-cache")
                self.send_header(
                    "Content-Type", "multipart/x-mixed-replace; boundary=frame"
                )
                self.end_headers()
                try:
                    while True:
                        frame = server._frame_source()
                        if frame is not None:
                            data = server._encode(frame)
                            if data is not None:
                                self.wfile.write(b"--frame\r\n")
                                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                                self.wfile.write(
                                    f"Content-Length: {len(data)}\r\n\r\n".encode()
                                )
                                self.wfile.write(data)
                                self.wfile.write(b"\r\n")
                        time.sleep(1.0 / server._fps)
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler

    def start(self):
        """Start serving in a background daemon thread (non-blocking)."""
        if self._thread is not None:
            return
        self._httpd = ThreadingHTTPServer(("0.0.0.0", self.port), self._make_handler())
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        print(f"Video stream serving on http://0.0.0.0:{self.port}/embed", flush=True)

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None
