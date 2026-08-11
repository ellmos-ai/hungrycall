/* HungryCall client.
 *
 * The server sends structured events over SSE and this file decides what they
 * look like. The earlier build shipped <script> fragments inside the event
 * payloads, which meant the wire format and the presentation were the same
 * thing — you could not change one without breaking the other, and nothing
 * could be tested without a browser.
 */
(function () {
  "use strict";

  var HC = (window.HC = window.HC || {});

  HC.map = null;
  HC.markers = [];
  HC.stream = null;
  HC.callCount = 0;
  HC.canceled = false;

  // ----------------------------------------------------------- color theme
  function syncThemeControl() {
    var button = $("theme-toggle");
    if (!button) return;
    var isDark = document.documentElement.dataset.theme === "dark";
    button.setAttribute("aria-pressed", String(isDark));
    var label = $("theme-label");
    if (label) label.textContent = isDark ? button.dataset.light : button.dataset.dark;
  }

  HC.toggleTheme = function () {
    var isDark = document.documentElement.dataset.theme === "dark";
    if (isDark) delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = "dark";
    try {
      localStorage.setItem("hc-theme", isDark ? "light" : "dark");
    } catch (error) { /* persistence is optional; the control still works */ }
    syncThemeControl();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncThemeControl);
  } else {
    syncThemeControl();
  }

  // ---------------------------------------------------------------- helpers
  function $(id) { return document.getElementById(id); }

  function setStatus(text) {
    var el = $("cascade-status");
    if (el) el.textContent = text;
  }

  function bumpCallCounter() {
    HC.callCount += 1;
    var el = $("call-counter");
    if (el) el.textContent = String(HC.callCount);
  }

  function logLine(text) {
    var log = $("activity-log");
    if (!log) return;
    var row = document.createElement("div");
    row.textContent = text;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  // ------------------------------------------------------------------- map
  HC.initMap = function (lat, lon, radiusKm, restaurants) {
    if (typeof L === "undefined" || !$("map")) return;
    if (HC.map) { HC.map.remove(); HC.map = null; }

    HC.map = L.map("map").setView([lat, lon], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(HC.map);

    L.circleMarker([lat, lon], {
      radius: 7, color: "#7C3AED", fillColor: "#EC4899", fillOpacity: 1, weight: 2
    }).addTo(HC.map);

    if (radiusKm > 0) {
      L.circle([lat, lon], {
        radius: radiusKm * 1000,
        color: "#2563EB", fillColor: "#7C3AED", fillOpacity: 0.07,
        weight: 1.5, dashArray: "5 6"
      }).addTo(HC.map);
    }

    /* Numbered pins drawn in CSS rather than L.marker: the default marker
       needs images/marker-icon.png, which this offline bundle does not carry,
       so every restaurant pin was silently a 404 and invisible. The number
       also does real work here — it is the position in the call order. */
    HC.markers = [];
    (restaurants || []).forEach(function (r, i) {
      var pin = L.divIcon({
        className: "map-pin",
        html: '<span>' + (i + 1) + "</span>",
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      });
      var marker = L.marker([r.lat, r.lon], { icon: pin, title: r.name }).addTo(HC.map);
      marker.bindPopup(
        "<b>" + (i + 1) + ". " + r.name + "</b><br>" +
        (r.cuisines || []).join(", ") + "<br>" + r.phone
      );
      HC.markers.push(marker);
    });
  };

  HC.initCandidates = function (restaurants, lat, lon, radiusKm) {
    HC.initMap(lat, lon, radiusKm, restaurants);
    HC.syncOrder();
  };

  // ------------------------------------------------------- candidate order
  /* The arrows used to move DOM nodes while the server called in its own
     order. Now the visible order is the order: it is written into a hidden
     field on every change, and the server calls exactly that sequence. */
  HC.syncOrder = function () {
    var list = $("candidate-list");
    var field = $("candidate_order");
    if (!list || !field) return;

    var ids = [];
    var rank = 1;
    Array.prototype.forEach.call(list.querySelectorAll(".cand"), function (card) {
      var box = card.querySelector('input[type="checkbox"]');
      var label = card.querySelector("[data-rank]");
      if (box && box.checked) {
        ids.push(card.dataset.id);
        if (label) label.textContent = String(rank++);
      } else if (label) {
        label.textContent = "—";
      }
    });
    field.value = ids.join(",");
  };

  HC.move = function (id, delta) {
    var card = $("cand-" + id);
    if (!card) return;
    var sibling = delta < 0 ? card.previousElementSibling : card.nextElementSibling;
    if (!sibling || !sibling.classList.contains("cand")) return;
    if (delta < 0) card.parentNode.insertBefore(card, sibling);
    else card.parentNode.insertBefore(sibling, card);
    HC.syncOrder();
  };

  HC.onToggle = function (box) {
    var card = box.closest(".cand");
    if (card) card.classList.toggle("off", !box.checked);
    HC.syncOrder();
  };

  HC.toggleSkipped = function (btn) {
    var box = $("skipped");
    if (!box) return;
    box.hidden = !box.hidden;
    btn.textContent = box.hidden ? btn.dataset.show : btn.dataset.hide;
  };

  // ------------------------------------------------------ order wish chains
  HC.orderChain = null;
  HC.criteriaPosition = null;
  HC.criteriaCell = null;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function make(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function option(value, text, selected) {
    var el = document.createElement("option");
    el.value = value;
    el.textContent = text;
    el.selected = value === selected;
    return el;
  }

  function syncOrderChain() {
    if (!HC.orderChain) return;
    var field = $("order_chain_json");
    if (field) field.value = JSON.stringify(HC.orderChain);
    var prompt = $("food_prompt");
    if (prompt) {
      prompt.value = HC.orderChain.posten.map(function (position) {
        var first = position.zellen[0] || { menge: 1, produkt: "" };
        return first.menge + "x " + first.produkt;
      }).join(", ");
    }
  }

  function ensureOrderChain() {
    if (HC.orderChain && Array.isArray(HC.orderChain.posten)) return true;
    if (!HC.orderChainInitial || !Array.isArray(HC.orderChainInitial.posten)) return false;
    HC.orderChain = clone(HC.orderChainInitial);
    return true;
  }

  function field(labelText, control) {
    var wrap = make("div", "field");
    var label = make("label", "", labelText);
    wrap.appendChild(label);
    wrap.appendChild(control);
    return wrap;
  }

  function reactionText(value) {
    if (value === "annehmen") return HC.text.reactionAccept;
    if (value === "ablehnen") return HC.text.reactionReject;
    return HC.text.reactionNext;
  }

  function criterionText(criterion) {
    var kind = criterion.art === "hoechstpreis" ? HC.text.criterionPrice :
      (criterion.art === "sonderwunsch" ? HC.text.criterionSpecial : HC.text.criterionQuestion);
    return kind + ": " + criterion.wert + " — " + reactionText(criterion.reaktion_nein);
  }

  function renderCell(positionIndex, cellIndex, cell) {
    var card = make("div", "order-cell");
    var label = cellIndex === 0 ? HC.text.wish : HC.text.replacement + " " + cellIndex;
    card.appendChild(make("div", "eyebrow", label));

    var grid = make("div", "order-cell-grid");
    var quantity = document.createElement("input");
    quantity.type = "number"; quantity.min = "1"; quantity.step = "1";
    quantity.value = cell.menge;
    quantity.addEventListener("input", function () {
      cell.menge = Math.max(1, parseInt(quantity.value || "1", 10)); syncOrderChain();
    });
    grid.appendChild(field(HC.text.quantity, quantity));

    var product = document.createElement("input");
    product.type = "text"; product.className = "order-product-input"; product.required = true; product.value = cell.produkt || "";
    product.addEventListener("input", function () { cell.produkt = product.value; syncOrderChain(); });
    grid.appendChild(field(HC.text.product, product));

    // Coverage-map finding #15: there used to be a food/drink selector here.
    // Nothing downstream ever read cell.art for anything the call needs -- a
    // restaurant employee already knows whether "Cola" is a drink from their
    // own menu, so the field never changed a question or a sentence. Removed
    // rather than left offering a choice with no effect (CONVERSATION-TREE.md
    // §4 row 15). cell.art still exists in the data model, always "essen",
    // for JSON-shape stability -- see models.py OrderCell.kind.
    card.appendChild(grid);

    var tools = make("div", "order-cell-tools");
    var gear = make("button", "mini", "⚙ " + HC.text.criteria);
    gear.type = "button";
    gear.addEventListener("click", function () { HC.openCriteria(positionIndex, cellIndex); });
    card.addEventListener("contextmenu", function (event) {
      event.preventDefault(); HC.openCriteria(positionIndex, cellIndex);
    });
    tools.appendChild(gear);
    tools.appendChild(make("span", "criteria-count", String((cell.kriterien || []).length)));
    if (HC.orderChain.posten[positionIndex].zellen.length > 1) {
      var remove = make("button", "mini", "× " + HC.text.remove);
      remove.type = "button";
      remove.addEventListener("click", function () { HC.removeCell(positionIndex, cellIndex); });
      tools.appendChild(remove);
    }
    card.appendChild(tools);
    return card;
  }

  HC.renderOrderChain = function () {
    var root = $("order-chain-builder");
    if (!root || !HC.orderChain) return;
    root.textContent = "";
    HC.orderChain.posten.forEach(function (position, positionIndex) {
      var section = make("section", "order-position");
      var head = make("div", "order-position-head");
      head.appendChild(make("h4", "", HC.text.position + " " + (positionIndex + 1)));
      if (HC.orderChain.posten.length > 1) {
        var removePosition = make("button", "mini", "× " + HC.text.remove);
        removePosition.type = "button";
        removePosition.addEventListener("click", function () { HC.removePosition(positionIndex); });
        head.appendChild(removePosition);
      }
      section.appendChild(head);

      var cells = make("div", "order-cells");
      position.zellen.forEach(function (cell, cellIndex) {
        if (cellIndex) cells.appendChild(make("span", "order-arrow", "→"));
        cells.appendChild(renderCell(positionIndex, cellIndex, cell));
      });
      var addCell = make("button", "mini", "＋ " + HC.text.addReplacement);
      addCell.type = "button";
      addCell.addEventListener("click", function () { HC.addCell(positionIndex); });
      cells.appendChild(addCell);
      section.appendChild(cells);

      var foot = make("div", "order-position-foot");
      var tags = document.createElement("input");
      tags.type = "text"; tags.value = (position.tags || []).join(", ");
      tags.setAttribute("list", "saved-tags");
      tags.addEventListener("change", function () {
        position.tags = tags.value.split(",").map(function (value) { return value.trim(); })
          .filter(function (value, index, all) { return value && all.indexOf(value) === index; });
        syncOrderChain();
      });
      foot.appendChild(field(HC.text.tags, tags));

      var rule = document.createElement("select");
      rule.appendChild(option("posten_weglassen", HC.text.ruleSkip, position.wenn_nichts_verfuegbar));
      rule.appendChild(option("bestellung_abbrechen", HC.text.ruleAbort, position.wenn_nichts_verfuegbar));
      rule.addEventListener("change", function () { position.wenn_nichts_verfuegbar = rule.value; syncOrderChain(); });
      foot.appendChild(field(HC.text.ruleSkip + " / " + HC.text.ruleAbort, rule));
      section.appendChild(foot);
      root.appendChild(section);
    });
    syncOrderChain();
  };

  HC.addPosition = function () {
    if (!ensureOrderChain()) return;
    HC.orderChain.posten.push({
      zellen: [{ menge: 1, produkt: "", art: "essen", kriterien: [] }],
      tags: [], wenn_nichts_verfuegbar: "posten_weglassen"
    });
    HC.renderOrderChain();
    var products = document.querySelectorAll(".order-product-input");
    if (products.length) products[products.length - 1].focus();
  };

  HC.removePosition = function (positionIndex) {
    if (HC.orderChain.posten.length > 1) HC.orderChain.posten.splice(positionIndex, 1);
    HC.renderOrderChain();
  };

  HC.addCell = function (positionIndex) {
    HC.orderChain.posten[positionIndex].zellen.push({
      menge: 1, produkt: "", art: "essen", kriterien: []
    });
    HC.renderOrderChain();
  };

  HC.removeCell = function (positionIndex, cellIndex) {
    var cells = HC.orderChain.posten[positionIndex].zellen;
    if (cells.length > 1) cells.splice(cellIndex, 1);
    HC.renderOrderChain();
  };

  HC.openCriteria = function (positionIndex, cellIndex) {
    HC.criteriaPosition = positionIndex; HC.criteriaCell = cellIndex;
    HC.renderCriteria(); HC.onCriterionKindChange();
    var dialog = $("criteria-dialog");
    if (dialog && dialog.showModal) dialog.showModal();
  };

  HC.closeCriteria = function () {
    var dialog = $("criteria-dialog");
    if (dialog && dialog.open) dialog.close();
  };

  HC.renderCriteria = function () {
    var root = $("criteria-current");
    if (!root || HC.criteriaPosition === null) return;
    root.textContent = "";
    var criteria = HC.orderChain.posten[HC.criteriaPosition].zellen[HC.criteriaCell].kriterien;
    criteria.forEach(function (criterion, index) {
      var row = make("div", "criterion-row");
      row.appendChild(make("span", "", criterionText(criterion)));
      var remove = make("button", "mini", "× " + HC.text.remove);
      remove.type = "button";
      remove.addEventListener("click", function () { HC.removeCriterion(index); });
      row.appendChild(remove); root.appendChild(row);
    });
  };

  HC.onCriterionKindChange = function () {
    var kind = $("criterion-kind");
    var input = $("criterion-value");
    var label = $("criterion-value-label");
    if (!kind || !input || !label) return;
    var question = kind.value === "rueckfrage";
    input.type = kind.value === "hoechstpreis" ? "number" : "text";
    input.step = kind.value === "hoechstpreis" ? "0.01" : "";
    label.textContent = kind.value === "hoechstpreis" ? HC.text.criterionValuePrice :
      (question ? HC.text.criterionValueQuestion : HC.text.criterionValueSpecial);
    $("criterion-single-reaction").hidden = question;
    $("criterion-yes-reaction").hidden = !question;
    $("criterion-no-reaction-question").hidden = !question;
  };

  HC.addCriterion = function () {
    if (HC.criteriaPosition === null) return;
    var kind = $("criterion-kind").value;
    var raw = $("criterion-value").value.trim();
    if (!raw) return;
    var value = kind === "hoechstpreis" ? Number(raw) : raw;
    if (kind === "hoechstpreis" && (!Number.isFinite(value) || value < 0)) return;
    var criterion = { art: kind, wert: value, reaktion_ja: "annehmen", reaktion_nein: "naechster_ersatz" };
    if (kind === "rueckfrage") {
      criterion.reaktion_ja = $("criterion-on-yes").value;
      criterion.reaktion_nein = $("criterion-on-no").value;
    } else {
      criterion.reaktion_nein = $("criterion-no-reaction").value;
    }
    HC.orderChain.posten[HC.criteriaPosition].zellen[HC.criteriaCell].kriterien.push(criterion);
    $("criterion-value").value = "";
    syncOrderChain(); HC.renderCriteria(); HC.renderOrderChain();
  };

  HC.removeCriterion = function (criterionIndex) {
    HC.orderChain.posten[HC.criteriaPosition].zellen[HC.criteriaCell].kriterien.splice(criterionIndex, 1);
    syncOrderChain(); HC.renderCriteria(); HC.renderOrderChain();
  };

  HC.loadOrderTemplate = function () {
    var id = $("order-template-select").value;
    var found = (HC.orderTemplates || []).find(function (item) { return item.id === id; });
    if (!found) return;
    HC.orderChain = clone(found.order_chain);
    $("order-template-name").value = found.name;
    HC.renderOrderChain();
  };

  HC.saveOrderTemplate = function () {
    syncOrderChain();
    var name = $("order-template-name").value.trim();
    var status = $("order-template-status");
    if (!name) { if (status) status.textContent = HC.text.templateError; return; }
    var body = new FormData();
    body.append("name", name);
    body.append("order_chain_json", JSON.stringify(HC.orderChain));
    fetch("/api/order-templates", { method: "POST", body: body })
      .then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
      .then(function (result) {
        if (!result.ok) throw new Error(result.data.error || HC.text.templateError);
        var index = (HC.orderTemplates || []).findIndex(function (item) { return item.id === result.data.id; });
        if (index >= 0) HC.orderTemplates[index] = result.data;
        else HC.orderTemplates.push(result.data);
        var select = $("order-template-select");
        if (select && !Array.prototype.some.call(select.options, function (item) {
          return item.value === result.data.id;
        })) {
          select.appendChild(option(result.data.id, result.data.name, result.data.id));
        }
        if (select) select.value = result.data.id;
        if (status) status.textContent = HC.text.templateSaved;
      })
      .catch(function (error) { if (status) status.textContent = String(error.message || error); });
  };

  function initOrderChain() {
    if (!HC.orderChainInitial || !$("order-chain-builder")) return;
    HC.orderChain = clone(HC.orderChainInitial);
    HC.renderOrderChain();
    HC.onModeChange();
  }

  // ------------------------------------------------------------ food modes
  /* Delivery and pickup are two different errands, so the form has to change
     shape, not just its wording: a pickup needs a collection time and a
     distance you are willing to drive; a delivery needs neither. */
  HC.onModeChange = function () {
    var pickup = document.querySelector('input[name="mode"][value="pickup"]');
    var isPickup = !!(pickup && pickup.checked);

    var label = $("budget-label");
    if (label) label.textContent = isPickup ? HC.text.budgetPickup : HC.text.budgetDelivery;

    var timeField = $("pickup-time-field");
    if (timeField) timeField.hidden = !isPickup;

    var distField = $("maxdist-field");
    if (distField) distField.hidden = !isPickup;

    var addr = document.querySelector('label[for="delivery_address"]');
    if (addr) addr.textContent = isPickup ? HC.text.addressPickup : HC.text.addressDelivery;
  };

  // `app.js` is deferred. On a cached/fast load the document can already be
  // interactive here; only initialise after onModeChange exists, otherwise a
  // first render throws and leaves the order editor looking inert.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initOrderChain);
  } else {
    initOrderChain();
  }

  // -------------------------------------------------------- call transport
  HC.onTransportChange = function () {
    var live = $("transport-live");
    var isLive = !!(live && live.checked);
    var panel = $("live-confirm-panel");
    var confirmation = $("confirm-live");
    var defaultTransport = $("transport-default");
    if (panel) panel.hidden = !isLive;
    if (confirmation) confirmation.required = isLive;
    if (defaultTransport) defaultTransport.disabled = isLive;

    var chip = $("transport-chip");
    var label = $("transport-label");
    var note = $("transport-note");
    if (chip) chip.classList.toggle("locked", isLive);
    if (label && HC.text) label.textContent = isLive ? HC.text.liveMode : HC.text.defaultTransport;
    if (note && HC.text) note.textContent = isLive ? HC.text.liveWarning : HC.text.defaultTransport;
  };

  HC.onSeatingChange = function () {
    var seating = $("seating");
    var field = $("seating-custom-field");
    var input = $("seating_custom");
    if (!seating || !field || !input) return;
    var custom = seating.value === "custom";
    field.hidden = !custom;
    input.disabled = !custom;
    input.required = custom;
    if (!custom) input.value = "";
  };

  // ---------------------------------------------------------- goal preview
  HC.previewGoal = function () {
    var form = $("cascade-form");
    var target = $("goal-preview");
    if (!form || !target) return;

    target.textContent = "…";
    fetch("/api/preview-goal?lang=" + encodeURIComponent(HC.lang), {
      method: "POST",
      body: new FormData(form)
    })
      .then(function (r) { return r.json(); })
      .then(function (data) { target.textContent = data.goal || data.error || ""; })
      .catch(function (err) { target.textContent = String(err); });
  };

  // --------------------------------------------------------------- cascade
  HC.startStream = function (orderId) {
    HC.canceled = false;
    if (HC.stream) { HC.stream.close(); HC.stream = null; }

    HC.stream = new EventSource(
      "/api/cascade-stream?order_id=" + encodeURIComponent(orderId) +
      "&lang=" + encodeURIComponent(HC.lang)
    );
    HC.stream.onmessage = function (evt) {
      var data;
      try { data = JSON.parse(evt.data); } catch (e) { return; }
      HC.handleEvent(data);
    };
    HC.stream.onerror = function () {
      if (HC.stream) { HC.stream.close(); HC.stream = null; }
    };
  };

  function setState(id, cls, glyph, title) {
    var el = $("state-" + id);
    if (!el) return;
    el.className = "state " + cls;
    el.textContent = glyph;
    if (title) el.title = title;
  }

  HC.handleEvent = function (data) {
    switch (data.type) {
      case "status":
        setStatus(data.text);
        break;

      case "dialing":
        setStatus(data.text);
        setState(data.id, "dialing", "◌", data.text);
        break;

      case "connected":
        bumpCallCounter();
        setStatus(data.text);
        setState(data.id, "live", "●", data.text);
        break;

      case "activity":
        logLine(data.line);
        break;

      case "rejected": {
        setState(data.id, "no", "✕", data.reason);
        var card = $("cand-" + data.id);
        if (card) card.classList.add("rejected");
        var reason = $("reason-" + data.id);
        if (reason) reason.textContent = data.label + ": " + data.reason;
        break;
      }

      case "accepted": {
        setState(data.id, "yes", "✓", data.text || "");
        var okCard = $("cand-" + data.id);
        if (okCard) okCard.classList.add("accepted");
        break;
      }

      case "outcome": {
        var out = $("outcome");
        if (out) {
          out.innerHTML = data.html;
          if (window.htmx) window.htmx.process(out);
        }
        setStatus(data.text || "");
        var cancel = $("cancel-btn");
        if (cancel) cancel.disabled = true;
        break;
      }

      case "canceled":
        setStatus(data.text);
        if (HC.stream) { HC.stream.close(); HC.stream = null; }
        break;

      case "error":
        setStatus(data.text);
        logLine(data.text);
        if (HC.stream) { HC.stream.close(); HC.stream = null; }
        break;

      case "done":
        if (HC.stream) { HC.stream.close(); HC.stream = null; }
        break;
    }
  };

  HC.cancel = function (orderId) {
    HC.canceled = true;
    var body = new FormData();
    body.append("order_id", orderId);
    fetch("/api/cancel-cascade", { method: "POST", body: body });
    setStatus(HC.text.canceled);
    var btn = $("cancel-btn");
    if (btn) btn.disabled = true;
  };
})();
