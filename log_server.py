from flask import Flask, Response, jsonify
import time
import subprocess

app = Flask(__name__)
LOG_FILE = "/srv/hf/ro_index/logs/crawler.log"

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RO-Index Matrix LITE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background-color: #000; color: #0f0; font-family: monospace; margin: 0; padding: 20px; }
            h1 { text-align: center; color: #fff; border-bottom: 1px solid #333; padding-bottom: 10px;}
            #logs { height: 70vh; overflow-y: auto; border: 1px solid #333; padding: 10px; white-space: pre-wrap; color: #ccc; }
            .stat { font-size: 20px; color: #0ff; margin-bottom: 10px; text-align: center; }
        </style>
    </head>
    <body>
        <h1>🕷️ MATRIX LITE</h1>
        <div class="stat" id="stats">Loading...</div>
        <div id="logs"></div>
        <script>
            const eventSource = new EventSource("/stream");
            const logsDiv = document.getElementById("logs");
            eventSource.onmessage = function(event) {
                const newLine = document.createElement("div");
                newLine.textContent = event.data;
                logsDiv.appendChild(newLine);
                logsDiv.scrollTop = logsDiv.scrollHeight;
                if (logsDiv.childElementCount > 100) logsDiv.removeChild(logsDiv.firstChild);
            };
            setInterval(() => {
                fetch('/api/stats').then(r => r.json()).then(data => {
                    document.getElementById('stats').innerText = `PAGINI: ${data.pages} | COADĂ: ${data.queue}`;
                });
            }, 3000);
        </script>
    </body>
    </html>
    """

@app.route('/stream')
def stream():
    def generate():
        with open(LOG_FILE, "r") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                yield f"data: {line}\n\n"
    return Response(generate(), mimetype="text/event-stream")

@app.route('/api/stats')
def stats():
    # Fast count using shell (no heavy python driver overhead)
    try:
        cmd = "mongosh --quiet --port 27018 ro_index_db --eval 'db.crawled_sites.countDocuments({})'"
        pages = subprocess.check_output(cmd, shell=True).decode().strip()
        cmd2 = "mongosh --quiet --port 27018 ro_index_db --eval 'db.crawl_queue.countDocuments({status: \"pending\"})'"
        queue = subprocess.check_output(cmd2, shell=True).decode().strip()
        return jsonify({"pages": pages, "queue": queue})
    except:
        return jsonify({"pages": "?", "queue": "?"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8085)
