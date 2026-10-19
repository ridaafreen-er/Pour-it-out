/* ==========================================================================
   MYJOURNAL - SCRIPT INTERACTIONS & LOGIC
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initPasswordToggles();
    initAuthForms();
});

// ================= THEME MANAGER =================
function initTheme() {
    const saved = localStorage.getItem("journalTheme") || "dark";
    applyTheme(saved);

    document.querySelectorAll(".btn-theme-toggle, .theme-toggle-btn").forEach(btn => {
        btn.addEventListener("click", toggleTheme);
    });
}

function applyTheme(theme) {
    if (theme === "light") {
        document.documentElement.setAttribute("data-theme", "light");
        document.body.classList.add("light-mode");
        updateThemeIcons("bi-moon-stars-fill");
    } else {
        document.documentElement.removeAttribute("data-theme");
        document.body.classList.remove("light-mode");
        updateThemeIcons("bi-sun-fill");
    }
}

function updateThemeIcons(iconClass) {
    document.querySelectorAll(".btn-theme-toggle i, .theme-toggle-btn i").forEach(icon => {
        icon.className = `bi ${iconClass}`;
    });
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    const next = current === "light" ? "dark" : "light";
    localStorage.setItem("journalTheme", next);
    applyTheme(next);
    showToast(`Switched to ${next === "light" ? "Lavender Light" : "Twilight Purple"} mode`, "info");
}

// ================= PASSWORD VISIBILITY TOGGLE =================
function initPasswordToggles() {
    document.querySelectorAll(".btn-toggle-pwd, .password-toggle").forEach(btn => {
        btn.addEventListener("click", () => {
            const container = btn.closest(".input-row-pwd, .input-with-icon, .form-field-group, .loginn, .registerFormm");
            const input = container ? container.querySelector("input[type='password'], input[type='text']") : null;
            const icon = btn.querySelector("i");
            if (input) {
                if (input.type === "password") {
                    input.type = "text";
                    if (icon) icon.className = "bi bi-eye-slash";
                } else {
                    input.type = "password";
                    if (icon) icon.className = "bi bi-eye";
                }
            }
        });
    });
}

// ================= TOAST NOTIFICATION SYSTEM =================
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let icon = "bi-info-circle-fill";
    if (type === "success") icon = "bi-check-circle-fill";
    if (type === "error") icon = "bi-exclamation-triangle-fill";

    toast.innerHTML = `
        <i class="bi ${icon} toast-icon"></i>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;

    toast.addEventListener("click", () => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 200);
    });

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 250);
        }
    }, 3500);
}

// ================= AUTH FORM SUBMISSIONS =================
function initAuthForms() {
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("username")?.value.trim();
            const email = document.getElementById("email")?.value.trim() || "";
            const password = document.getElementById("password")?.value.trim();
            const submitBtn = registerForm.querySelector("button[type='submit']");

            if (!username || !password) {
                showToast("Please enter both username and password", "error");
                return;
            }

            setLoading(submitBtn, true, "Creating Account...");

            try {
                const res = await fetch("/api/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, email, password })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    showToast("Account created! Moving your temporary reflections to your account...", "success");
                    setTimeout(() => { window.location.href = "journal.html"; }, 1000);
                } else {
                    showToast(data.message || "Registration failed", "error");
                    setLoading(submitBtn, false, "Create Account");
                }
            } catch (err) {
                showToast("Could not reach the server. Start the Flask app and try again.", "error");
                setLoading(submitBtn, false, "Create Account");
            }
        });
    }

    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("username")?.value.trim();
            const password = document.getElementById("password")?.value.trim();
            const submitBtn = loginForm.querySelector("button[type='submit']");

            if (!username || !password) {
                showToast("Please enter both username and password", "error");
                return;
            }

            setLoading(submitBtn, true, "Signing In...");

            try {
                const res = await fetch("/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    showToast("Welcome back! Loading your journal...", "success");
                    setTimeout(() => { window.location.href = "journal.html"; }, 800);
                } else {
                    showToast(data.message || "Invalid username or password", "error");
                    setLoading(submitBtn, false, "Sign In");
                }
            } catch (err) {
                showToast("Could not reach the server. Start the Flask app and try again.", "error");
                setLoading(submitBtn, false, "Sign In");
            }
        });
    }
}

function setLoading(btn, isLoading, text) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.innerHTML = isLoading 
        ? `<span style="display:inline-block;width:1rem;height:1rem;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:spin 0.75s linear infinite;margin-right:0.5rem;vertical-align:middle;"></span> ${text}`
        : text;
}

const spinStyle = document.createElement("style");
spinStyle.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(spinStyle);

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}