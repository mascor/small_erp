function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('visible');
}

document.addEventListener('DOMContentLoaded', function () {
  // Sidebar toggle button
  var toggleBtn = document.querySelector('.sidebar-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleSidebar);
  }
  var overlay = document.getElementById('sidebarOverlay');
  if (overlay) {
    overlay.addEventListener('click', toggleSidebar);
  }

  // Language select auto-submit
  var langSelect = document.getElementById('lang-switch');
  if (langSelect) {
    langSelect.addEventListener('change', function () {
      this.form.submit();
    });
  }

  // Auto-dismiss flash messages after 5 s
  document.querySelectorAll('.flash').forEach(function (el) {
    setTimeout(function () {
      el.style.opacity = '0';
      el.style.transform = 'translateY(-8px)';
      el.style.transition = 'all 0.3s ease';
      setTimeout(function () { el.remove(); }, 300);
    }, 5000);
  });

  // Flash close buttons
  document.querySelectorAll('.flash-close').forEach(function (btn) {
    btn.addEventListener('click', function () {
      this.parentElement.remove();
    });
  });

  // Confirm dialogs: forms/buttons with data-confirm attribute
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('submit', function (e) {
      if (!confirm(el.getAttribute('data-confirm'))) {
        e.preventDefault();
      }
    });
  });
});
