from flask import Flask, render_template_string, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
import socket
import uuid

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, interactive-widget=resizes-content">
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
            cursor: pointer;
        }
        .file-link {
            display: inline-block;
            margin-top: 5px;
            padding: 8px 12px;
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            font-size: 13px;
        }
        .file-link:hover {
            background: #e0e0e0;
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
        .preview-file {
            max-width: 120px;
            padding: 5px 8px;
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 3px;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
        
        /* Upload button styles */
        .upload-btn {
            background: #f0f0f0;
            border: 1px solid #ccc;
            padding: 8px 12px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .upload-btn:hover {
            background: #e0e0e0;
        }
        
        .file-input {
            display: none;
        }
        
        .form-controls {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        
        .form-controls textarea {
            flex: 1;
        }
        
        /* Paste indicator */
        .paste-indicator {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 20px 40px;
            border-radius: 8px;
            font-size: 16px;
            z-index: 3000;
            display: none;
        }
        
        .paste-indicator.show {
            display: block;
            animation: fadeInOut 1.5s;
        }
        
        @keyframes fadeInOut {
            0% { opacity: 0; }
            20% { opacity: 1; }
            80% { opacity: 1; }
            100% { opacity: 0; }
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
        
        /* Mobile messages area */
        #messages-mobile {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            padding-bottom: 120px;
        }
        
        /* Mobile form */
        #form-mobile {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            display: flex;
            flex-direction: column;
            padding: 10px;
            background: white;
            border-top: 1px solid #ccc;
            flex-shrink: 0;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
            z-index: 10;
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
            padding: 8px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
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
    </style>
</head>
<body>
    <!-- Paste Indicator -->
    <div id="paste-indicator" class="paste-indicator">Image pasted! 📋</div>
    
    <!-- Original Desktop Chat -->
    <div id="chat-container">
        <div id="chat">
            <div id="messages"></div>
            <form id="form">
                <div id="preview-container"></div>
                <div class="form-controls">
                    <textarea id="input" placeholder="Type message here, drop/paste images..." rows="2"></textarea>
                    <input type="file" id="file-input" class="file-input" multiple>
                    <button type="button" class="upload-btn" onclick="document.getElementById('file-input').click()">📎</button>
                </div>
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
            <div class="form-controls">
                <textarea id="input-mobile" placeholder="Type message here, drop/paste images..." rows="2"></textarea>
                <input type="file" id="file-input-mobile" class="file-input" multiple>
                <button type="button" class="upload-btn" onclick="document.getElementById('file-input-mobile').click()">📎</button>
            </div>
        </form>
    </div>
    
    <script>
        var socket = io();
        var pendingFiles = [];
        var isMobileOverlayOpen = false;
        
        // Original desktop functionality
        var form = document.getElementById('form');
        var input = document.getElementById('input');
        var messages = document.getElementById('messages');
        var previewContainer = document.getElementById('preview-container');
        var pasteIndicator = document.getElementById('paste-indicator');

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
        
        // File input handler for desktop
        document.getElementById('file-input').addEventListener('change', function(e) {
            for (let file of e.target.files) {
                pendingFiles.push(file);
                showPreview(file, previewContainer);
            }
            e.target.value = '';
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
                pendingFiles.push(file);
                showPreview(file, previewContainer);
            }
        });
        
        // PASTE functionality for desktop
        document.addEventListener('paste', function(e) {
            if (window.innerWidth >= 768 || isMobileOverlayOpen) {
                var items = e.clipboardData.items;
                var hasImage = false;
                
                for (var i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        hasImage = true;
                        var blob = items[i].getAsFile();
                        var uniqueName = 'pasted-image-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9) + '.png';
                        var file = new File([blob], uniqueName, { type: blob.type });
                        
                        pendingFiles.push(file);
                        
                        var currentPreview = isMobileOverlayOpen ? 
                            document.getElementById('preview-container-mobile') : 
                            previewContainer;
                        showPreview(file, currentPreview);
                    }
                }
                
                if (hasImage) {
                    showPasteIndicator();
                    e.preventDefault();
                }
            }
        });
        
        function showPasteIndicator() {
            pasteIndicator.classList.add('show');
            setTimeout(function() {
                pasteIndicator.classList.remove('show');
            }, 1500);
        }

        function showPreview(file, container) {
            var div = document.createElement('div');
            div.classList.add('preview-item');
            
            if (file.type.startsWith('image/')) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var img = document.createElement('img');
                    img.src = e.target.result;
                    div.appendChild(img);
                };
                reader.readAsDataURL(file);
            } else {
                var fileLabel = document.createElement('div');
                fileLabel.classList.add('preview-file');
                fileLabel.textContent = file.name;
                div.appendChild(fileLabel);
            }
            
            var btn = document.createElement('button');
            btn.textContent = '×';
            btn.classList.add('remove-btn');
            btn.onclick = function() {
                pendingFiles = pendingFiles.filter(f => f !== file);
                container.removeChild(div);
            };
            div.appendChild(btn);
            container.appendChild(div);
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
                images.forEach(fileInfo => {
                    if (fileInfo.type === 'image') {
                        html += '<br><img src="' + fileInfo.url + '" onclick="openImage(this.src)">';
                    } else {
                        html += '<br><a href="' + fileInfo.url + '" class="file-link" target="_blank" download>📄 ' + fileInfo.name + '</a>';
                    }
                });
            }
            item.innerHTML = html;
            
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
                    pendingFiles.push(file);
                    showPreview(file, newPreview);
                }
            });
            
            // Handle keyboard visibility
            newInput.addEventListener('focus', function() {
                setTimeout(function() {
                    newInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 300);
            });
            
            // File input handler for mobile
            var mobileFileInput = document.getElementById('file-input-mobile');
            var newFileInput = mobileFileInput.cloneNode(true);
            mobileFileInput.parentNode.replaceChild(newFileInput, mobileFileInput);
            
            newFileInput.addEventListener('change', function(e) {
                for (let file of e.target.files) {
                    pendingFiles.push(file);
                    showPreview(file, newPreview);
                }
                e.target.value = '';
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
    file_infos = []
    
    for file in files:
        filename = secure_filename(file.filename)
        if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        file_type = 'image' if file.content_type and file.content_type.startswith('image/') else 'file'
        file_infos.append({
            'url': f"/uploads/{filename}",
            'name': filename,
            'type': file_type
        })

    ip = request.remote_addr
    msg = {"user": ip, "text": text, "images": file_infos, "type": "mixed"}
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
