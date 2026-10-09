// ===== ELEMENTS =====
const entryInput = document.getElementById("entry");
const journalCards = document.getElementById("journalCards");

// ===== STATE =====
let selectedMood = "😊";

// ===== LOAD SAVED ENTRIES =====
window.onload = () => {
  const saved = JSON.parse(localStorage.getItem("journalEntries")) || [];
  saved.forEach(displayEntry);
};

// ===== MOOD SELECT =====
function setMood(mood) {
  selectedMood = mood;

  // visual feedback
  document.querySelectorAll(".moods span").forEach(span => {
    span.style.opacity = "0.4";
  });
  event.target.style.opacity = "1";
}

function searchEntries() {
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();
  const entries = document.querySelectorAll(".entry-card");

  entries.forEach(entry => {
    const text = entry.querySelector("p").textContent.toLowerCase();
    if (text.includes(searchTerm)) {
      entry.style.display = "block";
    } else {
      entry.style.display = "none";
    }
  });
}

// ===== SPEECH TO TEXT =====
function startRecording() {
  if (!("webkitSpeechRecognition" in window)) {
    alert("Speech recognition not supported");
    return;
  }

  document.body.classList.add("recording");

  const recognition = new webkitSpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.start();

  recognition.onresult = e => {
    entryInput.value += " " + e.results[0][0].transcript;
    document.body.classList.remove("recording");
  };

  recognition.onerror = () => {
    document.body.classList.remove("recording");
  };
}

// ===== ADD ENTRY =====
document.getElementById("journalForm").addEventListener("submit", e => {
  e.preventDefault();

  const text = entryInput.value.trim();
  if (!text) return;

  const entry = {
    text,
    mood: selectedMood,
    date: new Date().toLocaleString(),
    day: new Date().toLocaleDateString('en-US', { weekday: 'long' })
  };

  saveEntry(entry);
  displayEntry(entry);

  entryInput.value = "";
  selectedMood = "😊";
});

// ===== SAVE TO localStorage =====
function saveEntry(entry) {
  const entries = JSON.parse(localStorage.getItem("journalEntries")) || [];
  entries.push(entry);
  localStorage.setItem("journalEntries", JSON.stringify(entries));
}

// ===== DISPLAY ENTRY =====
function displayEntry(entry, index) {
  const card = document.createElement("div");
  card.className = "entry-card";

  card.innerHTML = `
    <p>${entry.text}</p>
    <small>${entry.mood} • ${entry.date}•${entry.day}</small>
    <i class="bi bi-trash delete-btn"></i>
  `;

  // DELETE LOGIC
  card.querySelector(".delete-btn").addEventListener("click", () => {
    deleteEntry(index);
    card.remove();
  });

  journalCards.prepend(card);
}
// ===== DELETE ENTRY =====
function deleteEntry(index) {
  const entries = JSON.parse(localStorage.getItem("journalEntries")) || [];
  entries.splice(index, 1);
  localStorage.setItem("journalEntries", JSON.stringify(entries));
}
// ===== DARK / LIGHT MODE =====
const themeBtn = document.getElementById("themeToggle");
if (themeBtn) {
  themeBtn.addEventListener("click", toggleTheme);
}
function toggleTheme() {
  document.body.classList.toggle("dark-mode");
  const isDark = document.body.classList.contains("dark-mode");
  localStorage.setItem("theme", isDark ? "dark" : "light");
}
function registered(){
  alert("Registered Successfully");
  window.location.href = "login.html";
    return;
}

const registerform = document.getElementById("registerForm");
 if(registerform){
  registerform.addEventListener("submit", e => {
    e.preventDefault();
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value.trim();
      
      const res=fetch("http://127.0.0.1:5000/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      }).then(response => {
        if (response.ok) { registered();
  }       else { alert("Registration failed"); }
      }).catch(() => { alert("An error occurred"); }
      );
  });
}

const loginform = document.getElementById("loginForm");
if(loginform){
  loginform.addEventListener("submit", e => {
    e.preventDefault();
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value.trim();
      if (!username || !password) {
        alert("Please enter both username and password");
        return;
      }
      fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      }).then(response => {response.ok ? window.location.href = "journal.html" : alert("Login failed"); }
      ).catch(() => { alert("An error occurred"); }
      );
  });
}