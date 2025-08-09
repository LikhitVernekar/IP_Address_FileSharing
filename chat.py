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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
    <style>
        body { font-family: sans-serif; margin: 0; }
        
        /* Original desktop chat styles */
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
        
        /* Mobile floating button - minimal design */
        #mobile-chat-toggle {
            display: none;
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            color: #333;
            font-size: 18px;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 1000;
            font-family: sans-serif;
        }
        
        /* Mobile fullscreen overlay */
        #mobile-chat-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            height: 100dvh; /* For better mobile support */
            background: white;
            z-index: 1001;
            flex-direction: column;
        }
        
        #mobile-chat-overlay.active {
            display: flex;
        }
        
        /* Mobile header with close button */
        #mobile-chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #ccc;
            flex-shrink: 0;
        }
        
        #close-chat {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            padding: 5px;
            color: #666;
        }
        
        /* Mobile messages area - same styling as desktop */
        #messages-mobile {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        /* Mobile form - same styling as desktop */
        #form-mobile {
            display: flex;
            flex-direction: column;
            padding: 5px;
            border-top: 1px solid #ccc;
            flex-shrink: 0;
        }
        
        #preview-container-mobile {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 5px;
        }
        
        #input-mobile {
            height: 50px;
            resize: none;
            padding: 5px;
            font-size: 16px; /* Prevents zoom on iOS */
        }
        
        /* Show mobile elements only on mobile */
        @media (max-width: 767px) {
            #chat-container {
                display: none;
            }
            
            #mobile-chat-toggle {
                display: block;
            }
        }
        
        /* Hide mobile elements on desktop */
        @media (min-width: 768px) {
            #mobile-chat-toggle,
            #mobile-chat-overlay {
                display: none !important;
            }
        }
        
        /* Handle keyboard on mobile */
        @media (max-width: 767px) {
            #mobile-chat-overlay {
                height: 100vh;
                height: 100dvh;
            }
            
            /* When keyboard opens, ensure entire form is above keyboard */
            .keyboard-open #mobile-chat-overlay {
                padding-bottom: 20px; /* Extra space above keyboard */
            }
            
            .keyboard-open #form-mobile {
                position: fixed;
                bottom: 20px; /* Always stay 20px above keyboard */
                left: 0;
                right: 0;
                background: white;
                border-top: 1px solid #ccc;
                z-index: 10;
                /* Ensure the entire form including border is visible */
                box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
            }
            
            .keyboard-open #messages-mobile {
                /* Adjust messages area to not overlap with fixed form */
                padding-bottom: 80px; /* Space for the fixed form */
            }
        }
    </style>
</head>
<body>
    <!-- Original Desktop Chat (unchanged) -->
    <div id="chat-container">
        <div id="chat">
            <div id="messages"></div>
            <form id="form">
                <div id="preview-container"></div>
                <textarea id="input" placeholder="Type message here or drop images..." rows="2"></textarea>
            </form>
        </div>
    </div>
    
    <!-- Mobile Chat Button -->
    <button id="mobile-chat-toggle">Chat</button>
    
    <!-- Mobile Chat Overlay -->
    <div id="mobile-chat-overlay">
        <div id="mobile-chat-header">
            <span>Chat</span>
            <button id="close-chat">×</button>
        </div>
        <div id="messages-mobile"></div>
        <form id="form-mobile">
            <div id="preview-container-mobile"></div>
            <textarea id="input-mobile" placeholder="Type message here or drop images..." rows="2"></textarea>
        </form>
    </div>
    
    <script>
        var socket = io();
        var pendingFiles = [];
        var isMobileOverlayOpen = false;
        
        // Original desktop functionality (unchanged)
        var form = document.getElementById('form');
        var input = document.getElementById('input');
        var messages = document.getElementById('messages');
        var previewContainer = document.getElementById('preview-container');

        socket.on('connect', function() {
            socket.emit('request_history');
        });

        socket.on('chat_history', function(history) {
            messages.innerHTML = '';
            document.getElementById('messages-mobile').innerHTML = '';
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
            var currentInput = isMobileOverlayOpen ? document.getElementById('input-mobile') : input;
            var currentPreview = isMobileOverlayOpen ? document.getElementById('preview-container-mobile') : previewContainer;
            
            if (currentInput.value.trim() || pendingFiles.length > 0) {
                var formData = new FormData();
                pendingFiles.forEach(file => {
                    formData.append('files', file);
                });
                formData.append('text', currentInput.value.trim());

                fetch('/upload', { method: 'POST', body: formData });

                currentInput.value = '';
                pendingFiles = [];
                currentPreview.innerHTML = '';
            }
        }

        // Drag & Drop for desktop
        input.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        input.addEventListener('drop', function(e) {
            e.preventDefault();
            for (let file of e.dataTransfer.files) {
                if (file.type.startsWith("image/")) {
                    pendingFiles.push(file);
                    showPreview(file, previewContainer);
                }
            }
        });

        function showPreview(file, container) {
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
                    container.removeChild(div);
                };
                div.appendChild(img);
                div.appendChild(btn);
                container.appendChild(div);
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
            
            // Add to both desktop and mobile
            messages.appendChild(item.cloneNode(true));
            document.getElementById('messages-mobile').appendChild(item);
            
            messages.scrollTop = messages.scrollHeight;
            document.getElementById('messages-mobile').scrollTop = document.getElementById('messages-mobile').scrollHeight;
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
            overlay.style.zIndex = '2000';
            overlay.onclick = function() { document.body.removeChild(overlay); };
            var img = document.createElement('img');
            img.src = src;
            img.style.maxWidth = '90%';
            img.style.maxHeight = '90%';
            overlay.appendChild(img);
            document.body.appendChild(overlay);
        }
        
        // Mobile chat functionality
        document.getElementById('mobile-chat-toggle').addEventListener('click', function() {
            document.getElementById('mobile-chat-overlay').classList.add('active');
            isMobileOverlayOpen = true;
            setupMobileEvents();
        });
        
        document.getElementById('close-chat').addEventListener('click', function() {
            document.getElementById('mobile-chat-overlay').classList.remove('active');
            isMobileOverlayOpen = false;
        });
        
        function setupMobileEvents() {
            var mobileForm = document.getElementById('form-mobile');
            var mobileInput = document.getElementById('input-mobile');
            var mobilePreview = document.getElementById('preview-container-mobile');
            
            // Clear any existing event listeners by replacing the form
            var newForm = mobileForm.cloneNode(true);
            mobileForm.parentNode.replaceChild(newForm, mobileForm);
            
            var newInput = newForm.querySelector('#input-mobile');
            var newPreview = newForm.querySelector('#preview-container-mobile');
            
            newForm.addEventListener('submit', function(e) {
                e.preventDefault();
            });

            newInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            // Mobile drag & drop
            newInput.addEventListener('dragover', function(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
            });

            newInput.addEventListener('drop', function(e) {
                e.preventDefault();
                for (let file of e.dataTransfer.files) {
                    if (file.type.startsWith("image/")) {
                        pendingFiles.push(file);
                        showPreview(file, newPreview);
                    }
                }
            });
            
            // Simple keyboard handling - no viewport manipulation
            newInput.addEventListener('focus', function() {
                document.body.classList.add('keyboard-open');
            });
            
            newInput.addEventListener('blur', function() {
                document.body.classList.remove('keyboard-open');
            });
            
            // Ensure input stays functional after sending messages
            newInput.addEventListener('input', function() {
                // Keep input active and responsive
            });
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
