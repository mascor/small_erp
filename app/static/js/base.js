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

  // Bulk delete timesheets: select-all + single-row delete
  var selectAll = document.getElementById('ts-select-all');
  var bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  var bulkForm = document.getElementById('bulk-delete-form');

  function updateBulkDeleteBtn() {
    if (!bulkDeleteBtn) return;
    var checked = document.querySelectorAll('.ts-row-checkbox:checked').length;
    bulkDeleteBtn.disabled = checked === 0;
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      document.querySelectorAll('.ts-row-checkbox').forEach(function (cb) {
        cb.checked = selectAll.checked;
      });
      updateBulkDeleteBtn();
    });
  }

  document.querySelectorAll('.ts-row-checkbox').forEach(function (cb) {
    cb.addEventListener('change', function () {
      updateBulkDeleteBtn();
      if (!cb.checked && selectAll) selectAll.checked = false;
    });
  });

  // Single-row "Elimina" button: uncheck all, check only this row, confirm, submit
  document.querySelectorAll('.ts-single-delete').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      if (!confirm(btn.getAttribute('data-confirm'))) return;
      var entryId = btn.getAttribute('data-id');
      document.querySelectorAll('.ts-row-checkbox').forEach(function (cb) {
        cb.checked = cb.value === entryId;
      });
      if (bulkForm) bulkForm.submit();
    });
  });

  // Bulk delete form confirm (when using "Elimina selezionati" button)
  if (bulkForm) {
    bulkDeleteBtn && bulkDeleteBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (!confirm(bulkForm.getAttribute('data-confirm'))) return;
      bulkForm.submit();
    });
  }
});
