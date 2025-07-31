import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib
import cgi
import datetime

UPLOAD_DIR = "/sdcard/Download/termux"  # Change this as needed
PASSWORD = "letmein"  # Your chosen password

def safe_join(base, *paths):
    # Prevent directory traversal outside UPLOAD_DIR
    abs_base = os.path.abspath(base)
    dest = os.path.abspath(os.path.join(base, *paths))
    if os.path.commonpath([abs_base, dest]) != abs_base:
        raise ValueError("Blocked directory traversal")
    return dest

class SimpleUploadServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        req_path = urllib.parse.unquote(parsed_path.path.lstrip("/"))
        abs_path = safe_join(UPLOAD_DIR, req_path) if req_path else UPLOAD_DIR

        # --- Handle file deletion ---
        if parsed_path.path == '/delete':
            query = urllib.parse.parse_qs(parsed_path.query)
            filename = query.get("file", [None])[0]
            password = query.get("pass", [""])[0]
            curdir = query.get("dir", [""])[0]
            if filename and password == PASSWORD:
                try:
                    target = safe_join(UPLOAD_DIR, curdir, filename)
                    if os.path.isfile(target):
                        os.remove(target)
                except Exception:
                    pass
            redirect_path = f"/{curdir}".rstrip("/") if curdir else "/"
            self.send_response(303)
            self.send_header("Location", redirect_path)
            self.end_headers()
            return

        # --- Serve a file download ---
        if os.path.isfile(abs_path):
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(abs_path)}"')
            self.end_headers()
            with open(abs_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # --- Directory listing page ---
        try:
            entries = os.listdir(abs_path)
        except Exception:
            self.send_error(404)
            return

        rel_dir = req_path.rstrip('/')  # For URLs
        curdir_param = rel_dir

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
            width: 25%;  
            word-break: break-word;  
        }}  
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
        .modal-error {{  
            color: #d32f2f;  
            font-size: 12px;  
            margin-bottom: 10px;  
            display: none;  
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
        .upload-container {{  
            display: flex;  
            align-items: flex-start;  
            gap: 30px;  
            margin-bottom: 20px;  
        }}  
        .upload-form-section {{  
            flex: 0 0 auto;  
        }}  
        .progress-container {{  
            flex: 0 0 25%;  
            display: block;  
            visibility: hidden;  
            min-width: 200px;  
        }}  
        .progress-container.active {{  
            visibility: visible;  
        }}  
        .progress-bar-bg {{  
            width: 100%;  
            background: #eee;  
            border-radius: 5px;  
            height: 18px;  
            margin-bottom: 4px;  
        }}  
        .progress-bar-fill {{  
            height: 100%;  
            background: #4caf50;  
            border-radius: 5px;  
            width: 0%;  
            transition: width 0.2s;  
        }}  
        .progress-text {{  
            font-size: 13px;  
        }}  
        .clear-file-btn {{  
            margin-left: 8px;  
            background: #eee;  
            border: 1px solid #ccc;  
            border-radius: 3px;  
            cursor: pointer;  
            font-size: 12px;  
            padding: 2px 6px;  
        }}  
        </style>  
        <script>  
        let modalCallback = null;  
        let modalType = null;  
        let modalFile = null;  
        let cur_dir = {repr(curdir_param)};
        function showPasswordModal(type, file, callback) {{  
            modalType = type;  
            modalFile = file;  
            modalCallback = callback;  
            document.getElementById('password-modal-bg').classList.add('active');  
            document.getElementById('password-input').value = '';  
            document.getElementById('password-input').type = 'password';  
            document.getElementById('show-pass-btn').textContent = 'Show';  
            document.getElementById('modal-error').style.display = 'none';  
            document.getElementById('password-input').focus();  
        }}  
        function hidePasswordModal() {{  
            document.getElementById('password-modal-bg').classList.remove('active');  
            document.getElementById('modal-error').style.display = 'none';  
            modalCallback = null;  
            modalType = null;  
            modalFile = null;  
        }}  
        function submitPasswordModal() {{  
            const pass = document.getElementById('password-input').value;  
            if (modalCallback) {{  
                modalCallback(pass, modalFile);  
            }}  
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
        function showError(message) {{  
            const errorDiv = document.getElementById('modal-error');  
            errorDiv.textContent = message;  
            errorDiv.style.display = 'block';  
        }}  
        window.addEventListener('DOMContentLoaded', function() {{  
            document.getElementById('password-modal-bg').addEventListener('mousedown', function(e) {{  
                if (e.target === this) {{  
                    hidePasswordModal();  
                }}  
            }});  
            document.getElementById('password-input').addEventListener('keydown', function(e) {{  
                if (e.key === 'Enter') {{  
                    submitPasswordModal();  
                }}  
            }});  
            // Progress bar logic  
            const uploadForm = document.getElementById('upload-form');  
            const fileInput = document.getElementById('file-input');  
            const clearBtn = document.getElementById('clear-file-btn');  
            const progressContainer = document.getElementById('progress-container');  
            const progressBar = document.getElementById('progress-bar-fill');  
            const progressText = document.getElementById('progress-text');  
            clearBtn.onclick = function(e) {{  
                fileInput.value = '';  
                clearBtn.style.display = 'none';  
            }};  
            fileInput.onchange = function() {{  
                clearBtn.style.display = fileInput.value ? 'inline-block' : 'none';  
            }};  
            uploadForm.onsubmit = function(e) {{  
                e.preventDefault();  
                askPasswordAndUpload();  
                return false;  
            }};  
        }});  
        function askPasswordAndUpload() {{  
            showPasswordModal('upload', null, function(pass) {{  
                if (pass === "{PASSWORD}") {{  
                    hidePasswordModal();  
                    uploadMultipleFiles(pass);  
                }} else {{  
                    showError("Wrong password!");  
                }}  
            }});  
            return false;  
        }}  
        function uploadMultipleFiles(pass) {{  
            const fileInput = document.getElementById('file-input');  
            const files = Array.from(fileInput.files);  
            if (files.length === 0) return;  
            let currentIndex = 0;  
            const totalFiles = files.length;  
            document.getElementById('progress-container').classList.add('active');  
            function uploadNextFile() {{  
                if (currentIndex >= totalFiles) {{  
                    document.getElementById('progress-container').classList.remove('active');  
                    document.getElementById('progress-bar-fill').style.width = '0%';  
                    document.getElementById('progress-text').textContent = '';  
                    document.getElementById('current-file').textContent = '';  
                    window.location.reload();  
                    return;  
                }}  
                const file = files[currentIndex];  
                const formData = new FormData();  
                formData.append('file', file);  
                formData.append('curdir', cur_dir);  
                const xhr = new XMLHttpRequest();  
                xhr.open('POST', '/', true);  
                xhr.upload.addEventListener('progress', function(event) {{  
                    if (event.lengthComputable) {{  
                        const percent = Math.round((event.loaded / event.total) * 100);  
                        document.getElementById('progress-bar-fill').style.width = percent + '%';  
                        document.getElementById('current-file').textContent = "Uploading: " + file.name + " (" + (currentIndex + 1) + "/" + totalFiles + ")";  
                        document.getElementById('progress-text').textContent =  
                            (event.loaded / (1024*1024)).toFixed(2) + ' MB / ' + (event.total / (1024*1024)).toFixed(2) + ' MB';  
                    }}  
                }});  
                xhr.onload = function() {{  
                    if (xhr.status === 200 || xhr.status === 303) {{  
                        currentIndex++;  
                        setTimeout(uploadNextFile, 100);  
                    }} else {{  
                        alert('Upload failed for ' + file.name);  
                        document.getElementById('progress-container').classList.remove('active');  
                    }}  
                }};  
                xhr.onerror = function() {{  
                    alert('Upload error for ' + file.name);  
                    document.getElementById('progress-container').classList.remove('active');  
                }};  
                xhr.send(formData);  
            }}  
            uploadNextFile();  
        }}  
        function confirmDelete(file) {{  
            showPasswordModal('delete', file, function(pass, file) {{  
                if (pass === "{PASSWORD}") {{  
                    hidePasswordModal();  
                    let p = "/delete?file=" + encodeURIComponent(file) + "&pass=" + encodeURIComponent(pass);  
                    if (cur_dir) p += "&dir=" + encodeURIComponent(cur_dir);  
                    window.location = p;  
                }} else {{  
                    showError("Wrong password!");  
                }}  
            }});  
        }}  
        </script>  
        </head>  
        <body>  
            <div class="upload-container">  
                <div class="upload-form-section">  
                    <h3>Upload File</h3>  
                    <form id="upload-form" enctype="multipart/form-data" method="post">  
                        <input id="file-input" type="file" name="file" multiple required />  
                        <button type="button" id="clear-file-btn" class="clear-file-btn" style="display:none;">Clear</button>  
                        <input type="submit" value="Upload" />  
                    </form>  
                </div>  
                <div id="progress-container" class="progress-container">  
                    <h3>Upload Progress</h3>  
                    <div id="current-file" style="font-size: 12px; margin-bottom: 5px;"></div>
                    <div class="progress-bar-bg">  
                        <div id="progress-bar-fill" class="progress-bar-fill"></div>  
                    </div>  
                    <div id="progress-text" class="progress-text"></div>  
                </div>  
            </div>  
            <div>  
                <h3>Files</h3>  
                <div class="file-entry" style="font-weight:bold;">  
                    <div>File Name</div>  
                    <div>Date Modified</div>  
                    <div>Size (KB)</div>  
                    <div>Action</div>  
                </div>  
        """.encode())

        # --- Parent directory link if not at root ---
        if rel_dir:
            parent = os.path.dirname(rel_dir.rstrip("/"))
            parent_href = urllib.parse.quote(parent + "/") if parent else ""
            self.wfile.write(f"""<div class="file-entry">
                <div><a href='/{parent_href}'>.. (parent directory)</a></div>
                <div></div><div></div><div></div>
            </div>""".encode())

        # --- Show folders first, then files, just like your original layout ---
        folders, files = [], []
        for entry in sorted(entries):
            entry_abs = os.path.join(abs_path, entry)
            # Only show visible (non-hidden) files/folders (optional)
            if os.path.isdir(entry_abs):
                folders.append(entry)
            elif os.path.isfile(entry_abs):
                files.append(entry)

        # Folders as links
        for folder in folders:
            entry_rel = os.path.join(rel_dir, folder) if rel_dir else folder
            href = urllib.parse.quote(entry_rel + "/")
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(abs_path, folder))
            ).strftime('%Y-%m-%d %H:%M:%S')
            self.wfile.write(f"""<div class="file-entry">
                <div><a href='/{href}'>{folder}/</a></div>
                <div>{mtime}</div>
                <div>--</div>
                <div></div>
            </div>""".encode())

        # Files
        for entry in files:
            entry_rel = os.path.join(rel_dir, entry) if rel_dir else entry
            encoded_name = urllib.parse.quote(entry_rel)
            entry_abs = os.path.join(abs_path, entry)
            size_kb = os.path.getsize(entry_abs) // 1024
            modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(entry_abs)).strftime('%Y-%m-%d %H:%M:%S')
            self.wfile.write(f"""<div class="file-entry">  
                <div><a href='/{encoded_name}' target="_blank">{entry}</a></div>  
                <div>{modified_time}</div>  
                <div>{size_kb} KB</div>  
                <div><a href="#" onclick="confirmDelete('{entry}');return false;" style="color:red;">Delete</a></div>  
            </div>""".encode())

        self.wfile.write(b"""  
            </div>  
            <div id="password-modal-bg" class="modal-bg">  
                <div class="modal-box">  
                    <label for="password-input">Enter password:</label>  
                    <div id="modal-error" class="modal-error"></div>  
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
            curdir = ""
            if "curdir" in form:
                curdir = form["curdir"].value
            upload_dir = safe_join(UPLOAD_DIR, curdir)
            if "file" in form:
                if isinstance(form["file"], list):
                    files = form["file"]
                else:
                    files = [form["file"]]
                for uploaded_file in files:
                    if uploaded_file.filename:
                        filename = os.path.basename(uploaded_file.filename)
                        filepath = os.path.join(upload_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(uploaded_file.file.read())
        redirect_path = f"/{curdir}".rstrip("/") if curdir else "/"
        self.send_response(303)
        self.send_header('Location', redirect_path)
        self.end_headers()

os.chdir(UPLOAD_DIR)
server_address = ("0.0.0.0", 8000)
httpd = HTTPServer(server_address, SimpleUploadServer)
print(f"Serving on http://0.0.0.0:8000/")
httpd.serve_forever()
