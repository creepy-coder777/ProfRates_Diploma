// Triggers
const openBtn = document.getElementById("open");

// Popups
const popupEmail = document.getElementById("popupEmail");
const popupCode = document.getElementById("popupCode");
const popupPassword = document.getElementById("popupPassword");

// Close icons
const closeEmail = document.getElementById("closeEmail");
const closeCode = document.getElementById("closeCode");
const closePassword = document.getElementById("closePassword");

// Action buttons
const sendLinkBtn = document.getElementById("sendLink");
const verifyCodeBtn = document.getElementById("verifyCode");
const resetPasswordBtn = document.getElementById("resetPassword");

// Inputs
const fpEmail = document.getElementById("fpEmail");
const fpCode = document.getElementById("fpCode");
const fpNewPass = document.getElementById("fpNewPass");
const fpConfirmPass = document.getElementById("fpConfirmPass");

// ✅ Allowed domain(s)
const allowedDomains = ["@polytechnic.am"];

// Function to create and show error message
function showError(inputElement, message) {
  // Remove any existing error message for this input
  hideError(inputElement);
  
  // Create error message element
  const errorElement = document.createElement('div');
  errorElement.className = 'error-message';
  errorElement.style.color = '#e74c3c';
  errorElement.style.fontSize = '12px';
  errorElement.style.marginTop = '4px';
  errorElement.style.marginBottom = '10px';
  errorElement.textContent = message;
  
  // Insert error message after the input
  inputElement.parentNode.insertBefore(errorElement, inputElement.nextSibling);
  
  return errorElement;
}

// Function to hide error message
function hideError(inputElement) {
  const nextSibling = inputElement.nextSibling;
  if (nextSibling && nextSibling.classList && nextSibling.classList.contains('error-message')) {
    nextSibling.remove();
  }
}

// Helper: validate email domain
function validateEmailDomain(email) {
  return allowedDomains.some(domain => email.toLowerCase().endsWith(domain));
}

// --- LOGIN VALIDATION ---
const loginBtn = document.querySelector(".submit");
const loginEmail = document.querySelector(".mail");
const loginPassword = document.querySelector(".pass");

loginBtn.addEventListener("click", (e) => {
  e.preventDefault(); // stop default redirect
  
  let isValid = true;
  
  // Clear previous errors
  hideError(loginEmail);
  hideError(loginPassword);
  
  // Validate email not empty
  if (!loginEmail.value.trim()) {
    showError(loginEmail, "Email field is required.");
    isValid = false;
  }
  // Validate email domain (only if email is not empty)
  else if (!validateEmailDomain(loginEmail.value)) {
    showError(loginEmail, "Please use your university email (example@polytechnic.am).");
    isValid = false;
  }
  
  // Validate password not empty
  if (!loginPassword.value.trim()) {
    showError(loginPassword, "Password field is required.");
    isValid = false;
  }
  
  // If valid, continue
  if (isValid) {
    window.location.href = "home_eng.html";
  }
});

// --- FORGOT PASSWORD FLOW ---
// Open first popup
openBtn.addEventListener("click", (e) => {
  e.preventDefault();
  popupEmail.classList.add("open");
});

// Close handlers
closeEmail.addEventListener("click", () => popupEmail.classList.remove("open"));
closeCode.addEventListener("click", () => popupCode.classList.remove("open"));
closePassword.addEventListener("click", () => popupPassword.classList.remove("open"));

// Overlay click to close
[popupEmail, popupCode, popupPassword].forEach(popup => {
  popup.addEventListener("click", (e) => {
    if (e.target === popup) popup.classList.remove("open");
  });
});

// Clear errors when user starts typing
loginEmail.addEventListener('input', () => hideError(loginEmail));
loginPassword.addEventListener('input', () => hideError(loginPassword));

// For forgot password flow
fpEmail.addEventListener('input', () => hideError(fpEmail));
fpCode.addEventListener('input', () => hideError(fpCode));
fpNewPass.addEventListener('input', () => hideError(fpNewPass));
fpConfirmPass.addEventListener('input', () => hideError(fpConfirmPass));

// Function for forgot password email validation
function validateForgotPasswordEmail() {
  hideError(fpEmail);
  
  if (!fpEmail.value.trim()) {
    showError(fpEmail, "Email field is required.");
    return false;
  }
  
  if (!validateEmailDomain(fpEmail.value)) {
    showError(fpEmail, "Please enter a valid university email (e.g., example@polytechnic.am).");
    return false;
  }
  
  return true;
}

// Flow: Email -> Code (with validation)
sendLinkBtn.addEventListener("click", () => {
  if (validateForgotPasswordEmail()) {
    popupEmail.classList.remove("open");
    popupCode.classList.add("open");
  }
});

// Flow: Code -> New Password
verifyCodeBtn.addEventListener("click", () => {
  const code = fpCode.value.trim();
  hideError(fpCode);

  const codePattern = /^\d{6}$/;
  if (!codePattern.test(code)) {
    showError(fpCode, "The verification code should be a 6-digit number.");
    return;
  }
  
  popupCode.classList.remove("open");
  popupPassword.classList.add("open");
});

// Final: Reset -> Alert
resetPasswordBtn.addEventListener("click", () => {
  let isValid = true;
  
  hideError(fpNewPass);
  hideError(fpConfirmPass);
  
  // Check if new password is not empty
  if (!fpNewPass.value.trim()) {
    showError(fpNewPass, "New password field is required.");
    isValid = false;
  }
  
  // Check if confirm password is not empty
  if (!fpConfirmPass.value.trim()) {
    showError(fpConfirmPass, "Confirm password field is required.");
    isValid = false;
  }
  
  // Check if passwords match
  if (fpNewPass.value.trim() && fpConfirmPass.value.trim() && fpNewPass.value !== fpConfirmPass.value) {
    showError(fpConfirmPass, "Passwords do not match.");
    isValid = false;
  }
  
  // Check password strength (optional)
  if (fpNewPass.value.trim() && fpNewPass.value.length < 6) {
    showError(fpNewPass, "Password must contain at least 6 characters.");
    isValid = false;
  }
  
  if (isValid) {
    popupPassword.classList.remove("open");
    alert("Password Reset Successfully!");
  }
});