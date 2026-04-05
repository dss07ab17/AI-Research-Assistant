const form = document.getElementById("query-form");
const submitButton = document.getElementById("submit-button");
const statusEl = document.getElementById("status");
const emptyStateEl = document.getElementById("empty-state");
const resultsEl = document.getElementById("results");
const answerEl = document.getElementById("answer");
const keyPointsEl = document.getElementById("key-points");
const citationsEl = document.getElementById("citations");

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function renderList(target, items, renderer) {
  target.innerHTML = "";
  items.forEach((item) => {
    const element = renderer(item);
    target.appendChild(element);
  });
}

async function readResponsePayload(response) {
  const rawBody = await response.text();

  if (!rawBody) {
    return {};
  }

  try {
    return JSON.parse(rawBody);
  } catch {
    return {
      detail: rawBody
    };
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const query = String(formData.get("query") || "").trim();
  const maxPapers = Number(formData.get("max_papers") || 3);

  if (!query) {
    setStatus("Please enter a research question.", "error");
    return;
  }

  submitButton.disabled = true;
  setStatus("Running the full research pipeline. This can take a moment while PDFs are fetched and parsed.", "loading");

  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query,
        max_papers: maxPapers
      })
    });

    const payload = await readResponsePayload(response);

    if (!response.ok) {
      const detail = typeof payload.detail === "string"
        ? payload.detail
        : payload.detail || "The request failed.";
      throw new Error(detail);
    }

    answerEl.textContent = payload.answer;

    renderList(keyPointsEl, payload.key_points || [], (text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    });

    renderList(citationsEl, payload.citations || [], (citation) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = citation.link;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = citation.title;
      item.appendChild(link);
      return item;
    });

    emptyStateEl.classList.add("hidden");
    resultsEl.classList.remove("hidden");
    setStatus("Research response ready.", "idle");
  } catch (error) {
    setStatus(error.message || "Something went wrong while querying the backend.", "error");
    resultsEl.classList.add("hidden");
    emptyStateEl.classList.remove("hidden");
  } finally {
    submitButton.disabled = false;
  }
});
