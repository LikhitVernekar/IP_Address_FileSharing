from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, send
import socket

app = Flask(__name__)
socketio = SocketIO(app)

# Store chat history
messages = []

# Get local IP
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
print(f"Server running at: http://{local_ip}:5000")

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Termux Chat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
    <style>
        body {
            font-family: sans-serif;
            display: flex;
            justify-content: flex-end;
            margin: 0;
            height: 100vh;
        }
        #chat-container {
            width: 30%;
            min-width: 300px;
            height: 100%;
            border-left: 1px solid #ccc;
            display: flex;
            flex-direction: column;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            border-bottom: 1px solid #ccc;
            word-wrap: break-word;
        }
        #input-container {
            display: flex;
            padding: 5px;
            box-sizing: border-box;
        }
        #message {
            flex: 1;
            height: 40px;
            resize: none;
            padding: 5px;
            font-size: 14px;
        }
        #send {
            padding: 5px 10px;
            font-size: 14px;
            margin-left: 5px;
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="messages"></div>
        <div id="input-container">
            <textarea id="message" placeholder="Type your message..." rows="1"></textarea>
            <button id="send">Send</button>
        </div>
    </div>

    <script>
        var socket = io();
        var ipAddress = "";

        fetch('/get_ip').then(res => res.json()).then(data => {
            ipAddress = data.ip;
        });

        socket.on('message', function(msg) {
            var messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML += "<div><b>" + msg.user + ":</b> " + msg.text + "</div>";
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });

        socket.on('load_messages', function(msgs) {
            var messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = "";
            msgs.forEach(function(m) {
                messagesDiv.innerHTML += "<div><b>" + m.user + ":</b> " + m.text + "</div>";
            });
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });

        function sendMessage() {
            var msg = document.getElementById('message').value.trim();
            if (msg !== "") {
                socket.send({user: ipAddress, text: msg});
                document.getElementById('message').value = "";
            }
        }

        document.getElementById('send').onclick = sendMessage;

        document.getElementById('message').addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_template)

@app.route('/get_ip')
def get_ip():
    return {"ip": request.remote_addr}

@socketio.on('connect')
def handle_connect():
    socketio.emit('load_messages', messages, to=request.sid)

@socketio.on('message')
def handle_message(msg):
    messages.append(msg)
    send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
