/* VaccTrack front-end behaviour (vanilla JS, no framework).
   Progressive enhancement only: everything works without JS
   (modals degrade to plain POST forms when JS is unavailable). */
(function () {
  "use strict";

  // Loading state on form submit: show spinner, disable button, guard
  // against double submissions.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.hasAttribute("data-loading-form")) return;
    if (form.noValidate && !form.checkValidity()) return; // let browser show hints
    var btn = form.querySelector("[data-loading-button]");
    if (btn) {
      var spinner = btn.querySelector(".spinner-border");
      if (spinner) spinner.classList.remove("d-none");
      btn.disabled = true;
      // Safety net: re-enable after 10s in case navigation stalls.
      setTimeout(function () {
        btn.disabled = false;
        if (spinner) spinner.classList.add("d-none");
      }, 10000);
    }
  });

  // Auto-dismiss success/info flashes after 6 seconds.
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".flash-stack .alert-success, .flash-stack .alert-info").forEach(function (el) {
      setTimeout(function () {
        var alert = bootstrap.Alert.getOrCreateInstance(el);
        alert.close();
      }, 6000);
    });

    // Print-friendly report button (replaces inline onclick for CSP).
    document.querySelectorAll("[data-print-page]").forEach(function (btn) {
      btn.addEventListener("click", function () { window.print(); });
    });

    // Account deletion: confirm in modal, then submit the real form.
    var confirmBtn = document.getElementById("confirmDeleteAccountBtn");
    var modalEl = document.getElementById("confirmDeleteAccount");
    if (confirmBtn && modalEl) {
      confirmBtn.addEventListener("click", function () {
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        var trigger = document.getElementById("deleteAccountBtn");
        if (trigger) trigger.closest("form").submit();
      });
    }
  });
})();
