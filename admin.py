from flask import Flask, request, render_template_string, send_from_directory, session
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room
import os, datetime, uuid, threading, time
from werkzeug.utils import secure_filename

UPLOAD_DIR = "uploads"
app = Flask(__name__)
app.config['SECRET_KEY'] = "secret"

# Tuning ping to reduce spurious disconnects
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_interval=20,   # server ping to clients
    ping_timeout=25,    # wait for pong
    cookie=None         # Socket.IO won’t overwrite Flask session cookie
)

# State
active_visitors = {}      # {visitor_id: {...}}
admin_connections = {}    # {sid: {...}}

# Settings
INACTIVITY_SECONDS = 20
CLEANUP_INTERVAL = 3

def now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(fmt)

def update_visitor_activity(visitor_id, current_page=None, ua=None, ip=None):
    now = datetime.datetime.now()
    prev = active_visitors.get(visitor_id, {})
    joined_at = prev.get("joined_at", now_str())
    active_visitors[visitor_id] = {
        "visitor_id": visitor_id,
        "ip": ip or prev.get("ip") or request.headers.get("X-Forwarded-For", request.remote_addr),
        "last_seen": now_str(),
        "current_page": current_page or prev.get("current_page", "/"),
        "user_agent": ua or prev.get("user_agent", request.headers.get("User-Agent", "Unknown")),
        "timestamp": now.timestamp(),
        "joined_at": joined_at
    }

def broadcast_all():
    payload = {
        'all_visitors': list(active_visitors.values()),
        'admin_users': list(admin_connections.values())
    }
    # Emit to admin namespace only
    socketio.emit('visitor_update', payload, namespace='/admin-io')

def cleanup_inactive_visitors():
    while True:
        try:
            ts = datetime.datetime.now().timestamp()
            to_remove = [vid for vid, data in list(active_visitors.items())
                         if ts - data.get("timestamp", ts) > INACTIVITY_SECONDS]
            for vid in to_remove:
                active_visitors.pop(vid, None)
            if to_remove:
                broadcast_all()
        except Exception as e:
            print("Cleanup error:", e)
        time.sleep(CLEANUP_INTERVAL)

threading.Thread(target=cleanup_inactive_visitors, daemon=True).start()

# Namespaces
class SiteNamespace(Namespace):
    namespace = '/site-io'

    def on_connect(self):
        # Ensure a session visitor_id
        if 'visitor_id' not in session:
            session['visitor_id'] = str(uuid.uuid4())
        # Do not broadcast from here; wait for client page info
        emit('ack', {'status': 'connected'})

    def on_disconnect(self):
        # Do nothing here; a visitor reload can briefly disconnect
        pass

    def on_visitor_connected(self, data):
        vid = session.get('visitor_id')
        page = (data or {}).get('page') or '/'
        ua = (data or {}).get('user_agent')
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        update_visitor_activity(vid, current_page=page, ua=ua, ip=ip)
        broadcast_all()

    def on_heartbeat(self, data):
        vid = session.get('visitor_id')
        if not vid:
            # Edge case: if session lost, assign a new one
            session['visitor_id'] = str(uuid.uuid4())
            vid = session['visitor_id']
        page = (data or {}).get('page')
        ua = (data or {}).get('user_agent')
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        update_visitor_activity(vid, current_page=page, ua=ua, ip=ip)
        # Throttle broadcast to admin: emit only if we want very live; comment out to reduce spam
        broadcast_all()

    def on_visitor_disconnected(self):
        vid = session.get('visitor_id')
        if vid in active_visitors:
            active_visitors.pop(vid, None)
            broadcast_all()

class AdminNamespace(Namespace):
    namespace = '/admin-io'

    def on_connect(self):
        # Track each admin by sid; do not tie removal to visitor state
        admin_connections[request.sid] = {
            "sid": request.sid,
            "visitor_id": session.get('visitor_id'),  # may be None, that’s fine
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "connected_at": now_str("%H:%M:%S")
        }
        # Send immediate sync so the admin sees themselves instantly
        emit('visitor_update', {
            'all_visitors': list(active_visitors.values()),
            'admin_users': list(admin_connections.values())
        })
        # Also broadcast to all admins so counts update everywhere
        broadcast_all()

    def on_disconnect(self):
        admin_connections.pop(request.sid, None)
        broadcast_all()

    def on_heartbeat(self, data):
        # Admin heartbeat to keep socket active; do nothing else
        pass

# Register namespaces
socketio.on_namespace(SiteNamespace('/site-io'))
socketio.on_namespace(AdminNamespace('/admin-io'))

# Shared page script for visitors (site namespace)
visitor_page_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
  var siteSocket = io('/site-io', {
    transports: ['websocket','polling'],
    withCredentials: true
  });

  function sendVisitorHeartbeat() {
    siteSocket.emit('heartbeat', {
      page: window.location.pathname,
      user_agent: navigator.userAgent
    });
  }

  siteSocket.on('connect', function() {
    siteSocket.emit('visitor_connected', {
      page: window.location.pathname,
      user_agent: navigator.userAgent
    });
  });

  setInterval(sendVisitorHeartbeat, 5000);

  window.addEventListener('beforeunload', function() {
    try { siteSocket.emit('visitor_disconnected'); } catch(e) {}
  });
</script>
"""

# Admin page script (admin namespace)
admin_page_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
  var adminSocket = io('/admin-io', {
    transports: ['websocket','polling'],
    withCredentials: true
  });

  adminSocket.on('visitor_update', function(data) {
    document.getElementById('total-visitors').textContent = data.all_visitors.length;
    var tbody = document.querySelector('#visitors-table tbody');
    tbody.innerHTML = '';
    data.all_visitors.forEach(function(v) {
      var row = document.createElement('tr');
      row.innerHTML =
        '<td>' + (v.visitor_id || '').substring(0,8) + '</td>' +
        '<td>' + (v.ip || '') + '</td>' +
        '<td>' + (v.current_page || '') + '</td>' +
        '<td>' + (v.joined_at || '') + '</td>' +
        '<td>' + (v.last_seen || '') + '</td>' +
        '<td>' + (v.user_agent || '') + '</td>';
      tbody.appendChild(row);
    });

    var atbody = document.querySelector('#admins-table tbody');
    atbody.innerHTML = '';
    data.admin_users.forEach(function(a) {
      var row = document.createElement('tr');
      row.innerHTML =
        '<td>' + (a.sid || '').substring(0,8) + '</td>' +
        '<td>' + (a.visitor_id ? a.visitor_id.substring(0,8) : 'N/A') + '</td>' +
        '<td>' + (a.ip || '') + '</td>' +
        '<td>' + (a.connected_at || '') + '</td>';
      atbody.appendChild(row);
    });
  });

  // Keep admin connection active
  setInterval(function(){
    adminSocket.emit('heartbeat', { t: Date.now() });
  }, 8000);
</script>
"""

# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        for f in request.files.getlist("file"):
            if f.filename:
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                f.save(os.path.join(UPLOAD_DIR, secure_filename(f.filename)))
    files = os.listdir(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else []
    template = """
      <h1>Home - File Upload</h1>
      <form method="POST" enctype="multipart/form-data">
          <input type="file" name="file" multiple>
          <input type="submit" value="Upload">
      </form>
      <ul>
          {% for file in files %}
              <li><a href="/download/{{ file }}">{{ file }}</a></li>
          {% endfor %}
      </ul>
      <p><a href="/admin">Admin Panel</a> | <a href="/test">Test</a> | <a href="/another">Another</a></p>
    """ + visitor_page_script
    return render_template_string(template, files=files)

@app.route("/test")
def test_page():
    template = """
      <h1>Test Page</h1>
      <p>Demo page for visitor tracking.</p>
      <p><a href="/">Home</a> | <a href="/admin">Admin Panel</a> | <a href="/another">Another</a></p>
    """ + visitor_page_script
    return render_template_string(template)

@app.route("/another")
def another_page():
    template = """
      <h1>Another Page</h1>
      <p>Another demo page.</p>
      <p><a href="/">Home</a> | <a href="/admin">Admin Panel</a> | <a href="/test">Test</a></p>
    """ + visitor_page_script
    return render_template_string(template)

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/admin")
def admin():
    template = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Panel - Live Visitors</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background: #f2f2f2; }
      </style>
    </head>
    <body>
      <h1>Admin Dashboard</h1>
      <p>Total Active Visitors: <span id="total-visitors">0</span></p>

      <h2>Visitors</h2>
      <table id="visitors-table">
        <thead>
          <tr>
            <th>Visitor ID</th>
            <th>IP</th>
            <th>Current Page</th>
            <th>Joined At</th>
            <th>Last Seen</th>
            <th>User Agent</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>

      <h2>Admin Connections</h2>
      <table id="admins-table">
        <thead>
          <tr>
            <th>SID</th>
            <th>Visitor ID</th>
            <th>IP</th>
            <th>Connected At</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    """ + admin_page_script + """
    </body>
    </html>
    """
    return render_template_string(template)

if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # For Android/Termux or proxies, 0.0.0.0 is fine
    socketio.run(app, host="0.0.0.0", port=8000, debug=True)
