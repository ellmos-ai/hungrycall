"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");


test("map initialization creates the center, radius and OSM layer without console errors", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "hungrycall", "static", "app.js"),
    "utf8"
  );
  const calls = [];
  const map = {
    setView(center, zoom) { calls.push(["setView", center, zoom]); return this; },
    remove() { calls.push(["remove"]); }
  };
  const addable = (kind) => ({
    addTo(target) { calls.push([kind, "addTo", target === map]); return this; },
    bindPopup() { return this; }
  });
  const document = {
    readyState: "complete",
    documentElement: { dataset: {} },
    getElementById(id) { return id === "map" ? {} : null; },
    createElement() { return {}; },
    addEventListener() {}
  };
  const context = {
    window: {},
    document,
    localStorage: { setItem() {} },
    console,
    setTimeout,
    clearTimeout,
    L: {
      map(id) { calls.push(["map", id]); return map; },
      tileLayer(url, options) { calls.push(["tile", url, options.attribution]); return addable("tile"); },
      circleMarker(center, options) { calls.push(["center", center, options.radius]); return addable("center"); },
      circle(center, options) { calls.push(["circle", center, options.radius]); return addable("circle"); },
      divIcon(options) { return options; },
      marker() { return addable("marker"); }
    }
  };
  context.window.document = document;
  vm.runInNewContext(source, context, { filename: "app.js" });

  context.window.HC.initMap(52.6908773, 13.5823608, 4.5, []);

  const plainCalls = JSON.parse(JSON.stringify(calls));
  assert.deepEqual(plainCalls.find((call) => call[0] === "setView"), [
    "setView", [52.6908773, 13.5823608], 13
  ]);
  assert.deepEqual(plainCalls.find((call) => call[0] === "circle"), [
    "circle", [52.6908773, 13.5823608], 4500
  ]);
  assert.ok(calls.some((call) => call[0] === "tile"));
});


test("an interactive document initializes visible order inputs before the add button is used", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "hungrycall", "static", "app.js"),
    "utf8"
  );
  const byId = {};
  function element(tag) {
    let text = "";
    const node = {
      tag,
      children: [],
      style: {},
      dataset: {},
      appendChild(child) { this.children.push(child); return child; },
      addEventListener() {},
      setAttribute() {},
      focus() { this.focused = true; }
    };
    Object.defineProperty(node, "textContent", {
      get() { return text; },
      set(value) { text = String(value); this.children = []; }
    });
    return node;
  }
  const root = element("div");
  const walk = (node, found, className) => {
    if (node.tag === "input" && node.type === "text" && (!className || node.className === className)) found.push(node);
    (node.children || []).forEach((child) => walk(child, found, className));
    return found;
  };
  byId["order-chain-builder"] = root;
  byId.order_chain_json = element("input");
  byId.food_prompt = element("input");
  const document = {
    readyState: "interactive",
    documentElement: { dataset: {} },
    getElementById(id) { return byId[id] || null; },
    querySelector() { return null; },
    querySelectorAll(selector) { return walk(root, [], selector === ".order-product-input" ? "order-product-input" : undefined); },
    createElement(tag) { return element(tag); },
    addEventListener() {}
  };
  const context = {
    window: { HC: {
      text: {
        position: "Position", wish: "Wish", replacement: "Replacement", quantity: "Quantity",
        product: "Product", tags: "Tags",
        criteria: "Criteria", remove: "Remove", addReplacement: "Replacement",
        ruleSkip: "Skip", ruleAbort: "Abort", budgetDelivery: "Budget", budgetPickup: "Budget",
        addressDelivery: "Address", addressPickup: "Address"
      },
      orderChainInitial: {
        version: 1,
        posten: [{
          zellen: [{ menge: 1, produkt: "Burger", art: "essen", kriterien: [] }],
          tags: [], wenn_nichts_verfuegbar: "posten_weglassen"
        }]
      }
    } }, document, localStorage: { setItem() {} }, console, setTimeout, clearTimeout
  };
  context.window.document = document;
  vm.runInNewContext(source, context, { filename: "app.js" });

  const initialProducts = walk(root, [], "order-product-input");
  assert.equal(initialProducts.length, 1);
  assert.equal(initialProducts[0].value, "Burger");
  context.window.HC.addPosition();

  assert.equal(context.window.HC.orderChain.posten.length, 2);
  assert.equal(context.window.HC.orderChain.posten[1].zellen[0].produkt, "");
  const products = walk(root, [], "order-product-input");
  assert.equal(products.length, 2);
  assert.equal(products[1].focused, true);
});


test("a cell's criteria are visible on the cell, not just a count (E9)", () => {
  // Endabnahme-Befund 2026-08-22: only a bare count ("1") showed on the
  // cell before -- a price limit the user had actually set went unnoticed
  // until a call already acted on it. renderCell() now also puts a short
  // chip per criterion directly on the cell; clicking a chip opens the
  // same edit dialog the gear button does.
  const source = fs.readFileSync(
    path.join(__dirname, "..", "hungrycall", "static", "app.js"),
    "utf8"
  );
  const byId = {};
  function element(tag) {
    let text = "";
    const node = {
      tag,
      className: "",
      children: [],
      style: {},
      dataset: {},
      listeners: {},
      appendChild(child) { this.children.push(child); return child; },
      addEventListener(type, handler) { this.listeners[type] = handler; },
      setAttribute() {},
      focus() {}
    };
    Object.defineProperty(node, "textContent", {
      get() { return text; },
      set(value) { text = String(value); this.children = []; }
    });
    return node;
  }
  const root = element("div");
  const walk = (node, found, className) => {
    if (node.className === className) found.push(node);
    (node.children || []).forEach((child) => walk(child, found, className));
    return found;
  };
  byId["order-chain-builder"] = root;
  byId.order_chain_json = element("input");
  byId.food_prompt = element("input");
  const document = {
    readyState: "interactive",
    documentElement: { dataset: {} },
    getElementById(id) { return byId[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) {
      const node = element(tag);
      // make() sets .className via a plain assignment (not setAttribute),
      // so className must be a real, settable property here too.
      return node;
    },
    addEventListener() {}
  };
  const context = {
    window: { HC: {
      text: {
        position: "Position", wish: "Wish", replacement: "Replacement", quantity: "Quantity",
        product: "Product", tags: "Tags",
        criteria: "Criteria", remove: "Remove", addReplacement: "Replacement",
        ruleSkip: "Skip", ruleAbort: "Abort", budgetDelivery: "Budget", budgetPickup: "Budget",
        addressDelivery: "Address", addressPickup: "Address",
        criterionPrice: "Maximum price", criterionSpecial: "Special request",
        criterionQuestion: "Question", reactionAccept: "accept",
        reactionNext: "soft: next replacement", reactionReject: "hard: reject position"
      },
      orderChainInitial: {
        version: 1,
        posten: [{
          zellen: [{
            menge: 1, produkt: "Pizza Napoli", art: "essen",
            kriterien: [{ art: "hoechstpreis", wert: 12.5, reaktion_ja: "annehmen", reaktion_nein: "naechster_ersatz" }]
          }],
          tags: [], wenn_nichts_verfuegbar: "posten_weglassen"
        }]
      }
    } }, document, localStorage: { setItem() {} }, console, setTimeout, clearTimeout
  };
  context.window.document = document;
  vm.runInNewContext(source, context, { filename: "app.js" });

  const chips = walk(root, [], "criterion-chip");
  assert.equal(chips.length, 1);
  assert.equal(chips[0].textContent, "≤ 12.5 €");
  assert.equal(chips[0].title, "Maximum price: 12.5 — soft: next replacement");

  chips[0].listeners.click();
  assert.equal(context.window.HC.criteriaPosition, 0);
  assert.equal(context.window.HC.criteriaCell, 0);
});


test("custom seating input is enabled and required only for the custom choice", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "hungrycall", "static", "app.js"),
    "utf8"
  );
  const seating = { value: "any" };
  const field = { hidden: false };
  const input = { disabled: false, required: true, value: "stale text" };
  const byId = {
    seating,
    "seating-custom-field": field,
    seating_custom: input
  };
  const document = {
    readyState: "complete",
    documentElement: { dataset: {} },
    getElementById(id) { return byId[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return {}; },
    addEventListener() {}
  };
  const context = {
    window: {}, document, localStorage: { setItem() {} }, console, setTimeout, clearTimeout
  };
  context.window.document = document;
  vm.runInNewContext(source, context, { filename: "app.js" });

  context.window.HC.onSeatingChange();
  assert.equal(field.hidden, true);
  assert.equal(input.disabled, true);
  assert.equal(input.required, false);
  assert.equal(input.value, "");

  seating.value = "custom";
  context.window.HC.onSeatingChange();
  assert.equal(field.hidden, false);
  assert.equal(input.disabled, false);
  assert.equal(input.required, true);
});
