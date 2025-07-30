import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib
import cgi

UPLOAD_DIR = "/sdcard/Download/termux"  # Change this as needed
PASSWORD = "letmein"  # Your chosen password

class SimpleUploadServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        # Handle file deletion
        if parsed_path.path == '/delete':
            query = urllib.parse.parse_qs(parsed_path.query)
            filename = query.get("file", [None])[0]
            password = query.get("pass", [""])[0]
            if filename and password == PASSWORD:
                filepath = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return

        # Serve files directly
        file_path = urllib.parse.unquote(parsed_path.path.lstrip("/"))
        full_path = os.path.join(UPLOAD_DIR, file_path)
        if os.path.isfile(full_path):
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            with open(full_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # Main page
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(f"""
        <html>
        <head>
        <style>
        .file-entry {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #ccc;
        }}
        .file-entry div {{
            width: 33%;
            word-break: break-word;
        }}
        /* Modal styles */
        .modal-bg {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0; top: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.3);
            justify-content: center;
            align-items: center;
        }}
        .modal-bg.active {{
            display: flex;
        }}
        .modal-box {{
            background: #fff;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px #0002;
            min-width: 250px;
            position: relative;
        }}
        .modal-box label {{
            display: block;
            margin-bottom: 8px;
        }}
        .modal-box input[type="password"], .modal-box input[type="text"] {{
            width: 100%;
            padding: 6px;
            margin-bottom: 10px;
        }}
        .modal-actions {{
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }}
        .show-pass-btn {{
            background: none;
            border: none;
            cursor: pointer;
            position: absolute;
            right: 35px;
            top: 53px;
            font-size: 14px;
        }}
        </style>
        <script>
        let modalCallback = null;
        let modalType = null;
        let modalFile = null;

        function showPasswordModal(type, file, callback) {{
            modalType = type;
            modalFile = file;
            modalCallback = callback;
            document.getElementById('password-modal-bg').classList.add('active');
            document.getElementById('password-input').value = '';
            document.getElementById('password-input').type = 'password';
            document.getElementById('show-pass-btn').textContent = 'Show';
            document.getElementById('password-input').focus();
        }}

        function hidePasswordModal() {{
            document.getElementById('password-modal-bg').classList.remove('active');
            modalCallback = null;
            modalType = null;
            modalFile = null;
        }}

        function submitPasswordModal() {{
            const pass = document.getElementById('password-input').value;
            if (modalCallback) {{
                modalCallback(pass, modalFile);
            }}
            hidePasswordModal();
        }}

        function togglePassword() {{
            const input = document.getElementById('password-input');
            const btn = document.getElementById('show-pass-btn');
            if (input.type === 'password') {{
                input.type = 'text';
                btn.textContent = 'Hide';
            }} else {{
                input.type = 'password';
                btn.textContent = 'Show';
            }}
        }}

        window.addEventListener('DOMContentLoaded', function() {{
            // Hide modal on click outside
            document.getElementById('password-modal-bg').addEventListener('mousedown', function(e) {{
                if (e.target === this) {{
                    hidePasswordModal();
                }}
            }});
            // Enter key submits
            document.getElementById('password-input').addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') {{
                    submitPasswordModal();
                }}
            }});
        }});

        function askPasswordAndUpload(form) {{
            showPasswordModal('upload', null, function(pass) {{
                if (pass === "{PASSWORD}") {{
                    form.submit();
                }} else {{
                    alert("Wrong password!");
                }}
            }});
            return false; // Prevent default submit
        }}

        function confirmDelete(file) {{
            showPasswordModal('delete', file, function(pass, file) {{
                if (pass === "{PASSWORD}") {{
                    window.location = "/delete?file=" + encodeURIComponent(file) + "&pass=" + encodeURIComponent(pass);
                }} else {{
                    alert("Wrong password!");
                }}
            }});
        }}
        </script>
        </head>
        <body>
            <div style="margin-bottom:20px;">
                <h3>Upload File</h3>
                <form enctype="multipart/form-data" method="post" onsubmit="return askPasswordAndUpload(this);">
                    <input type="file" name="file" required />
                    <input type="submit" value="Upload" />
                </form>
            </div>

            <div>
                <h3>Files</h3>
                <div class="file-entry" style="font-weight:bold;">
                    <div>File Name</div>
                    <div>Size (KB)</div>
                    <div>Action</div>
                </div>
        """.encode())

        for filename in os.listdir(UPLOAD_DIR):
            full_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(full_path):
                encoded_name = urllib.parse.quote(filename)
                size_kb = os.path.getsize(full_path) // 1024
                self.wfile.write(f"""
                    <div class="file-entry">
                        <div><a href='/{encoded_name}' target="_blank">{filename}</a></div>
                        <div>{size_kb} KB</div>
                        <div><a href="#" onclick="confirmDelete('{filename}');return false;" style="color:red;">Delete</a></div>
                    </div>
                """.encode())

        # Password modal HTML
        self.wfile.write(b"""
            </div>
            <div id="password-modal-bg" class="modal-bg">
                <div class="modal-box">
                    <label for="password-input">Enter password:</label>
                    <input id="password-input" type="password" autocomplete="off" />
                    <button type="button" id="show-pass-btn" class="show-pass-btn" onclick="togglePassword()">Show</button>
                    <div class="modal-actions">
                        <button type="button" onclick="submitPasswordModal()">Submit</button>
                        <button type="button" onclick="hidePasswordModal()">Cancel</button>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)

    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type"))
        if ctype == 'multipart/form-data':
            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            pdict['CONTENT-LENGTH'] = int(self.headers.get('Content-length'))
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST'}, keep_blank_values=True)

            if "file" in form:
                uploaded_file = form["file"]
                if uploaded_file.filename:
                    filename = os.path.basename(uploaded_file.filename)
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(uploaded_file.file.read())

        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()


os.chdir(UPLOAD_DIR)
server_address = ("0.0.0.0", 8000)
httpd = HTTPServer(server_address, SimpleUploadServer)
print(f"Serving on http://0.0.0.0:8000/")
httpd.serve_forever()
