const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
function applySystemTheme() {
  document.querySelector('meta[name="theme-color"]').content = systemTheme.matches ? '#161616' : '#ffffff';
}
systemTheme.addEventListener('change', applySystemTheme);
applySystemTheme();
