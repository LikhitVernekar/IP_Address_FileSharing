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
        #preview-container {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 5px;
        }
        .preview-item {
            position: relative;
            display: inline-block;
        }
        .preview-item img {
            max-width: 50px;
            max-height: 50px;
            border: 1px solid #ccc;
        }
        .remove-btn {
            position: absolute;
            top: -5px;
            right: -5px;
            background: red;
            color: white;
            border: none;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            font-size: 12px;
            cursor: pointer;
        }
        #input {
            height: 50px;
            resize: none;
            padding: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat">
            <div id="messages"></div>
            <form id="form">
                <div id="preview-container"></div>
                <textarea id="input" placeholder="Type message here or drop images..." rows="2"></textarea>
            </form>
        </div>
    </div>
    <script>
        var socket = io();
        var form = document.getElementById('form');
        var input = document.getElementById('input');
        var messages = document.getElementById('messages');
        var previewContainer = document.getElementById('preview-container');
        var pendingFiles = [];

        socket.on('connect', function() {
            socket.emit('request_history');
        });

        socket.on('chat_history', function(history) {
            messages.innerHTML = '';
            history.forEach(function(msg) {
                appendMessage(msg.user, msg.text, msg.images || [], msg.type);
            });
        });

        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        function sendMessage() {
            if (input.value.trim() || pendingFiles.length > 0) {
                var formData = new FormData();
                pendingFiles.forEach(file => {
                    formData.append('files', file);
                });
                formData.append('text', input.value.trim());

                fetch('/upload', { method: 'POST', body: formData });

                input.value = '';
                pendingFiles = [];
                previewContainer.innerHTML = '';
            }
        }

        // Drag & Drop
        input.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        input.addEventListener('drop', function(e) {
            e.preventDefault();
            for (let file of e.dataTransfer.files) {
                if (file.type.startsWith("image/")) {
                    pendingFiles.push(file);
                    showPreview(file);
                }
            }
        });

        function showPreview(file) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var div = document.createElement('div');
                div.classList.add('preview-item');
                var img = document.createElement('img');
                img.src = e.target.result;
                var btn = document.createElement('button');
                btn.textContent = '×';
                btn.classList.add('remove-btn');
                btn.onclick = function() {
                    pendingFiles = pendingFiles.filter(f => f !== file);
                    previewContainer.removeChild(div);
                };
                div.appendChild(img);
                div.appendChild(btn);
                previewContainer.appendChild(div);
            };
            reader.readAsDataURL(file);
        }

        socket.on('message', function(msg) {
            appendMessage(msg.user, msg.text, msg.images || [], msg.type);
        });

        function appendMessage(user, text, images, type) {
            var item = document.createElement('div');
            item.classList.add('message');
            var html = '<b>' + user + ':</b>';
            if (text) html += ' ' + text;
            if (images && images.length > 0) {
                images.forEach(src => {
                    html += '<br><img src="' + src + '" onclick="openImage(this.src)">';
                });
            }
            item.innerHTML = html;
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
    text = request.form.get('text', '')
    files = request.files.getlist('files')
    urls = []
    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        urls.append(f"/uploads/{filename}")

    ip = request.remote_addr
    msg = {"user": ip, "text": text, "images": urls, "type": "mixed"}
    chat_history.append(msg)
    socketio.emit('message', msg)
    return '', 204

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@socketio.on('message')
def handle_message(data):
    ip = request.remote_addr
    msg = {"user": ip, "text": data.get('text', ''), "images": data.get('images', []), "type": data['type']}
    chat_history.append(msg)
    emit('message', msg, broadcast=True)

@socketio.on('request_history')
def send_history():
    emit('chat_history', chat_history)

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Chat server running at: http://{local_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
