from flask import Flask, render_template_string, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

chat_history = []

# Get local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Chat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
    <style>
        body { font-family: sans-serif; margin: 0; }
        #chat-container {
            display: flex;
            justify-content: flex-end;
            height: 100vh;
        }
        #chat {
            border-left: 1px solid #ccc;
            width: 30%;
            display: flex;
            flex-direction: column;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .message {
            margin-bottom: 10px;
            word-wrap: break-word;
        }
        .message img {
            max-width: 100%;
            max-height: 150px;
            display: block;
            margin-top: 5px;
            border: 1px solid #ccc;
        }
        #form {
            display: flex;
            flex-direction: column;
            padding: 5px;
            border-top: 1px solid #ccc;
        }
        #input {
            height: 50px;
            resize: none;
            padding: 5px;
            font-size: 14px;
        }
        #file {
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat">
            <div id="messages"></div>
            <form id="form">
                <textarea id="input" placeholder="Type message here..." rows="2"></textarea>
                <input type="file" id="file" accept="image/*">
            </form>
        </div>
    </div>
    <script>
        var socket = io();
        var form = document.getElementById('form');
        var input = document.getElementById('input');
        var fileInput = document.getElementById('file');
        var messages = document.getElementById('messages');

        socket.on('connect', function() {
            socket.emit('request_history');
        });

        socket.on('chat_history', function(history) {
            messages.innerHTML = '';
            history.forEach(function(msg) {
                appendMessage(msg.user, msg.text, msg.type);
            });
        });

        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim()) {
                    socket.emit('message', {text: input.value, type: 'text'});
                    input.value = '';
                }
            }
        });

        fileInput.addEventListener('change', function() {
            var file = fileInput.files[0];
            if (file) {
                var formData = new FormData();
                formData.append('file', file);
                fetch('/upload', { method: 'POST', body: formData });
                fileInput.value = '';
            }
        });

        socket.on('message', function(msg) {
            appendMessage(msg.user, msg.text, msg.type);
        });

        function appendMessage(user, text, type) {
            var item = document.createElement('div');
            item.classList.add('message');
            if (type === 'text') {
                item.innerHTML = '<b>' + user + ':</b> ' + text;
            } else if (type === 'image') {
                item.innerHTML = '<b>' + user + ':</b><br><img src="' + text + '" onclick="openImage(this.src)">';
            }
            messages.appendChild(item);
            messages.scrollTop = messages.scrollHeight;
        }

        function openImage(src) {
            var overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = 0;
            overlay.style.left = 0;
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.background = 'rgba(0,0,0,0.8)';
            overlay.style.display = 'flex';
            overlay.style.alignItems = 'center';
            overlay.style.justifyContent = 'center';
            overlay.onclick = function() { document.body.removeChild(overlay); };
            var img = document.createElement('img');
            img.src = src;
            img.style.maxWidth = '90%';
            img.style.maxHeight = '90%';
            overlay.appendChild(img);
            document.body.appendChild(overlay);
        }
    </script>
</body>
</html>
""")

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    ip = request.remote_addr
    msg = {"user": ip, "text": f"/uploads/{filename}", "type": "image"}
    chat_history.append(msg)
    socketio.emit('message', msg)
    return '', 204

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@socketio.on('message')
def handle_message(data):
    ip = request.remote_addr
    msg = {"user": ip, "text": data['text'], "type": data['type']}
    chat_history.append(msg)
    emit('message', msg, broadcast=True)

@socketio.on('request_history')
def send_history():
    emit('chat_history', chat_history)

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Chat server running at: http://{local_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
