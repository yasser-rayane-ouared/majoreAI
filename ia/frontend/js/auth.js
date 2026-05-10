/**
 * StudyFlow AI - Auth Pages Logic
 */

// Redirect if already logged in
if (isLoggedIn() && (window.location.pathname === '/login' || window.location.pathname === '/register')) {
  window.location.href = '/';
}

function showError(msg) {
  const el = document.getElementById('auth-error');
  if (el) { el.textContent = msg; el.classList.add('show'); }
}

function hideError() {
  const el = document.getElementById('auth-error');
  if (el) el.classList.remove('show');
}

async function handleLogin(e) {
  e.preventDefault();
  hideError();
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = 'Signing in...';
  try {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.detail || 'Login failed'); return; }
    setToken(data.token);
    setUser(data.user);
    window.location.href = '/';
  } catch (err) {
    showError('Network error. Please try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideError();
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = 'Creating account...';
  try {
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.detail || 'Registration failed'); return; }
    setToken(data.token);
    setUser(data.user);
    window.location.href = '/';
  } catch (err) {
    showError('Network error. Please try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Account';
  }
}

function handleGoogleLogin() {
  showError('Google login requires configuring GOOGLE_CLIENT_ID in .env');
}
