// ==========================================
// TripMate-AI Frontend
// Matches current FastAPI backend exactly
// ==========================================

let currentThreadId =
  localStorage.getItem("travel_thread_id") || null;

let latestAnswerMarkdown = "";


// ==========================================
// PROMPT BUTTONS
// ==========================================

function setPrompt(text) {
  const input = document.getElementById("userInput");

  if (input) {
    input.value = text;
    input.focus();
  }
}



// ==========================================
// LOADING STATE
// ==========================================

function setLoading(isLoading) {
  const sendBtn = document.getElementById("sendBtn");
  const btnText = document.getElementById("btnText");
  const btnLoader = document.getElementById("btnLoader");

  if (sendBtn) {
    sendBtn.disabled = isLoading;
  }

  if (btnText && btnLoader) {
    if (isLoading) {
      btnText.classList.add("hidden");
      btnLoader.classList.remove("hidden");
    } else {
      btnText.classList.remove("hidden");
      btnLoader.classList.add("hidden");
    }
  }
}


// ==========================================
// ERROR HANDLING
// ==========================================

function showError(message) {
  const errorBox = document.getElementById("errorBox");

  if (!errorBox) {
    console.error(message);
    return;
  }

  // Handle FastAPI validation errors properly
  if (typeof message === "object") {
    if (Array.isArray(message)) {
      message = message
        .map((item) => {
          if (typeof item === "object") {
            return item.msg || JSON.stringify(item);
          }

          return String(item);
        })
        .join(", ");
    } else {
      message =
        message.msg ||
        message.error ||
        JSON.stringify(message);
    }
  }

  errorBox.textContent = String(message);

  errorBox.classList.remove("hidden");

  errorBox.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });
}


function hideError() {
  const errorBox = document.getElementById("errorBox");

  if (!errorBox) {
    return;
  }

  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}


// ==========================================
// MARKDOWN RENDERING
// ==========================================

function renderMarkdown(element, markdown) {
  if (!element) {
    return;
  }

  if (typeof marked !== "undefined") {
    element.innerHTML = marked.parse(markdown || "");
  } else {
    element.innerText = markdown || "";
  }
}


// ==========================================
// SHOW RESULT
// ==========================================

function showResult(answer, threadId) {
  latestAnswerMarkdown = answer || "";

  const resultSection =
    document.getElementById("resultSection");

  const resultBox =
    document.getElementById("resultBox");

  const threadInfo =
    document.getElementById("threadInfo");

  const resultTitle =
    document.getElementById("resultTitle");

  renderMarkdown(
    resultBox,
    latestAnswerMarkdown
  );

  if (threadInfo) {
    threadInfo.textContent =
      `Thread ID: ${threadId}`;
  }

  if (resultTitle) {
    resultTitle.textContent =
      "Your AI Travel Plan";
  }

  if (resultSection) {
    resultSection.classList.remove("hidden");

    resultSection.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }
}


// ==========================================
// SEND TRAVEL REQUEST
// ==========================================

async function sendMessage() {
  hideError();

  const input =
    document.getElementById("userInput");

  if (!input) {
    showError("Input field not found.");
    return;
  }

  const message =
    input.value.trim();

  if (!message) {
    showError(
      "Please enter your travel request first."
    );

    return;
  }

  setLoading(true);

  try {

    // ======================================
    // IMPORTANT
    // Backend expects:
    //
    // {
    //   "message": "...",
    //   "thread_id": "..."
    // }
    //
    // thread_id MUST NOT be null because
    // TravelRequest defines it as `str`.
    // ======================================

    const payload = {
      message: message,
      thread_id: currentThreadId || ""
    };

    console.log(
      "Sending travel request:",
      payload
    );


    const response = await fetch(
      "/api/travel",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify(payload)
      }
    );


    // ======================================
    // READ RESPONSE
    // ======================================

    let data;

    try {
      data = await response.json();
    } catch (error) {
      throw new Error(
        `Server returned HTTP ${response.status}`
      );
    }


    console.log(
      "Backend response:",
      data
    );


    // ======================================
    // HANDLE FASTAPI ERRORS
    // ======================================

    if (!response.ok) {

      // FastAPI validation error
      if (data.detail) {

        if (Array.isArray(data.detail)) {

          const messages =
            data.detail
              .map((error) => {
                return (
                  error.msg ||
                  JSON.stringify(error)
                );
              })
              .join(", ");

          throw new Error(messages);

        }

        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail)
        );
      }


      // Our backend error format
      if (data.error) {
        throw new Error(data.error);
      }


      throw new Error(
        `Request failed with HTTP ${response.status}`
      );
    }


    // ======================================
    // BACKEND SUCCESS CHECK
    // ======================================

    if (data.success === false) {
      throw new Error(
        data.error ||
        "Travel planning failed."
      );
    }


    // ======================================
    // SAVE THREAD ID
    // ======================================

    if (data.thread_id) {

      currentThreadId =
        data.thread_id;

      localStorage.setItem(
        "travel_thread_id",
        currentThreadId
      );
    }


    // ======================================
    // SHOW FINAL ANSWER
    // ======================================

    showResult(
      data.answer,
      data.thread_id
    );


  } catch (error) {

    console.error(
      "Travel request failed:",
      error
    );

    showError(
      error.message ||
      "Something went wrong."
    );

  } finally {

    setLoading(false);
  }
}


// ==========================================
// COPY RESULT
// ==========================================

function copyResult() {
  const resultBox =
    document.getElementById("resultBox");

  if (!resultBox) {
    showError("Result box not found.");
    return;
  }

  const text =
    resultBox.innerText;

  if (!text) {
    showError("Nothing to copy.");
    return;
  }


  navigator.clipboard
    .writeText(text)

    .then(() => {

      const copyBtn =
        document.querySelector(".copy-btn");

      if (!copyBtn) {
        return;
      }

      const oldText =
        copyBtn.textContent;

      copyBtn.textContent =
        "Copied!";

      setTimeout(() => {
        copyBtn.textContent =
          oldText;
      }, 1400);

    })

    .catch(() => {
      showError(
        "Could not copy result."
      );
    });
}


// ==========================================
// DOWNLOAD PDF
// ==========================================

function downloadPDF() {
  const pdfContent =
    document.getElementById("pdfContent");

  if (
    !latestAnswerMarkdown ||
    !pdfContent
  ) {
    showError(
      "No travel plan available to download."
    );

    return;
  }


  if (
    typeof html2pdf ===
    "undefined"
  ) {
    showError(
      "PDF library is not loaded."
    );

    return;
  }


  const downloadBtn =
    document.querySelector(
      ".download-btn"
    );

  const oldText =
    downloadBtn?.textContent ||
    "Download PDF";


  if (downloadBtn) {
    downloadBtn.textContent =
      "Preparing PDF...";

    downloadBtn.disabled =
      true;
  }


  const options = {

    margin: 0.5,

    filename:
      "ai-travel-plan.pdf",

    image: {
      type: "jpeg",
      quality: 0.98
    },

    html2canvas: {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff"
    },

    jsPDF: {
      unit: "in",
      format: "a4",
      orientation: "portrait"
    },

    pagebreak: {
      mode: [
        "avoid-all",
        "css",
        "legacy"
      ]
    }
  };


  html2pdf()
    .set(options)
    .from(pdfContent)
    .save()

    .then(() => {

      if (downloadBtn) {
        downloadBtn.textContent =
          oldText;

        downloadBtn.disabled =
          false;
      }

    })

    .catch((error) => {

      console.error(
        "PDF error:",
        error
      );

      if (downloadBtn) {
        downloadBtn.textContent =
          oldText;

        downloadBtn.disabled =
          false;
      }

      showError(
        "Could not download PDF."
      );

    });
}


// ==========================================
// CTRL + ENTER
// ==========================================

document.addEventListener(
  "keydown",
  function (event) {

    if (
      event.ctrlKey &&
      event.key === "Enter"
    ) {
      event.preventDefault();
      sendMessage();
    }

  }
);