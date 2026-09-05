function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = '⚠ ' + msg;
  el.style.display = 'flex';
  setTimeout(() => { el.style.display = 'none'; }, 4500);
}
