document.addEventListener('DOMContentLoaded', function () {
  var agentSelect = document.getElementById('agent_id');
  if (!agentSelect) return;
  agentSelect.addEventListener('change', function () {
    var selected = this.options[this.selectedIndex];
    var pct = selected.getAttribute('data-percentage');
    if (pct && parseFloat(pct) > 0) {
      document.getElementById('agent_percentage').value = pct;
    }
  });
});
