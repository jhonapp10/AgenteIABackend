# servidor.py

from flask import Flask, send_from_directory
import uvicorn
app = Flask(__name__, static_folder='static')

@app.route('/static/mensajes/<path:filename>')
def serve_audio(filename):
    return send_from_directory('static/mensajes', filename)

if __name__ == "__main__":
    ##app.run(host="0.0.0.0", port=5000)
    uvicorn.run("main:app", host="0.0.0.0", port=8000)