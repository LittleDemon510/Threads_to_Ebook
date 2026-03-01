"""
Threads Ebook — Flask Backend
Receives profile + posts JSON, returns a PDF.
Deploy on AWS EC2 (t2.micro free tier) or Elastic Beanstalk.
"""

import io
import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from pdf_generator import generate_pdf

# ─── LOGGING ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── APP SETUP ────────────────────────────────────────────────────────────
app = Flask(__name__)

# Allow only from Chrome extension and your frontend
# In production, replace * with your domain
CORS(app, resources={
    r"/generate-pdf": {"origins": "*"},
    r"/health":       {"origins": "*"},
})

# ─── ROUTES ───────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "threads-ebook"})


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf_endpoint():
    """
    POST /generate-pdf
    Body: {
        profile: { username, display_name, bio, location, followers, following },
        posts: [{ text, images, date_formatted, likes, replies, reposts }, ...]
    }
    Returns: PDF file
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        profile = data.get("profile", {})
        posts   = data.get("posts", [])

        if not profile.get("username"):
            return jsonify({"error": "Missing username in profile"}), 400

        if not posts:
            return jsonify({"error": "No posts provided"}), 400

        logger.info(f"Generating PDF for @{profile['username']} with {len(posts)} posts")

        pdf_bytes = generate_pdf(profile, posts)

        username = profile.get("username", "user")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"threads-ebook-{username}.pdf"
        )

    except Exception as e:
        logger.exception("Error generating PDF")
        return jsonify({"error": str(e)}), 500


# ─── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
