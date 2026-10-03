
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import yt_dlp
import os
import uuid
import glob
import time
import logging
from urllib.parse import urlparse


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

# Maximum size allowed for one downloaded video
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))

# Delete temporary files after this many seconds
FILE_LIFETIME_SECONDS = int(
    os.getenv("FILE_LIFETIME_SECONDS", "600")
)

# yt-dlp network timeout
YTDLP_SOCKET_TIMEOUT = int(
    os.getenv("YTDLP_SOCKET_TIMEOUT", "30")
)

DOWNLOAD_FOLDER = os.path.abspath(
    os.getenv("DOWNLOAD_FOLDER", "downloads")
)

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# HELPER: CLEAN OLD FILES
# =========================================================

def cleanup_old_files():
    """
    Delete temporary downloaded files that are older
    than FILE_LIFETIME_SECONDS.
    """

    current_time = time.time()

    try:

        for file_path in glob.glob(
            os.path.join(DOWNLOAD_FOLDER, "*")
        ):

            if not os.path.isfile(file_path):
                continue

            try:

                file_age = (
                    current_time -
                    os.path.getmtime(file_path)
                )

                if file_age > FILE_LIFETIME_SECONDS:

                    os.remove(file_path)

                    logger.info(
                        "Deleted expired file: %s",
                        os.path.basename(file_path)
                    )

            except OSError as error:

                logger.warning(
                    "Could not delete file %s: %s",
                    file_path,
                    error
                )

    except Exception as error:

        logger.warning(
            "Cleanup error: %s",
            error
        )


# =========================================================
# HELPER: VALIDATE INSTAGRAM REEL URL
# =========================================================

def is_valid_instagram_reel_url(url):

    try:

        parsed = urlparse(url)

        # Only HTTPS is accepted
        if parsed.scheme != "https":
            return False

        hostname = (
            parsed.hostname or ""
        ).lower()

        # Allow Instagram domains
        allowed_domains = {
            "instagram.com",
            "www.instagram.com"
        }

        if hostname not in allowed_domains:
            return False

        path = parsed.path.rstrip("/")

        # Accept:
        # /reel/...
        # /reels/...
        if not (
            path.startswith("/reel/")
            or path.startswith("/reels/")
        ):
            return False

        return True

    except Exception:

        return False


# =========================================================
# HELPER: FIND DOWNLOADED FILE
# =========================================================

def find_downloaded_file(file_id):

    files = glob.glob(
        os.path.join(
            DOWNLOAD_FOLDER,
            file_id + ".*"
        )
    )

    # Only return actual files
    files = [
        file_path
        for file_path in files
        if os.path.isfile(file_path)
    ]

    if not files:
        return None

    return files[0]


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")

@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(".", "robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(".", "sitemap.xml")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# =========================================================
# PROCESS REEL
# =========================================================

@app.route("/api/process", methods=["POST"])
def process_reel():

    # Clean old temporary files
    cleanup_old_files()

    # -----------------------------------------
    # CHECK JSON
    # -----------------------------------------

    if not request.is_json:

        return jsonify({
            "success": False,
            "message": "Request must contain JSON data."
        }), 400

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    # -----------------------------------------
    # GET URL
    # -----------------------------------------

    reel_url = str(
        data.get("url", "")
    ).strip()

    if not reel_url:

        return jsonify({
            "success": False,
            "message": "Please enter an Instagram Reel URL."
        }), 400

    # -----------------------------------------
    # URL LENGTH PROTECTION
    # -----------------------------------------

    if len(reel_url) > 2048:

        return jsonify({
            "success": False,
            "message": "The URL is too long."
        }), 400

    # -----------------------------------------
    # VALIDATE INSTAGRAM REEL URL
    # -----------------------------------------

    if not is_valid_instagram_reel_url(
        reel_url
    ):

        return jsonify({
            "success": False,
            "message": "Please enter a valid Instagram Reel URL."
        }), 400

    # -----------------------------------------
    # UNIQUE FILE ID
    # -----------------------------------------

    file_id = str(
        uuid.uuid4()
    )

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        file_id + ".%(ext)s"
    )

    # -----------------------------------------
    # YT-DLP OPTIONS
    # -----------------------------------------

    ydl_options = {

        "outtmpl": output_template,

        # Prefer MP4
        "format": "best[ext=mp4]/best",

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        # Network timeout
        "socket_timeout": YTDLP_SOCKET_TIMEOUT,

        # Limited retries
        "retries": 2,

        # Do not use stored login credentials
        "cookiefile": None,

        # Restrict potentially unnecessary requests
        "nocheckcertificate": False,

    }

    try:

        logger.info(
            "Processing Reel: %s",
            reel_url
        )

        # -----------------------------------------
        # DOWNLOAD
        # -----------------------------------------

        with yt_dlp.YoutubeDL(
            ydl_options
        ) as ydl:

            info = ydl.extract_info(
                reel_url,
                download=True
            )

        # -----------------------------------------
        # FIND FILE
        # -----------------------------------------

        video_file = find_downloaded_file(
            file_id
        )

        if not video_file:

            logger.error(
                "Downloaded file not found."
            )

            return jsonify({
                "success": False,
                "message": "Video could not be downloaded."
            }), 500

        # -----------------------------------------
        # CHECK FILE SIZE
        # -----------------------------------------

        file_size = os.path.getsize(
            video_file
        )

        max_size = (
            MAX_FILE_SIZE_MB *
            1024 *
            1024
        )

        if file_size > max_size:

            try:
                os.remove(video_file)
            except OSError:
                pass

            logger.warning(
                "File exceeded size limit: %s",
                video_file
            )

            return jsonify({
                "success": False,
                "message": (
                    f"Video is larger than "
                    f"{MAX_FILE_SIZE_MB} MB."
                )
            }), 413

        # -----------------------------------------
        # FILE NAME
        # -----------------------------------------

        filename = os.path.basename(
            video_file
        )

        # -----------------------------------------
        # THUMBNAIL
        # -----------------------------------------

        thumbnail = info.get(
            "thumbnail"
        )

        logger.info(
            "Reel successfully processed: %s",
            filename
        )

        # -----------------------------------------
        # RESPONSE
        # -----------------------------------------

        return jsonify({

            "success": True,

            "message": (
                "Reel is ready to download."
            ),

            "thumbnail": thumbnail,

            "download_url":
                "/download/" + filename

        })

    except yt_dlp.utils.DownloadError as error:

        logger.warning(
            "yt-dlp download error: %s",
            error
        )

        # Remove partially downloaded files
        for file_path in glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                file_id + ".*"
            )
        ):

            try:
                os.remove(file_path)
            except OSError:
                pass

        return jsonify({

            "success": False,

            "message": (
                "This Reel could not be accessed. "
                "It may be private, unavailable, "
                "login-required, or temporarily "
                "inaccessible."
            )

        }), 400

    except Exception as error:

        logger.exception(
            "Unexpected processing error"
        )

        # Cleanup failed download
        for file_path in glob.glob(
            os.path.join(
                DOWNLOAD_FOLDER,
                file_id + ".*"
            )
        ):

            try:
                os.remove(file_path)
            except OSError:
                pass

        return jsonify({

            "success": False,

            "message": (
                "Something went wrong while "
                "processing the Reel."
            )

        }), 500


# =========================================================
# DOWNLOAD FILE
# =========================================================

@app.route(
    "/download/<filename>",
    methods=["GET"]
)
def download_video(filename):

    # -----------------------------------------
    # BASIC SECURITY CHECK
    # -----------------------------------------

    # Prevent path traversal
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
    ):

        return jsonify({
            "success": False,
            "message": "Invalid file name."
        }), 400

    # -----------------------------------------
    # BUILD SAFE PATH
    # -----------------------------------------

    file_path = os.path.abspath(
        os.path.join(
            DOWNLOAD_FOLDER,
            filename
        )
    )

    # Make sure requested file stays
    # inside DOWNLOAD_FOLDER
    if not file_path.startswith(
        DOWNLOAD_FOLDER + os.sep
    ):

        return jsonify({
            "success": False,
            "message": "Invalid file path."
        }), 400

    # -----------------------------------------
    # CHECK FILE
    # -----------------------------------------

    if not os.path.isfile(file_path):

        return jsonify({
            "success": False,
            "message": "File not found or expired."
        }), 404

    # -----------------------------------------
    # SEND FILE
    # -----------------------------------------

    try:

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(
                file_path
            )
        )

    except Exception as error:

        logger.exception(
            "File sending error: %s",
            error
        )

        return jsonify({
            "success": False,
            "message": "Could not send the file."
        }), 500


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "message": "Page not found."
    }), 404


@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "success": False,
        "message": "Request is too large."
    }), 413


@app.errorhandler(500)
def internal_error(error):

    logger.exception(
        "Internal server error"
    )

    return jsonify({
        "success": False,
        "message": "Internal server error."
    }), 500


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )