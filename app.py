from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import time
import itertools

app = Flask(__name__)

# Absolute path to the images folder
IMAGE_FOLDER = os.path.join(app.root_path, 'static', 'images')

# --- In-memory chat state -----------------------------------------------
# Messages are kept in memory only (reset when the server restarts).
# Each message: {"id": int, "sender": str, "glyphs": [filenames...], "ts": float}
messages = []
_id_counter = itertools.count(1)
MAX_MESSAGES = 500  # simple cap so this doesn't grow forever


def get_images():
    if not os.path.exists(IMAGE_FOLDER):
        return []
    return sorted(
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))
    )


@app.route('/')
def index():
    images = get_images()
    return render_template('index.html', images=images)


@app.route('/static/images/<filename>')
def image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)


@app.route('/api/glyphs')
def api_glyphs():
    return jsonify(get_images())


@app.route('/api/send', methods=['POST'])
def api_send():
    data = request.get_json(silent=True) or {}
    sender = (data.get('sender') or 'anonim').strip()[:40]
    glyphs = data.get('glyphs') or []

    # Validate: must be a non-empty list of known glyph filenames
    valid_glyphs = set(get_images())
    glyphs = [g for g in glyphs if g in valid_glyphs]
    if not glyphs:
        return jsonify({"error": "no valid glyphs"}), 400
    if len(glyphs) > 50:
        glyphs = glyphs[:50]

    msg = {
        "id": next(_id_counter),
        "sender": sender or 'anonim',
        "glyphs": glyphs,
        "ts": time.time(),
    }
    messages.append(msg)
    if len(messages) > MAX_MESSAGES:
        del messages[: len(messages) - MAX_MESSAGES]

    return jsonify(msg)


@app.route('/api/messages')
def api_messages():
    """Poll for messages newer than ?since=<id>."""
    try:
        since = int(request.args.get('since', 0))
    except ValueError:
        since = 0
    new_messages = [m for m in messages if m['id'] > since]
    return jsonify(new_messages)


if __name__ == '__main__':
    # host="0.0.0.0" so other devices on the same network can reach it,
    # e.g. http://<your-computer's-lan-ip>:5000
    # PORT comes from the environment on Railway/Render; falls back to 5000 locally.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
