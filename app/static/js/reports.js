document.addEventListener('DOMContentLoaded', function () {
  var btn = document.getElementById('print-report-btn');
  if (btn) {
    btn.addEventListener('click', function () {
      window.print();
    });
  }
});
