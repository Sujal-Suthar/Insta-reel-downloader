const input = document.getElementById("reelUrl");

const downloadBtn =
    document.getElementById("downloadBtn");

const message =
    document.getElementById("message");

const loading =
    document.getElementById("loading");

const previewCard =
    document.getElementById("previewCard");

const previewImage =
    document.getElementById("previewImage");

const previewText =
    document.getElementById("previewText");

const realDownloadBtn =
    document.getElementById("realDownloadBtn");


// ==========================================
// DOWNLOAD BUTTON
// ==========================================

downloadBtn.addEventListener(
    "click",
    processReel
);


// ==========================================
// ENTER KEY
// ==========================================

input.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Enter") {

            processReel();

        }

    }
);


// ==========================================
// PROCESS REEL
// ==========================================

async function processReel() {

    const url = input.value.trim();


    // Clear previous result

    hidePreview();

    clearMessage();


    // ======================================
    // EMPTY URL
    // ======================================

    if (url === "") {

        showError(
            "Please paste an Instagram Reel link."
        );

        return;

    }


    // ======================================
    // URL VALIDATION
    // ======================================

    const instagramPattern =
        /^https?:\/\/(www\.)?instagram\.com\/(reel|reels)\/[A-Za-z0-9_-]+/i;


    if (!instagramPattern.test(url)) {

        showError(
            "Please enter a valid Instagram Reel URL."
        );

        return;

    }


    // ======================================
    // START LOADING
    // ======================================

    setLoading(true);


    try {

        const response = await fetch(
            "/api/process",
            {

                method: "POST",

                headers: {

                    "Content-Type":
                        "application/json"

                },

                body: JSON.stringify({

                    url: url

                })

            }
        );


        const data =
            await response.json();


        // ==================================
        // BACKEND ERROR
        // ==================================

        if (!response.ok || !data.success) {

            showError(
                data.message ||
                "Unable to download this Reel."
            );

            return;

        }


        // ==================================
        // SUCCESS
        // ==================================

        showSuccess(
            data.message
        );


        // ==================================
        // PREVIEW
        // ==================================

        showPreview(
            data.thumbnail,
            data.download_url
        );


    }

    catch (error) {

        console.error(error);

        showError(
            "Unable to connect to the server."
        );

    }

    finally {

        setLoading(false);

    }

}


// ==========================================
// LOADING
// ==========================================

function setLoading(status) {

    if (status) {

        loading.style.display = "flex";

        downloadBtn.disabled = true;

        downloadBtn.textContent =
            "Processing...";

    }

    else {

        loading.style.display = "none";

        downloadBtn.disabled = false;

        downloadBtn.textContent =
            "Download";

    }

}


// ==========================================
// SHOW PREVIEW
// ==========================================

function showPreview(
    thumbnail,
    downloadUrl
) {

    previewCard.style.display =
        "block";


    if (thumbnail) {

        previewImage.src =
            thumbnail;

    }


    previewText.textContent =
        "Your Reel is ready to download.";


    realDownloadBtn.href =
        downloadUrl;


    realDownloadBtn.classList.remove(
        "disabled"
    );

}


// ==========================================
// HIDE PREVIEW
// ==========================================

function hidePreview() {

    previewCard.style.display =
        "none";


    previewImage.src = "";


    realDownloadBtn.href =
        "#";


    realDownloadBtn.classList.add(
        "disabled"
    );

}


// ==========================================
// SUCCESS
// ==========================================

function showSuccess(text) {

    message.textContent = text;

    message.className =
        "message-success";

}


// ==========================================
// ERROR
// ==========================================

function showError(text) {

    message.textContent = text;

    message.className =
        "message-error";

}


// ==========================================
// CLEAR MESSAGE
// ==========================================

function clearMessage() {

    message.textContent = "";

    message.className = "";

}