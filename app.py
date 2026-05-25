import os
from flask import Flask, send_from_directory

app = Flask(__name__,
            static_folder='static',
            static_url_path='')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from backend.api.routes import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')

@app.route('/gui-design')
def gui_design():
    return send_from_directory(BASE_DIR, 'gui-design.html')

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 9473))
    print(f"[md2docx] Server starting at http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)
