document.addEventListener('DOMContentLoaded', function () {
  var selectAll = document.getElementById('select-all');
  var bulkActions = document.getElementById('bulk-actions');
  var countSpan = document.getElementById('selected-count');
  if (!selectAll) return;

  function getCheckboxes() {
    return document.querySelectorAll('.activity-checkbox');
  }

  function updateUI() {
    var checked = document.querySelectorAll('.activity-checkbox:checked').length;
    countSpan.textContent = checked;
    bulkActions.style.display = checked > 0 ? 'flex' : 'none';
    var boxes = getCheckboxes();
    selectAll.checked = boxes.length > 0 && checked === boxes.length;
    selectAll.indeterminate = checked > 0 && checked < boxes.length;
  }

  selectAll.addEventListener('change', function () {
    var boxes = getCheckboxes();
    for (var i = 0; i < boxes.length; i++) {
      boxes[i].checked = selectAll.checked;
    }
    updateUI();
  });

  document.addEventListener('change', function (e) {
    if (e.target.classList.contains('activity-checkbox')) {
      updateUI();
    }
  });
});
