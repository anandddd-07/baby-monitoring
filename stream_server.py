"""
stream_server.py - a tiny MJPEG video server.

Streamlit sends every image as a separate download, so pushing frames through
Streamlit halves the frame rate and looks choppy. This server keeps one
connection open and streams JPEG frames to the browser like a normal webcam
does, which is much smoother.

The app puts a plain <img> tag pointing at this server on the page, and the
browser keeps the connection open and redraws each frame as it arrives.
"""
import http.server
import socketserver
import threading
import time


class MjpegServer:
    """Serves the latest frame over a multipart MJPEG response."""

    def __init__(self, port=8765, host="127.0.0.1"):
        self.host = host
        self.port = port
        self._frame = None
        self._lock = threading.Lock()
        self._httpd = None

    # ------------------------------------------------------------------ api
    def update(self, jpeg_bytes):
        """Publish a new frame. Called from the detection thread."""
        with self._lock:
            self._frame = jpeg_bytes

    def clear(self):
        with self._lock:
            self._frame = None

    @property
    def url(self):
        return "http://%s:%d/stream" % (self.host, self.port)

    # --------------------------------------------------------------- server
    def start(self):
        """Start serving. Returns True when the server is listening."""
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                self.send_response(200)
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Connection", "close")
                self.send_header(
                    "Content-Type", "multipart/x-mixed-replace; boundary=frame"
                )
                self.end_headers()
                self.close_connection = True

                last = None
                while True:
                    with server._lock:
                        frame = server._frame

                    if frame is None:
                        time.sleep(0.05)
                        continue

                    if frame is not last:
                        last = frame
                        try:
                            self.wfile.write(
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                            )
                            self.wfile.write(frame)
                            self.wfile.write(b"\r\n")
                        except (BrokenPipeError, ConnectionResetError, OSError):
                            break
                    else:
                        time.sleep(0.01)

            def log_message(self, *args):
                pass

        class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
            daemon_threads = True

        try:
            self._httpd = ThreadedServer((self.host, self.port), Handler)
        except OSError:
            # Port already taken, try the next few.
            for offset in range(1, 20):
                try:
                    self._httpd = ThreadedServer(
                        (self.host, self.port + offset), Handler
                    )
                    self.port = self.port + offset
                    break
                except OSError:
                    continue
            else:
                return False

        thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        thread.start()
        return True

    def stop(self):
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
