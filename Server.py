import os
import urllib
import cgi
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

UPLOAD_DIR = "/sdcard/Download/termux"  # Change as needed
PASSWORD = "letmein"

def safe_join(root, *paths):
    # Prevent directory traversal (can't escape from UPLOAD_DIR)
    dest = os.path.abspath(os.path.join(root, *paths))
    if os.path.commonpath([dest, os.path.abspath(root)]) != os.path.abspath(root):
        raise ValueError("Escape attempt detected")
    return dest

class SimpleUploadServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        rel_path = urllib.parse.unquote(parsed_path.path.lstrip("/"))
        abs_path = safe_join(UPLOAD_DIR, rel_path) if rel_path else UPLOAD_DIR

        # ---- Handle File Deletion ----
        if parsed_path.path == '/delete':
            query = urllib.parse.parse_qs(parsed_path.query)
            filename = query.get("file", [None])[0]
            password = query.get("pass", [""])[0]
            current_dir = query.get("dir", [""])[0]
            if filename and password == PASSWORD:
                try:
                    file_to_delete = safe_join(UPLOAD_DIR, current_dir, filename)
                    if os.path.isfile(file_to_delete):
                        os.remove(file_to_delete)
                except Exception:
                    pass
            redirect_path = "/" + current_dir.strip("/") if current_dir else "/"
            self.send_response(303)
            self.send_header("Location", redirect_path)
            self.end_headers()
            return

        # ---- Serve Files ----
        if os.path.isfile(abs_path):
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(abs_path)}"')
            self.end_headers()
            with open(abs_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # ---- Directory Listing ----
        try:
            entries = os.listdir(abs_path)
        except Exception:
            self.send_error(404)
            return

        entries.sort()
        current_dir = rel_path

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # ---------- BEGIN PAGE ----------
        self.wfile.write(f"""<!DOCTYPE html>
<html>
<head>
<title>File Share</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{
    font-family: "Segoe UI",Arial,sans-serif;
    background: #f9f9f9;
    margin: 0; padding: 0 0 30px 0;
}}
.upload-container {{
    display: flex;
    align-items: flex-start;
    gap: 30px;
    margin: 30px 0 15px 0;
    padding: 0 15px;
}}
.upload-form-section {{
    flex: 0 0 auto;
}}
.progress-container {{
    flex: 0 0 25%%;
    display: block;
    visibility: hidden;
    min-width: 200px;
}}
.progress-container.active {{ visibility: visible; }}
.progress-bar-bg {{
    width: 100%%;
    background: #eee;
    border-radius: 5px;
    height: 18px;
    margin-bottom: 4px;
}}
.progress-bar-fill {{
    height: 100%%;
    background: #4caf50;
    border-radius: 5px;
    width: 0%%;
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
.file-list-container {{
    background: #fff;
    margin: 0 15px;
    border-radius: 8px;
    box-shadow: 0 2px 8px #0002;
    padding: 25px 18px;
    max-width: 900px;
}}
.file-list {{
    width: 100%%;
    display: flex;
    flex-direction: column;
}}
.file-entry {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #ececec;
}}
.file-entry.header {{
    font-weight: bold;
    background: #f3f3f8;
    border-radius: 7px 7px 0 0;
    border-bottom: 2px solid #d9d9ea;
}}
.file-cell {{
    flex-basis: 25%%;
    min-width: 0;
    word-break: break-word;
}}
.file-cell.action {{
    text-align: right;
}}
.folder-link {{
    color: #2196F3;
    font-weight: bold;
    text-decoration: none;
}}
.folder-link:hover {{ text-decoration: underline; }}
.delete-link {{ color: #d32f2f; cursor: pointer; text-decoration: underline; }}
.delete-link:hover {{ color: #b71c1c; }}
.modal-bg {{
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0; top: 0; width: 100vw; height: 100vh;
    background: rgba(0,0,0,0.3);
    justify-content: center;
    align-items: center;
}}
.modal-bg.active {{ display: flex; }}
.modal-box {{
    background: #fff;
    padding: 20px 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px #0002;
    min-width: 250px; position: relative;
}}
.modal-error {{
    color: #d32f2f;
    font-size: 12px; margin-bottom: 10px;
    display: none;
}}
.modal-box label {{ display: block; margin-bottom: 8px; }}
.modal-box input[type="password"], .modal-box input[type="text"] {{
    width: 100%%; padding: 6px; margin-bottom: 10px;
}}
.modal-actions {{
    display: flex; justify-content: flex-end; gap: 10px;
}}
.show-pass-btn {{
    background: none; border: none; cursor: pointer;
    position: absolute; right: 35px; top: 53px; font-size: 14px;
}}
@media(max-width: 800px) {{
.file-list-container {{ max-width: 99vw; padding: 2vw; }}
.file-entry, .file-entry.header {{ font-size: 14px; }}
}}
</style>
<script>
let modalCallback = null;
let modalType = null;
let modalFile = null;
let current_dir = "{current_dir}";
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
    modalCallback = null; modalType = null; modalFile = null;
}}
function submitPasswordModal() {{
    const pass = document.getElementById('password-input').value;
    if (modalCallback) {{ modalCallback(pass, modalFile); }}
}}
function togglePassword() {{
    const input = document.getElementById('password-input');
    const btn = document.getElementById('show-pass-btn');
    if (input.type === 'password') {{
        input.type = 'text'; btn.textContent = 'Hide';
    }} else {{ input.type = 'password'; btn.textContent = 'Show'; }}
}}
function showError(message) {{
    const errorDiv = document.getElementById('modal-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}}
window.addEventListener('DOMContentLoaded', function() {{
    document.getElementById('password-modal-bg').addEventListener('mousedown', function(e) {{
        if (e.target === this) {{ hidePasswordModal(); }}
    }});
    document.getElementById('password-input').addEventListener('keydown', function(e) {{
        if (e.key === 'Enter') {{ submitPasswordModal(); }}
    }});
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const clearBtn = document.getElementById('clear-file-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-text');
    clearBtn.onclick = function() {{
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
        formData.append('current-dir', current_dir);
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/', true);
        xhr.upload.addEventListener('progress', function(event) {{
            if (event.lengthComputable) {{
                const percent = Math.round((event.loaded / event.total) * 100);
                document.getElementById('progress-bar-fill').style.width = percent + '%';
                document.getElementById('current-file').textContent = "Uploading: " + file.name + " (" + (currentIndex+1) + "/" + totalFiles + ")";
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
            if (current_dir) p += "&dir=" + encodeURIComponent(current_dir);
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
<div class="file-list-container">
<h3>Folders and Files</h3>
<div class="file-list">
    <div class="file-entry header">
        <div class="file-cell">File/Folder Name</div>
        <div class="file-cell">Date Modified</div>
        <div class="file-cell">Size (KB)</div>
        <div class="file-cell action">Action</div>
    </div>
""".encode())

        # Parent directory link
        if current_dir:
            parent_dir = os.path.dirname(current_dir.rstrip("/"))
            parent_href = urllib.parse.quote(parent_dir+"/") if parent_dir else ""
            self.wfile.write(f"""<div class="file-entry">
                <div class="file-cell"><a class="folder-link" href='/{parent_href}'>.. (parent directory)</a></div>
                <div class="file-cell"></div><div class="file-cell"></div><div class="file-cell action"></div>
            </div>""".encode())

        for entry in entries:
            entry_rel = os.path.join(current_dir, entry) if current_dir else entry
            entry_abs = safe_join(UPLOAD_DIR, entry_rel)
            display_name = entry
            encoded_rel_for_url = urllib.parse.quote(entry_rel)
            try:
                stats = os.stat(entry_abs)
                modified_time = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                if os.path.isdir(entry_abs):
                    # Folder row
                    row = f"""
                    <div class="file-entry">
                        <div class="file-cell">
                            <a class="folder-link" href='/{encoded_rel_for_url}/'>{display_name}/</a>
                        </div>
                        <div class="file-cell">{modified_time}</div>
                        <div class="file-cell">--</div>
                        <div class="file-cell action"></div>
                    </div>"""
                else:
                    size_kb = stats.st_size // 1024
                    row = f"""
                    <div class="file-entry">
                        <div class="file-cell">
                            <a href='/{encoded_rel_for_url}' target="_blank">{display_name}</a>
                        </div>
                        <div class="file-cell">{modified_time}</div>
                        <div class="file-cell">{size_kb} KB</div>
                        <div class="file-cell action">
                            <a href="#" class="delete-link" onclick="confirmDelete('{display_name}');return false;">Delete</a>
                        </div>
                    </div>"""
                self.wfile.write(row.encode())
            except Exception:
                continue

        # Ending out the HTML
        self.wfile.write(b"""
    </div>
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
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'}, keep_blank_values=True)
            # Get the current directory (for upload destination)
            current_dir = ""
            if "current-dir" in form:
                current_dir = form["current-dir"].value
            upload_dest = safe_join(UPLOAD_DIR, current_dir)
            os.makedirs(upload_dest, exist_ok=True)
            if "file" in form:
                file_fields = form["file"]
                if not isinstance(file_fields, list):
                    file_fields = [file_fields]
                for uploaded_file in file_fields:
                    if uploaded_file.filename:
                        filename = os.path.basename(uploaded_file.filename)
                        dest_path = os.path.join(upload_dest, filename)
                        with open(dest_path, 'wb') as out_f:
                            out_f.write(uploaded_file.file.read())
        # After upload, redirect back to current dir
        redirect_path = "/" + current_dir.strip("/") if current_dir else "/"
        self.send_response(303)
        self.send_header('Location', redirect_path)
        self.end_headers()

# Start serving
os.chdir(UPLOAD_DIR)
server_address = ("0.0.0.0", 8000)
httpd = HTTPServer(server_address, SimpleUploadServer)
print(f"Serving on http://0.0.0.0:8000/")
httpd.serve_forever()
