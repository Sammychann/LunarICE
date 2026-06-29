import json
import os
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
sys.path.insert(0, str(PARENT))

RUNNING = False
RESULT = {"success": False, "output": "No run yet."}

HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>LunarIce-360 UI</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }
    .card { background: #111827; padding: 1.5rem; border-radius: 12px; max-width: 900px; margin: auto; }
    button { padding: 0.7rem 1rem; border: none; border-radius: 8px; background: #38bdf8; color: #082f49; font-weight: bold; cursor: pointer; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    pre { background: #020617; padding: 1rem; white-space: pre-wrap; border-radius: 8px; max-height: 320px; overflow: auto; }
    .row { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>LunarIce-360</h1>
    <p>Run the synthetic demo pipeline from a simple browser interface.</p>
    <div class=\"row\">
      <button id=\"runBtn\" onclick=\"runPipeline()\">Run pipeline</button>
      <span id=\"status\">Idle</span>
    </div>
    <pre id=\"output\">No output yet.</pre>
    <div id="results" style="display: none; margin-top: 2rem;">
      <h2>Results Summary</h2>
      <img src="/outputs/summary_figure.png" alt="Summary Figure" style="max-width: 100%; border-radius: 8px; border: 1px solid #334155;">
    </div>
  </div>

  <script>
    async function runPipeline() {
      const btn = document.getElementById('runBtn');
      const out = document.getElementById('output');
      const status = document.getElementById('status');
      const resultsDiv = document.getElementById('results');
      
      btn.disabled = true;
      resultsDiv.style.display = 'none';
      status.textContent = 'Running...';
      out.textContent = 'Starting pipeline...';
      try {
        const response = await fetch('/run', { method: 'POST' });
        const data = await response.json();
        out.textContent = data.output || 'Pipeline completed.';
        status.textContent = data.success ? 'Started' : 'Failed';
      } catch (err) {
        out.textContent = 'Error: ' + err;
        status.textContent = 'Failed';
      } finally {
        setTimeout(async () => {
          try {
            const res = await fetch('/status');
            const data = await res.json();
            if (data.result && data.result.output) {
              out.textContent = data.result.output;
              status.textContent = data.running ? 'Running...' : (data.result.success ? 'Completed' : 'Failed');
              
              // Show results image if completed successfully
              if (!data.running && data.result.success) {
                  resultsDiv.style.display = 'block';
                  // Add a cache-busting query parameter to force image reload
                  const img = resultsDiv.querySelector('img');
                  img.src = '/outputs/summary_figure.png?t=' + new Date().getTime();
              }
            }
          } catch (e) {}
          btn.disabled = false;
        }, 1000);
      }
    }
  </script>
</body>
</html>
"""


def run_pipeline_background():
    global RUNNING, RESULT
    RUNNING = True
    RESULT = {"success": False, "output": "Pipeline started..."}

    try:
        command = [sys.executable, '-m', 'BAHood.demo_synthetic']
        completed = subprocess.run(
            command,
            cwd=str(PARENT),
            capture_output=True,
            text=True,
            timeout=None,
        )
        output = completed.stdout + completed.stderr
        RESULT = {
            "success": completed.returncode == 0,
            "output": output if output else "Pipeline completed without additional output.",
        }
    except Exception as exc:
        RESULT = {"success": False, "output": f"Pipeline failed: {exc}"}
    finally:
        RUNNING = False


class LunarUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        elif parsed.path == '/status':
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'running': RUNNING, 'result': RESULT}).encode('utf-8'))
        elif parsed.path.startswith('/outputs/'):
            # Very simple static file serving for the outputs directory
            filename = os.path.basename(parsed.path)
            filepath = os.path.join(PARENT, 'outputs', filename)
            if os.path.exists(filepath):
                self.send_response(HTTPStatus.OK)
                if filename.endswith('.png'):
                    self.send_header('Content-Type', 'image/png')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/run':
            if RUNNING:
                self.send_response(HTTPStatus.ACCEPTED)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'output': 'Pipeline is already running.'}).encode('utf-8'))
                return

            thread = threading.Thread(target=run_pipeline_background, daemon=True)
            thread.start()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'output': 'Pipeline started...'}).encode('utf-8'))
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 8000), LunarUIHandler)
    print('Starting LunarIce-360 UI at http://127.0.0.1:8000')
    webbrowser.open('http://127.0.0.1:8000')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
