from flask import Flask, request
from flask_socketio import SocketIO, emit
import socket

app = Flask(__name__)
socketio = SocketIO(app)

# Store all chat history
chat_history = []

# Serve HTML directly from the Python script
@app.route('/')
def index():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Simple Chat</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <h2>💬 Chat</h2>
    <div id="chat" style="border:1px solid black;height:300px;overflow-y:auto;padding:5px;"></div>
    <textarea id="message" placeholder="Type a message..." style="width:100%;height:60px;"></textarea>
    <button onclick="sendMessage()">Send</button>

    <script>
        var socket = io();
        var ipAddress = "";

        // On connection, store our IP from server
        socket.on('set_ip', function(data) {{
            ipAddress = data;
        }});

        // Load old messages
        socket.on('chat_history', function(history) {{
            var chatDiv = document.getElementById('chat');
            chatDiv.innerHTML = "";
            history.forEach(function(msg) {{
                var p = document.createElement('p');
                p.textContent = msg;
                chatDiv.appendChild(p);
            }});
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }});

        // Receive new message
        socket.on('message', function(msg) {{
            var chatDiv = document.getElementById('chat');
            var p = document.createElement('p');
            p.textContent = msg;
            chatDiv.appendChild(p);
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }});

        // Send message function
        function sendMessage() {{
            var messageBox = document.getElementById('message');
            var text = messageBox.value.trim();
            if(text !== "") {{
                socket.emit('message', text);
                messageBox.value = "";
            }}
        }}

        // Handle Enter and Shift+Enter
        document.getElementById('message').addEventListener('keydown', function(e) {{
            if (e.key === "Enter" && !e.shiftKey) {{
                e.preventDefault();
                sendMessage();
            }}
        }});
    </script>
</body>
</html>
"""

# Handle new connection
@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    socketio.emit('set_ip', client_ip, to=request.sid)
    socketio.emit('chat_history', chat_history, to=request.sid)

# Handle incoming message
@socketio.on('message')
def handle_message(msg):
    client_ip = request.remote_addr
    final_msg = f"[{client_ip}] {msg}"
    chat_history.append(final_msg)
    emit('message', final_msg, broadcast=True)

# Get local IP for displaying server URL
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("\n📡 Chat server running!")
    print(f"Access on this device: http://localhost:5000")
    print(f"Access from other devices: http://{local_ip}:5000\n")
    socketio.run(app, host='0.0.0.0', port=5000)
