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

    initAlarmSound();
  });

  // ---------- Alarm chime (opt-in, stored locally) ----------
  var SOUND_KEY = "vt-alarm-sound";

  function playChime() {
    // Short two-tone alarm chime via WebAudio (no external assets).
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var now = ctx.currentTime;
      var tones = [880, 660, 880, 660];
      tones.forEach(function (freq, i) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq;
        var t = now + i * 0.22;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.22, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.19);
        osc.connect(gain).connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.2);
      });
      setTimeout(function () { ctx.close(); }, 1500);
    } catch (e) { /* audio unavailable or blocked: stay silent */ }
  }

  function initAlarmSound() {
    var btn = document.getElementById("alarmSoundToggle");
    if (!btn) return;
    var label = btn.querySelector(".alarm-sound-label");
    var hasActiveAlarms = btn.getAttribute("data-active-alarms") === "1";

    function render(on) {
      if (label) label.textContent = on ? "Sound on" : "Sound off";
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.classList.toggle("alarm-sound-on", !!on);
    }

    var enabled = null;
    try { enabled = localStorage.getItem(SOUND_KEY) === "1"; } catch (e) { enabled = false; }
    render(enabled);

    btn.addEventListener("click", function () {
      enabled = !enabled;
      try { localStorage.setItem(SOUND_KEY, enabled ? "1" : "0"); } catch (e) {}
      render(enabled);
      // Clicking is a user gesture, so the chime is always allowed here.
      if (enabled) playChime();
    });

    // If sound was enabled earlier and something is due/overdue now,
    // try to ring on load (browsers may block until first interaction).
    if (enabled && hasActiveAlarms) playChime();
  }
})();
