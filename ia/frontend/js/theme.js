/**
 * StudyFlow AI - Theme Management
 */
function getTheme() {
  return localStorage.getItem('sf_theme') || 'dark';
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('sf_theme', theme);
  updateThemeUI(theme);
}

function toggleTheme() {
  const current = getTheme();
  setTheme(current === 'dark' ? 'light' : 'dark');
}

function updateThemeUI(theme) {
  const icon = document.getElementById('theme-icon');
  const label = document.getElementById('theme-label');
  const headerBtn = document.getElementById('header-theme-btn');
  if (icon) icon.textContent = theme === 'dark' ? '🌙' : '☀️';
  if (label) label.textContent = theme === 'dark' ? 'Dark Mode' : 'Light Mode';
  if (headerBtn) headerBtn.textContent = theme === 'dark' ? '🌙' : '☀️';
}

// Initialize theme on load
(function() {
  const saved = getTheme();
  document.documentElement.setAttribute('data-theme', saved);
  document.addEventListener('DOMContentLoaded', () => updateThemeUI(saved));
})();
