/* Real-time updates with WebSocket + polling fallback (section 13).
 * No external libraries — works offline on the local network. */
(function () {
  "use strict";

  // --- Live region updater: re-fetches an HTML fragment and swaps it in. ---
  function startPolling(el) {
    var url = el.dataset.pollUrl;
    var interval = parseInt(el.dataset.pollInterval || "10000", 10);
    if (!url) return;
    var timer = setInterval(function () {
      fetch(url, { headers: { "HX-Request": "true" } })
        .then(function (r) { return r.ok ? r.text() : null; })
        .then(function (html) {
          if (html === null) return;
          // Empty body => the live region expired (e.g. order-status chip): remove it.
          if (html.trim() === "") { clearInterval(timer); el.remove(); return; }
          el.innerHTML = html;
        })
        .catch(function () { /* keep last good state on error */ });
    }, interval);
  }

  // --- Optional WebSocket layer; on any message we refresh via polling URL. ---
  function connectSocket(el) {
    var wsUrl = el.dataset.wsUrl;
    if (!wsUrl || !("WebSocket" in window)) return;
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    var sock;
    var refreshUrl = el.dataset.pollUrl;

    function refresh() {
      if (!refreshUrl) return;
      fetch(refreshUrl, { headers: { "HX-Request": "true" } })
        .then(function (r) { return r.ok ? r.text() : null; })
        .then(function (html) {
          if (html === null) return;
          if (html.trim() === "") { el.remove(); return; }
          el.innerHTML = html;
        });
    }

    function open() {
      try {
        sock = new WebSocket(proto + location.host + wsUrl);
      } catch (e) { return; }
      sock.onmessage = function (ev) {
        refresh();
        if (el.dataset.sound === "true") playChime();
        flashTitle();
      };
      sock.onclose = function () { setTimeout(open, 3000); }; // auto-reconnect
    }
    open();
  }

  // --- Audio + tab title notification for new orders. ---
  function playChime() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = 880; gain.gain.value = 0.15;
      osc.start(); osc.stop(ctx.currentTime + 0.25);
    } catch (e) { /* autoplay may be blocked until first interaction */ }
  }

  var titleTimer;
  function flashTitle() {
    var original = document.title;
    var on = true;
    clearInterval(titleTimer);
    titleTimer = setInterval(function () {
      document.title = on ? "🔔 Nová objednávka!" : original;
      on = !on;
    }, 800);
    setTimeout(function () { clearInterval(titleTimer); document.title = original; }, 6000);
  }

  // --- Live timers (data-since = ISO timestamp). ---
  function tickTimers() {
    document.querySelectorAll("[data-since]").forEach(function (el) {
      var since = new Date(el.dataset.since).getTime();
      if (isNaN(since)) return;
      var secs = Math.floor((Date.now() - since) / 1000);
      var m = Math.floor(secs / 60), s = secs % 60;
      el.textContent = m + ":" + (s < 10 ? "0" : "") + s;
      var overdue = parseInt(el.dataset.overdue || "0", 10);
      if (overdue && secs > overdue * 60) {
        var card = el.closest(".order-card");
        if (card) card.classList.add("order-card--overdue");
      }
    });
  }

  // --- Item config: live total + double-submit guard. ---
  function bindGuards() {
    document.querySelectorAll("form[data-once]").forEach(function (form) {
      form.addEventListener("submit", function () {
        var btn = form.querySelector("button[type=submit]");
        if (btn) { btn.disabled = true; btn.textContent = "Odosielam…"; }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-poll-url]").forEach(function (el) {
      startPolling(el);
      connectSocket(el);
    });
    bindGuards();
    tickTimers();
    setInterval(tickTimers, 1000);
  });
})();

/* ----------------------------------------------------------------------------
 * Guest menu: inline dish expansion (HTMX), live price, quantity, toast.
 * These helpers are global because templates call them via inline handlers.
 * -------------------------------------------------------------------------- */

// Recompute the live total inside an open configuration form.
function recalcCfg(form) {
  if (!form) return;
  var addBtn = form.querySelector(".cfg__add");
  var totalEl = form.querySelector(".cfg__total");
  if (!addBtn || !totalEl) return;
  var base = parseFloat(addBtn.dataset.base || "0");
  var sum = base;
  // All option inputs carry data-price (name varies per modifier group).
  form.querySelectorAll("input[data-price]").forEach(function (input) {
    if (input.checked) sum += parseFloat(input.dataset.price || "0");
  });
  var qty = parseInt(form.querySelector('input[name="quantity"]').value || "1", 10);
  if (isNaN(qty) || qty < 1) qty = 1;
  totalEl.textContent = (sum * qty).toFixed(2);
}

// +/- stepper next to the quantity input.
function stepQty(wrap, delta) {
  var input = wrap.querySelector('input[name="quantity"]');
  var v = parseInt(input.value || "1", 10) + delta;
  if (isNaN(v) || v < 1) v = 1;
  if (v > 20) v = 20;
  input.value = v;
  recalcCfg(input.form);
}

function closeDish(itemId) {
  var dish = document.getElementById("dish-" + itemId);
  if (!dish) return;
  dish.classList.remove("expanded");
  var panel = dish.querySelector(".dish__panel");
  if (panel) {
    panel.classList.remove("open");
    panel.innerHTML = "";
  }
}

function closeAllDishes() {
  document.querySelectorAll(".dish.expanded").forEach(function (dish) {
    dish.classList.remove("expanded");
    var panel = dish.querySelector(".dish__panel");
    if (panel) { panel.classList.remove("open"); panel.innerHTML = ""; }
  });
}

function showToast(text) {
  var toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = text;
  toast.classList.add("toast--show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(function () { toast.classList.remove("toast--show"); }, 2500);
}

document.addEventListener("DOMContentLoaded", function () {
  // Toggle: clicking an already-open dish header collapses it instead of reloading.
  document.body.addEventListener("htmx:beforeRequest", function (e) {
    var el = e.detail.elt;
    if (el && el.classList && el.classList.contains("dish__header")) {
      var target = document.querySelector(el.getAttribute("hx-target"));
      if (target && target.classList.contains("open")) {
        e.preventDefault();
        closeDish(el.closest(".dish").id.replace("dish-", ""));
      }
    }
  });

  // After the config form loads, expand the card and bind the live total.
  document.body.addEventListener("htmx:afterSwap", function (e) {
    var panel = e.target;
    if (panel && panel.classList && panel.classList.contains("dish__panel")) {
      if (panel.querySelector(".cfg")) {
        // Only one dish open at a time.
        document.querySelectorAll(".dish.expanded").forEach(function (d) {
          if (d !== panel.closest(".dish")) closeDish(d.id.replace("dish-", ""));
        });
        panel.classList.add("open");
        panel.closest(".dish").classList.add("expanded");
        recalcCfg(panel.querySelector(".cfg"));
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  });

  // Item added (HX-Trigger from the server): confirm via toast, then collapse.
  document.body.addEventListener("itemAdded", function () {
    showToast("✓ Pridané do košíka");
    setTimeout(closeAllDishes, 900);
  });
});
