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
