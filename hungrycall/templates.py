"""HTML for the HungryCall web interface.

Design note — the electric picnic map
--------------------------------------
HungryCall is a lively route through nearby food, not an analytics dashboard.
The light default feels like a white takeaway counter covered by a cobalt route,
violet waypoints and pink refusal marks. Grass-neon green appears only when a
line is genuinely live or a candidate succeeds. The dark switchboard remains
available as a deliberate second mode. The type system keeps one rule: *the
machine speaks in monospace, the human reads in sans*. Transcripts, activity
lines, phone numbers, prices and the goal text are machine speech.

No web fonts, no CDN. The page claimed offline capability while pulling a font
from Google; either the claim or the link had to go, and the claim is worth
more.
"""

import html
import json
from typing import Any, Dict, List, Optional

from hungrycall.i18n import SUPPORTED, t
from hungrycall.models import Branch, Concession, Mode, Restaurant, Seating
from hungrycall.phone_utils import mask_phone


def esc(value: Any) -> str:
    """Escape anything that came from a form before it goes into HTML."""
    return html.escape(str(value), quote=True)


# The approved empty-fridge motif is the product mark across the web UI. The
# accompanying wordmark remains real text, so the decorative image stays
# hidden from assistive technology instead of being announced twice.
BRAND_MARK = (
    '<img class="brand-mark" src="/static/brand/motiv.png" alt="" '
    'width="1024" height="1024" aria-hidden="true">'
)

FAVICON = "/static/brand/logo-square.png"


# --------------------------------------------------------------------------
# Design tokens and stylesheet
# --------------------------------------------------------------------------

STYLESHEET = """
:root {
  color-scheme: light;
  --ink:          #F7F9FF;
  --panel:        #FFFFFF;
  --panel-2:      #EEF2FF;
  --line:         #C7D2FE;
  --paper:        #18203B;
  --dim:          #667085;
  --brass:        #2563EB;
  --brass-lo:     #7C3AED;
  --violet:       #7C3AED;
  --pink:         #EC4899;
  --patch:        #82F21B;
  --patch-ink:    #347A00;
  --busy:         #EC4899;
  --busy-ink:     #B42367;
  --body-rules:   rgba(37,99,235,0.055);
  --header-bg:    rgba(255,255,255,0.92);
  --chip-bg:      rgba(238,242,255,0.82);
  --field-bg:     #FFFFFF;
  --accent-wash:  rgba(37,99,235,0.075);
  --success-wash: rgba(130,242,27,0.12);
  --facts-bg:     #F5F3FF;
  --log-bg:       #F4F5FF;
  --log-rule:     rgba(124,58,237,0.18);
  --warning-text: #A51D5D;
  --popup-bg:     #FFFFFF;
  --popup-attr:   rgba(255,255,255,0.9);
  --shadow:       0 12px 34px rgba(63,71,140,0.11);

  --font-display: "Segoe UI Variable Display", "Trebuchet MS", "Arial Narrow", system-ui, sans-serif;
  --font-body: system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "Cascadia Mono", Consolas, "SF Mono", "DejaVu Sans Mono", ui-monospace, monospace;

  --gap: 1.25rem;
  --radius: 4px;
}

html[data-theme="dark"] {
  color-scheme: dark;
  --ink:          #111327;
  --panel:        #191B35;
  --panel-2:      #25284D;
  --line:         #3E4474;
  --paper:        #F8FAFF;
  --dim:          #A7AED0;
  --brass:        #6EA8FF;
  --brass-lo:     #A78BFA;
  --violet:       #A78BFA;
  --pink:         #FF5CA8;
  --patch:        #8CFF32;
  --patch-ink:    #B7FF82;
  --busy:         #FF5CA8;
  --busy-ink:     #FF91C2;
  --body-rules:   rgba(110,168,255,0.045);
  --header-bg:    rgba(25,27,53,0.94);
  --chip-bg:      rgba(10,12,31,0.42);
  --field-bg:     #111327;
  --accent-wash:  rgba(110,168,255,0.10);
  --success-wash: rgba(140,255,50,0.08);
  --facts-bg:     rgba(7,9,25,0.38);
  --log-bg:       #0C0E20;
  --log-rule:     rgba(167,139,250,0.20);
  --warning-text: #FF9AC8;
  --popup-bg:     #191B35;
  --popup-attr:   rgba(17,19,39,0.88);
  --shadow:       0 14px 38px rgba(0,0,0,0.26);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

/* The hidden attribute must win. A class that sets display (.field is flex)
   outranks the user-agent rule for [hidden], which left the pickup-only
   fields on screen during a delivery — visible, and quietly submitted. */
[hidden] { display: none !important; }

body {
  background: var(--ink);
  color: var(--paper);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.55;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-image:
    radial-gradient(circle at 8% 5%, rgba(37,99,235,0.09), transparent 24rem),
    radial-gradient(circle at 92% 18%, rgba(236,72,153,0.07), transparent 22rem),
    repeating-linear-gradient(180deg, transparent 0 39px, var(--body-rules) 39px 40px);
  background-attachment: fixed;
}

h1, h2, h3, .eyebrow, .btn, th {
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

h1 { font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.05rem; }

a { color: var(--brass); }

.eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.22em;
  color: var(--brass);
}

.mono, code, pre, .num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

/* ---------- header ---------- */
header {
  border-bottom: 1px solid var(--line);
  background: var(--header-bg);
  backdrop-filter: blur(14px);
  position: sticky; top: 0; z-index: 50;
}
.header-inner {
  max-width: 1180px; margin: 0 auto; padding: 0.7rem 1.5rem;
  display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;
}
.brand { display: flex; align-items: center; gap: 0.7rem; text-decoration: none; color: inherit; }
.brand-mark { width: 42px; height: 42px; flex: none; display: block; object-fit: contain; }
.brand-name { font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; font-size: 1.05rem; }
.brand-sub { font-size: 0.7rem; color: var(--dim); letter-spacing: 0.04em; text-transform: none; }
.header-spacer { flex: 1 1 auto; }

.chip {
  display: inline-flex; align-items: center; gap: 0.45rem;
  border: 1px solid var(--line); border-radius: 999px;
  padding: 0.25rem 0.75rem; font-size: 0.78rem; color: var(--dim);
  background: var(--chip-bg);
}
.chip strong { color: var(--paper); font-family: var(--font-mono); }
.chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--patch); box-shadow: 0 0 0 3px var(--success-wash); flex: none; }
.chip.locked .dot { background: var(--busy); }
.theme-toggle { cursor: pointer; color: var(--paper); font-family: var(--font-mono); }
.theme-toggle:hover { border-color: var(--violet); color: var(--violet); }
.theme-toggle .theme-icon { color: var(--pink); font-size: 0.9rem; }

.langbar { display: flex; border: 1px solid var(--line); border-radius: 999px; overflow: hidden; }
.langbar a {
  padding: 0.25rem 0.7rem; font-size: 0.75rem; text-decoration: none;
  color: var(--dim); font-family: var(--font-mono); text-transform: uppercase;
}
.langbar a[aria-current="true"] { background: var(--brass); color: var(--ink); font-weight: 700; }

/* ---------- layout ---------- */
main { flex: 1; width: 100%; max-width: 1180px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
.stack { display: flex; flex-direction: column; gap: var(--gap); }
.split { display: grid; grid-template-columns: minmax(0,1.05fr) minmax(0,0.95fr); gap: var(--gap); align-items: start; }
@media (max-width: 940px) { .split { grid-template-columns: 1fr; } }

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.35rem;
  box-shadow: var(--shadow);
}
.panel > * + * { margin-top: 0.9rem; }
.panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; border-bottom: 1px solid var(--line); padding-bottom: 0.6rem; }

.muted { color: var(--dim); font-size: 0.9rem; }
.small { font-size: 0.82rem; }
.hr { border: none; border-top: 1px solid var(--line); }

/* ---------- landing ---------- */
.fridge-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.78fr);
  gap: clamp(1.5rem, 5vw, 4.5rem);
  align-items: center;
  padding: 0.5rem 0 2rem;
}
.hero { padding: 1rem 0; max-width: 62ch; }
.hero h1 { margin-bottom: 0.9rem; }
.claim {
  font-size: clamp(1.05rem, 2.2vw, 1.3rem);
  border-left: 3px solid var(--brass);
  padding-left: 1rem;
  color: var(--paper);
  background: linear-gradient(90deg, var(--accent-wash), transparent);
  padding-top: 0.35rem;
  padding-bottom: 0.35rem;
}
.hero .muted { margin-top: 0.9rem; }

.fridge-reveal {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #1C2552;
  box-shadow: var(--shadow);
}
.fridge-stage {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  isolation: isolate;
  background: #1C2552;
}
.fridge-stage::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
}
.fridge-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  will-change: opacity;
}
.fridge-layer-off {
  z-index: 0;
  opacity: 1;
  animation: fridge-dark-out 1.35s cubic-bezier(0.45, 0, 0.2, 1) 0.65s forwards;
}
.fridge-layer-on {
  z-index: 1;
  opacity: 0;
  animation: fridge-light-on 1.35s cubic-bezier(0.45, 0, 0.2, 1) 0.65s forwards;
}
.fridge-caption {
  border-top: 1px solid var(--line);
  background: var(--panel);
  color: var(--paper);
  padding: 0.85rem 1rem;
  font-size: 0.9rem;
  line-height: 1.45;
}
@keyframes fridge-dark-out {
  from { opacity: 1; }
  to { opacity: 0; }
}
@keyframes fridge-light-on {
  from { opacity: 0; }
  to { opacity: 1; }
}
@media (max-width: 820px) {
  .fridge-hero { grid-template-columns: 1fr; }
  .fridge-reveal { width: min(100%, 32rem); justify-self: center; }
}

.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); }
@media (max-width: 800px) { .tiles { grid-template-columns: 1fr; } }

.tile {
  display: block; text-decoration: none; color: inherit;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.6rem 1.5rem 1.5rem; position: relative; overflow: hidden;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
  box-shadow: var(--shadow);
}
.tile::before { content: ""; position: absolute; inset: 0 0 auto; height: 4px; background: linear-gradient(90deg, var(--brass), var(--violet), var(--pink)); }
.tile:hover, .tile:focus-visible { border-color: var(--brass); background: var(--panel-2); transform: translateY(-2px); }
.tile:focus-visible { outline: 2px solid var(--brass); outline-offset: 2px; }
.tile-jack {
  display: block;  /* an inline span ignores width and height and renders as a dot */
  width: 40px; height: 40px; border-radius: 50%; margin-bottom: 1rem;
  background: radial-gradient(circle at 32% 30%, #FFFFFF 0%, var(--brass) 40%, var(--violet) 100%);
  box-shadow: inset 0 0 0 5px var(--panel), 0 0 0 1px var(--violet);
  transition: box-shadow 0.18s ease;
}
.tile:nth-child(2) .tile-jack { background: radial-gradient(circle at 32% 30%, #FFFFFF 0%, var(--pink) 40%, var(--violet) 100%); }
.tile:hover .tile-jack, .tile:focus-visible .tile-jack { box-shadow: inset 0 0 0 5px var(--panel), 0 0 0 1px var(--violet), 0 0 20px rgba(124,58,237,0.32); }
.tile h2 { font-size: 1.75rem; letter-spacing: 0.04em; }
.tile .tile-sub { color: var(--brass); font-size: 0.85rem; margin-top: 0.2rem; }

/* The explanation is the reveal: closed by default, opens on hover or focus. */
.tile-hint {
  display: grid; grid-template-rows: 0fr;
  transition: grid-template-rows 0.28s ease, opacity 0.28s ease, margin-top 0.28s ease;
  opacity: 0; margin-top: 0;
}
.tile-hint > span { overflow: hidden; display: block; font-size: 0.92rem; color: var(--dim); }
.tile:hover .tile-hint, .tile:focus-visible .tile-hint, .tile:focus-within .tile-hint {
  grid-template-rows: 1fr; opacity: 1; margin-top: 1rem;
}
.tile-more { margin-top: 1.1rem; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.72rem; color: var(--brass); }

/* ---------- the cascade animation (the one signature element) ---------- */
.exchange { background: linear-gradient(135deg, var(--panel), var(--panel-2)); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--shadow); }
.exchange svg { width: 100%; height: auto; display: block; }

.cord-line { stroke: var(--brass); stroke-width: 2.5; }
.plug-head { fill: var(--pink); }
.station-ring { fill: none; stroke: var(--line); stroke-width: 2; }
.station-core { fill: var(--panel-2); stroke: var(--line); stroke-width: 1; }
.station-label { font-family: var(--font-mono); font-size: 11px; fill: var(--dim); }
/* Hidden until this station's turn comes. Without the base opacity, a delayed
   animation leaves the element in its normal state, so every verdict is on
   screen before the plug has reached it and the sequence reads backwards. */
.station-verdict { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.06em; opacity: 0; }

.cord { animation: cord-walk 13s infinite; }
.s1 .station-ring { animation: ring-busy 13s infinite; }
.s2 .station-ring { animation: ring-busy 13s infinite; animation-delay: 2.6s; }
.s3 .station-ring { animation: ring-ok 13s infinite; animation-delay: 5.2s; }
.v1 { animation: verdict-in 13s infinite; }
.v2 { animation: verdict-in 13s infinite; animation-delay: 2.6s; }
.v3 { animation: verdict-in 13s infinite; animation-delay: 5.2s; }
.v4 { animation: verdict-in 13s infinite; animation-delay: 7.4s; }
.s4 { animation: fade-out-station 13s infinite; animation-delay: 7.4s; }

@keyframes cord-walk {
  0%    { transform: translateX(0px); }
  8%    { transform: translateX(120px); }
  20%   { transform: translateX(120px); }
  28%   { transform: translateX(280px); }
  40%   { transform: translateX(280px); }
  48%   { transform: translateX(440px); }
  94%   { transform: translateX(440px); }
  100%  { transform: translateX(0px); }
}
@keyframes ring-busy {
  0%, 8%    { stroke: var(--line); stroke-width: 2; }
  12%, 16%  { stroke: var(--brass); stroke-width: 3; }
  20%, 100% { stroke: var(--busy); stroke-width: 3; }
}
@keyframes ring-ok {
  0%, 8%    { stroke: var(--line); stroke-width: 2; }
  12%, 16%  { stroke: var(--brass); stroke-width: 3; }
  20%, 100% { stroke: var(--patch); stroke-width: 4; }
}
@keyframes verdict-in {
  0%, 16%   { opacity: 0; }
  22%, 100% { opacity: 1; }
}
@keyframes fade-out-station {
  0%, 12%   { opacity: 1; }
  24%, 100% { opacity: 0.35; }
}

.legend { display: grid; gap: 0.4rem; margin-top: 1.2rem; }
.legend div { display: flex; align-items: baseline; gap: 0.6rem; font-size: 0.9rem; color: var(--dim); }
.legend .key { width: 0.6rem; height: 0.6rem; border-radius: 50%; flex: none; transform: translateY(-1px); }
.legend .k-busy { background: var(--busy); }
.legend .k-ok { background: var(--patch); }
.legend .k-off { background: var(--line); }

@media (prefers-reduced-motion: reduce) {
  .fridge-layer-off { opacity: 0; animation: none !important; }
  .fridge-layer-on { opacity: 1; animation: none !important; }
  .cord { transform: translateX(440px); }
  .cord, .s1 .station-ring, .s2 .station-ring, .s3 .station-ring,
  .v1, .v2, .v3, .v4, .s4, .pulse, .dialing { animation: none !important; }
  .s1 .station-ring, .s2 .station-ring { stroke: var(--busy); stroke-width: 3; }
  .s3 .station-ring { stroke: var(--patch); stroke-width: 4; }
  .v1, .v2, .v3, .v4 { opacity: 1; }
  .s4 { opacity: 0.35; }
  .tile-hint { grid-template-rows: 1fr; opacity: 1; margin-top: 1rem; }
}

/* ---------- forms ---------- */
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0.9rem; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 0.9rem; }
@media (max-width: 700px) { .grid3, .grid2 { grid-template-columns: 1fr; } }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field.wide { grid-column: 1 / -1; }
label { font-size: 0.78rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--dim); font-family: var(--font-display); }
input, select, textarea {
  background: var(--field-bg); color: var(--paper);
  border: 1px solid var(--line); border-radius: var(--radius);
  padding: 0.6rem 0.7rem; font-size: 0.95rem; font-family: var(--font-body);
}
input.num, input[type="number"], input[type="time"], input[type="date"] { font-family: var(--font-mono); }
input:focus, select:focus, textarea:focus { outline: 2px solid var(--brass); outline-offset: 1px; border-color: var(--brass); }
.help { font-size: 0.8rem; color: var(--dim); }

.btn {
  border: 1px solid var(--brass); background: var(--brass); color: var(--ink);
  border-radius: var(--radius); padding: 0.7rem 1.15rem; cursor: pointer;
  font-size: 0.82rem; display: inline-flex; align-items: center; gap: 0.5rem;
}
.btn:hover { background: var(--violet); border-color: var(--violet); color: #FFFFFF; }
.btn:focus-visible { outline: 2px solid var(--paper); outline-offset: 2px; }
.btn.ghost { background: transparent; color: var(--paper); border-color: var(--line); }
.btn.ghost:hover { border-color: var(--brass); color: var(--brass); }
.btn.danger { background: transparent; color: var(--busy); border-color: var(--busy); }
.btn.danger:hover { background: var(--busy); color: var(--ink); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-row { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }

/* mode switch: two real choices, not a decorative toggle */
.switch { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
@media (max-width: 620px) { .switch { grid-template-columns: 1fr; } }
.switch label {
  display: block; cursor: pointer; border: 1px solid var(--line); border-radius: var(--radius);
  padding: 0.85rem 1rem; text-transform: none; letter-spacing: 0; font-family: var(--font-body);
  color: var(--paper);
}
.switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.switch label .t { font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.9rem; display: block; }
.switch label .n { font-size: 0.82rem; color: var(--dim); display: block; margin-top: 0.35rem; }
.switch input:checked + label { border-color: var(--brass); background: var(--panel-2); }
.switch input:checked + label .t { color: var(--brass); }
.switch input:focus-visible + label { outline: 2px solid var(--brass); outline-offset: 2px; }

.checks { display: flex; flex-direction: column; gap: 0.5rem; }
.check { display: flex; gap: 0.6rem; align-items: flex-start; font-size: 0.92rem; }
.check input { margin-top: 0.25rem; accent-color: var(--brass); }
.tier { font-family: var(--font-mono); font-size: 0.75rem; color: var(--brass); border: 1px solid var(--brass-lo); border-radius: 3px; padding: 0 0.3rem; }

.transport-switch { margin-top: 0.65rem; }
.transport-switch label { position: relative; overflow: hidden; }
.transport-switch label::after { content: ""; position: absolute; inset: auto 0 0; height: 3px; background: var(--brass); opacity: 0; }
.transport-switch input:checked + label::after { opacity: 1; }
.transport-switch input[value="live"]:checked + label { border-color: var(--pink); background: rgba(236,72,153,0.07); }
.transport-switch input[value="live"]:checked + label .t { color: var(--busy-ink); }
.transport-switch input[value="live"]:checked + label::after { background: linear-gradient(90deg, var(--pink), var(--violet)); }
.live-confirm { border: 1px solid var(--pink); border-left: 4px solid var(--pink); background: rgba(236,72,153,0.07); border-radius: var(--radius); padding: 0.85rem 1rem; }
.live-confirm strong { color: var(--busy-ink); }
.live-confirm .check { margin-top: 0.6rem; }

/* ---------- candidates ---------- */
.candidates { display: flex; flex-direction: column; gap: 0.6rem; }
.cand {
  display: flex; gap: 0.8rem; align-items: flex-start;
  border: 1px solid var(--line); border-radius: var(--radius);
  padding: 0.75rem 0.85rem; background: var(--panel);
  transition: border-color 0.2s, opacity 0.2s;
}
.cand.off { opacity: 0.4; }
.cand.rejected { border-color: var(--busy); }
.cand.rejected .cand-name { text-decoration: line-through; }
.cand.accepted { border-color: var(--patch); background: var(--success-wash); }
.cand-rank { font-family: var(--font-mono); color: var(--brass); width: 1.6rem; text-align: right; flex: none; padding-top: 0.1rem; }
.cand-body { flex: 1; min-width: 0; }
.cand-name { font-weight: 600; }
.cand-meta { font-size: 0.8rem; color: var(--dim); }
.cand-meta .num { color: var(--paper); }
.cand-reason { font-size: 0.82rem; color: var(--busy-ink); margin-top: 0.3rem; font-family: var(--font-mono); }
.cand-tools { display: flex; flex-direction: column; gap: 0.2rem; flex: none; }
.mini {
  background: var(--panel-2); color: var(--paper); border: 1px solid var(--line);
  border-radius: 3px; font-size: 0.7rem; line-height: 1; padding: 0.25rem 0.4rem; cursor: pointer;
}
.mini:hover { border-color: var(--brass); color: var(--brass); }
.state { flex: none; width: 2rem; text-align: center; font-size: 1.15rem; padding-top: 0.05rem; }
.state.dialing { color: var(--brass); animation: pulse 1.1s infinite; }
.state.live { color: var(--patch-ink); text-shadow: 0 0 10px var(--patch); }
.state.no { color: var(--busy-ink); }
.state.yes { color: var(--patch-ink); text-shadow: 0 0 10px var(--patch); }
@keyframes pulse { 0%,100% { opacity: 0.35; } 50% { opacity: 1; } }

/* ---------- bands, monitor, result ---------- */
.band {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  border: 1px solid var(--brass-lo); border-left: 3px solid var(--brass);
  background: var(--accent-wash); border-radius: var(--radius); padding: 0.55rem 0.85rem;
  font-size: 0.85rem;
}
.band .k { color: var(--brass); font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.72rem; }
.band .v { font-family: var(--font-mono); }

.status { font-family: var(--font-mono); font-size: 0.9rem; color: var(--dim); }
.log {
  background: var(--log-bg); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 0.6rem 0.75rem; max-height: 190px; overflow-y: auto;
  font-family: var(--font-mono); font-size: 0.76rem; color: var(--dim);
}
.log div { padding: 0.12rem 0; border-bottom: 1px dotted var(--log-rule); word-break: break-word; }
.log div:last-child { border-bottom: none; color: var(--paper); }

.result { border: 1px solid var(--patch); border-left: 4px solid var(--patch); border-radius: var(--radius); background: var(--success-wash); padding: 1.35rem; }
.result > * + * { margin-top: 1rem; }
.result h2 { color: var(--patch-ink); }
.result-sentence { font-size: 1.15rem; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.9rem; background: var(--facts-bg); padding: 0.9rem; border-radius: var(--radius); }
.fact .k { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--dim); font-family: var(--font-display); }
.fact .v { font-family: var(--font-mono); font-size: 1.1rem; }
.callback { border: 1px solid var(--patch); border-radius: var(--radius); padding: 0.8rem 1rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.callback .num { font-size: 1.25rem; color: var(--patch-ink); letter-spacing: 0.06em; }
details { border: 1px solid var(--line); border-radius: var(--radius); padding: 0.7rem 0.85rem; }
summary { cursor: pointer; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.8rem; color: var(--brass); }
pre { white-space: pre-wrap; word-break: break-word; font-size: 0.78rem; color: var(--dim); margin-top: 0.7rem; }

.notice { border: 1px solid var(--line); border-left: 3px solid var(--dim); border-radius: var(--radius); padding: 0.7rem 0.9rem; font-size: 0.85rem; color: var(--dim); }
.notice.warn { border-left-color: var(--busy); color: var(--warning-text); }
.tag { font-family: var(--font-mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; border: 1px solid var(--line); border-radius: 3px; padding: 0.05rem 0.35rem; color: var(--dim); }

.loading { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 2.5rem 1rem; text-align: center; }
.loading .ring { width: 46px; height: 46px; border-radius: 50%; border: 3px solid var(--line); border-top-color: var(--brass); animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator, .htmx-request.htmx-indicator { display: flex; }

#map-shell { position: sticky; top: 5.5rem; }
#map { height: 460px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel-2); }
/* Numbered pin: the number is the position in the call order. */
.map-pin span {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--brass); color: var(--ink);
  font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700;
  border: 2px solid var(--ink); box-shadow: 0 2px 6px rgba(0,0,0,0.5);
}
.leaflet-popup-content-wrapper, .leaflet-popup-tip { background: var(--popup-bg); color: var(--paper); }
.leaflet-popup-content { font-family: var(--font-body); font-size: 0.85rem; }
.leaflet-control-attribution { background: var(--popup-attr) !important; color: var(--dim) !important; }
.leaflet-control-attribution a { color: var(--brass) !important; }

table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--line); }
th { font-size: 0.7rem; letter-spacing: 0.12em; color: var(--dim); }
td.num { font-family: var(--font-mono); }

footer { border-top: 1px solid var(--line); padding: 1.5rem; color: var(--dim); font-size: 0.8rem; }
footer .footer-inner { max-width: 1180px; margin: 0 auto; display: flex; gap: 1.5rem; flex-wrap: wrap; justify-content: space-between; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 1rem; top: 1rem; background: var(--brass); color: var(--ink); padding: 0.5rem 1rem; z-index: 100; }
"""


# --------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------

def render_page(
    body: str,
    lang: str,
    *,
    path: str = "/",
    with_map: bool = False,
    title: Optional[str] = None,
) -> str:
    """Wrap page content in the shared shell."""
    page_title = title or t("app.name", lang)
    leaflet = ""
    if with_map:
        leaflet = (
            '<link rel="stylesheet" href="/static/leaflet.css">'
            '<script src="/static/leaflet.js" defer></script>'
        )

    lang_links = "".join(
        f'<a href="?lang={code}" aria-current="{"true" if code == lang else "false"}" '
        f'rel="nofollow">{code}</a>'
        for code in SUPPORTED
    )

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(page_title)} — {esc(t("app.name", lang))}</title>
<link rel="icon" type="image/png" href="{FAVICON}">
<script>
try {{
  if (localStorage.getItem("hc-theme") === "dark") document.documentElement.dataset.theme = "dark";
}} catch (error) {{ /* storage can be unavailable; light remains the safe default */ }}
</script>
<script src="/static/htmx.min.js" defer></script>
<script src="/static/app.js" defer></script>
<script src="/static/huckepack.js" defer></script>
{leaflet}
<style>{STYLESHEET}</style>
</head>
<body>
<a class="skip" href="#content">{esc(t("nav.start", lang))}</a>
<header>
  <div class="header-inner">
    <a class="brand" href="/?lang={lang}">
      {BRAND_MARK}
      <span>
        <span class="brand-name">{esc(t("app.name", lang))}</span>
        <span class="brand-sub">{esc(t("app.subtitle", lang))}</span>
      </span>
    </a>
    <span class="header-spacer"></span>
    <span class="chip" id="transport-chip" title="{esc(t("safety.mode.dry.explain", lang))}">
      <span class="dot"></span><span id="transport-label">{esc(t("safety.mode.dry", lang))}</span>
    </span>
    <span class="chip" title="{esc(t("safety.calls.explain", lang))}">
      {esc(t("safety.calls", lang))} <strong id="call-counter">0</strong>
    </span>
    <a class="chip" href="/history?lang={lang}" style="text-decoration:none;">{esc(t("nav.history", lang))}</a>
    <button class="chip theme-toggle" type="button" id="theme-toggle"
            data-light="{esc(t("theme.light", lang))}" data-dark="{esc(t("theme.dark", lang))}"
            aria-label="{esc(t("theme.switch.aria", lang))}" aria-pressed="false"
            onclick="HC.toggleTheme()">
      <span class="theme-icon" aria-hidden="true">◐</span><span id="theme-label">{esc(t("theme.dark", lang))}</span>
    </button>
    <nav class="langbar" aria-label="{esc(t("lang.switch.aria", lang))}">{lang_links}</nav>
  </div>
</header>
<main id="content">
{body}
</main>
<footer><div class="footer-inner">
  <span>{esc(t("safety.dataflow", lang))}</span>
  <span class="mono">{esc(t("safety.live.gated", lang))}</span>
</div></footer>
</body>
</html>"""


# --------------------------------------------------------------------------
# Landing page: the two tiles and the cascade animation
# --------------------------------------------------------------------------

def render_landing(lang: str) -> str:
    """The first screen: choose a branch, and see what a cascade actually does."""
    stations = [
        ("s1", "v1", 120, "Trattoria", t("landing.anim.rejected", lang), "var(--busy)"),
        ("s2", "v2", 280, "Burger House", t("landing.anim.rejected", lang), "var(--busy)"),
        ("s3", "v3", 440, "Asia Wok", t("landing.anim.booked", lang), "var(--patch)"),
        ("s4", "v4", 600, "Sushi Kudo", t("landing.anim.never", lang), "var(--dim)"),
    ]
    station_svg = ""
    for cls, vcls, x, name, verdict, colour in stations:
        station_svg += f"""
        <g class="{cls}" transform="translate({x},70)">
          <circle class="station-ring" r="20"></circle>
          <circle class="station-core" r="13"></circle>
          <text class="station-label" text-anchor="middle" y="45">{esc(name)}</text>
          <text class="station-verdict {vcls}" text-anchor="middle" y="61" fill="{colour}">{esc(verdict)}</text>
        </g>"""

    return f"""
<section class="fridge-hero">
  <div class="hero">
    <p class="eyebrow">{esc(t("app.tagline", lang))}</p>
    <h1>{esc(t("landing.choose", lang))}</h1>
    <p class="claim">{esc(t("landing.claim", lang))}</p>
    <p class="muted">{esc(t("landing.lead", lang))}</p>
  </div>
  <figure class="fridge-reveal">
    <div class="fridge-stage" role="img" aria-label="{esc(t("landing.fridge.alt", lang))}">
      <img class="fridge-layer fridge-layer-off" src="/static/brand/motiv-aus.png"
           alt="" width="1024" height="1024" aria-hidden="true">
      <img class="fridge-layer fridge-layer-on" src="/static/brand/motiv-an.png"
           alt="" width="1024" height="1024" aria-hidden="true">
    </div>
    <figcaption class="fridge-caption">{esc(t("landing.fridge.caption", lang))}</figcaption>
  </figure>
</section>

<section class="tiles" aria-label="{esc(t("landing.choose", lang))}">
  <a class="tile" href="/order?lang={lang}">
    <span class="tile-jack" aria-hidden="true"></span>
    <h2>{esc(t("landing.tile.food.title", lang))}</h2>
    <div class="tile-sub">{esc(t("landing.tile.food.sub", lang))}</div>
    <span class="tile-hint"><span>{esc(t("landing.tile.food.hint", lang))}</span></span>
    <div class="tile-more">{esc(t("landing.tile.reveal", lang))} →</div>
  </a>
  <a class="tile" href="/reserve?lang={lang}">
    <span class="tile-jack" aria-hidden="true"></span>
    <h2>{esc(t("landing.tile.table.title", lang))}</h2>
    <div class="tile-sub">{esc(t("landing.tile.table.sub", lang))}</div>
    <span class="tile-hint"><span>{esc(t("landing.tile.table.hint", lang))}</span></span>
    <div class="tile-more">{esc(t("landing.tile.reveal", lang))} →</div>
  </a>
</section>

<section class="exchange" style="margin-top:1.25rem;" aria-labelledby="how-title">
  <div class="panel-head" style="border:none;padding:0;">
    <h2 id="how-title">{esc(t("landing.anim.title", lang))}</h2>
  </div>
  <p class="muted" style="margin:0.5rem 0 1rem;max-width:70ch;">{esc(t("landing.anim.lead", lang))}</p>

  <svg viewBox="0 0 700 150" role="img"
       aria-label="{esc(t("landing.anim.legend.1", lang))} {esc(t("landing.anim.legend.2", lang))} {esc(t("landing.anim.legend.3", lang))}">
    <line x1="0" y1="70" x2="700" y2="70" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 5"></line>
    {station_svg}
    <g class="cord">
      <line class="cord-line" x1="-900" y1="70" x2="0" y2="70"></line>
      <circle class="plug-head" cx="0" cy="70" r="6"></circle>
    </g>
  </svg>

  <div class="legend">
    <div><span class="key k-busy"></span>{esc(t("landing.anim.legend.1", lang))}</div>
    <div><span class="key k-ok"></span>{esc(t("landing.anim.legend.2", lang))}</div>
    <div><span class="key k-off"></span>{esc(t("landing.anim.legend.3", lang))}</div>
  </div>
</section>

<section class="panel" style="margin-top:1.25rem;">
  <h3>{esc(t("landing.pattern.title", lang))}</h3>
  <p class="muted">{esc(t("landing.pattern.body", lang))}</p>
  <p class="small mono">{esc(t("landing.pattern.link", lang))}</p>
</section>
"""


# --------------------------------------------------------------------------
# Branch pages
# --------------------------------------------------------------------------

def _scenario_options(scenarios: List[str], selected: str) -> str:
    return "".join(
        f'<option value="{esc(s)}"{" selected" if s == selected else ""}>{esc(s)}</option>'
        for s in scenarios
    )


def render_branch_page(
    branch: Branch,
    lang: str,
    scenarios: List[str],
    default_scenario: str,
) -> str:
    """Step 1 of a branch: where you are, plus the branch's own questions."""
    is_food = branch is Branch.FOOD
    title_key = "food.title" if is_food else "table.title"
    address_label = t("form.address", lang) if is_food else t("form.address.pickup", lang)

    detail = render_food_fields(lang) if is_food else render_table_fields(lang)

    return f"""
<div class="split">
  <div class="stack">
    <div class="panel">
      <div class="panel-head">
        <h2>{esc(t(title_key, lang))}</h2>
        <a class="small" href="/?lang={lang}">← {esc(t("nav.back", lang))}</a>
      </div>

      <form id="search-form" hx-post="/api/search?lang={lang}"
            hx-target="#step2" hx-indicator="#search-indicator" hx-swap="innerHTML">
        <input type="hidden" name="branch" value="{branch.value}">
        <h3 class="eyebrow">{esc(t("form.where.title", lang))}</h3>
        <div class="grid3" style="margin-top:0.6rem;">
          <div class="field">
            <label for="postcode">{esc(t("form.postcode", lang))}</label>
            <input class="num" type="text" id="postcode" name="postcode" value="12345" required>
          </div>
          <div class="field">
            <label for="city">{esc(t("form.city", lang))}</label>
            <input type="text" id="city" name="city" value="Dorfstadt" required>
          </div>
          <div class="field">
            <label for="radius_km">{esc(t("form.radius", lang))}</label>
            <input type="number" id="radius_km" name="radius_km" value="3.0" step="0.5" min="0.5" max="20">
          </div>
          <div class="field wide">
            <label for="delivery_address">{esc(address_label)}</label>
            <input type="text" id="delivery_address" name="delivery_address"
                   value="Dorfstraße 10, 12345 Dorfstadt" required>
          </div>
          <div class="field wide">
            <label for="scenario">{esc(t("form.scenario", lang))}</label>
            <select id="scenario" name="scenario">{_scenario_options(scenarios, default_scenario)}</select>
            <span class="help">{esc(t("form.scenario.help", lang))}</span>
          </div>
        </div>

        <div class="notice" style="margin-top:0.9rem;">
          <label class="check" for="test-mode">
            <input type="checkbox" id="test-mode" name="test_mode" value="yes">
            <span><strong>{esc(t("search.test_mode.option", lang))}</strong><br>
              <span class="small">{esc(t("search.test_mode.help", lang))}</span>
            </span>
          </label>
        </div>

        {detail}

        {render_transport_controls(lang)}

        <div class="btn-row" style="margin-top:1.1rem;">
          <button type="submit" class="btn">{esc(t("form.search", lang))}</button>
          <span class="small muted" id="transport-note">{esc(t("safety.mode.dry.explain", lang))}</span>
        </div>
      </form>

      <div id="search-indicator" class="htmx-indicator">{render_search_loading(lang)}</div>
      <div id="step2"></div>
    </div>
  </div>

  <div id="map-shell">
    <div class="panel" style="padding:0.5rem;">
      <div id="map"></div>
    </div>
    {render_limits(lang)}
  </div>
</div>

<script>
window.HC = window.HC || {{}};
HC.lang = "{lang}";
HC.branch = "{branch.value}";
HC.text = {json.dumps({
    "budgetDelivery": t("food.budget.delivery", lang),
    "budgetPickup": t("food.budget.pickup", lang),
    "addressDelivery": t("form.address", lang),
    "addressPickup": t("form.address.pickup", lang),
    "canceled": t("cascade.canceled", lang),
    "rejected": t("cascade.rejected", lang),
    "dryMode": t("safety.mode.dry", lang),
    "dryExplain": t("safety.mode.dry.explain", lang),
    "liveMode": t("safety.mode.live", lang),
    "liveWarning": t("safety.live.warning", lang),
}, ensure_ascii=False)};
</script>
"""


def render_food_fields(lang: str) -> str:
    """Delivery is the default; pickup is a real switch, not a label change."""
    return f"""
<hr class="hr" style="margin:1.2rem 0;">
<h3 class="eyebrow">{esc(t("food.mode.title", lang))}</h3>
<div class="switch" style="margin-top:0.6rem;">
  <input type="radio" id="mode-delivery" name="mode" value="delivery" checked onchange="HC.onModeChange()">
  <label for="mode-delivery">
    <span class="t">{esc(t("food.mode.delivery", lang))}</span>
    <span class="n">{esc(t("food.mode.delivery.note", lang))}</span>
  </label>
  <input type="radio" id="mode-pickup" name="mode" value="pickup" onchange="HC.onModeChange()">
  <label for="mode-pickup">
    <span class="t">{esc(t("food.mode.pickup", lang))}</span>
    <span class="n">{esc(t("food.mode.pickup.note", lang))}</span>
  </label>
</div>

<div class="grid3" style="margin-top:1rem;">
  <div class="field wide">
    <label for="food_prompt">{esc(t("food.prompt", lang))}</label>
    <textarea id="food_prompt" name="food_prompt" rows="2" required>2x Cheeseburger, 1x große Pommes, 1x Cola Zero</textarea>
    <span class="help">{esc(t("food.prompt.help", lang))}</span>
  </div>
  <div class="field">
    <label for="customer_name">{esc(t("form.name", lang))}</label>
    <input type="text" id="customer_name" name="customer_name" value="Alex" required>
  </div>
  <div class="field">
    <label for="max_budget_eur" id="budget-label">{esc(t("food.budget.delivery", lang))}</label>
    <input type="number" id="max_budget_eur" name="max_budget_eur" value="35.00" step="0.50" min="1" required>
  </div>
  <div class="field" id="pickup-time-field" hidden>
    <label for="pickup_time">{esc(t("food.pickup.time", lang))}</label>
    <input type="time" id="pickup_time" name="pickup_time" value="19:30">
  </div>
  <div class="field wide">
    <span class="help">{esc(t("food.budget.help", lang))}</span>
  </div>
  <div class="field" id="maxdist-field" hidden>
    <label for="max_distance_km">{esc(t("food.maxdistance", lang))}</label>
    <input type="number" id="max_distance_km" name="max_distance_km" step="0.5" min="0.5" placeholder="5.0">
    <span class="help">{esc(t("food.maxdistance.help", lang))}</span>
  </div>
</div>
"""


TABLE_CONCESSIONS: List[Concession] = [
    Concession(key="indoor_ok", label="an indoor table is acceptable instead of an outdoor one", tier=1),
    Concession(key="time_flex", label="a table one hour earlier or later is acceptable", tier=2),
    Concession(key="deposit_ok", label="a booking deposit of up to 15 EUR is acceptable", tier=3),
]


def render_table_fields(lang: str) -> str:
    """The table branch asks about time, people and seating. No price anywhere."""
    checks = ""
    for concession in TABLE_CONCESSIONS:
        checks += f"""
    <label class="check">
      <input type="checkbox" name="concessions" value="{concession.key}">
      <span>{esc(t("table.concession." + concession.key, lang))}
        <span class="tier">{esc(t("table.concession.order", lang, order=concession.tier))}</span>
      </span>
    </label>"""

    return f"""
<hr class="hr" style="margin:1.2rem 0;">
<h3 class="eyebrow">{esc(t("table.when.title", lang))}</h3>
<input type="hidden" name="mode" value="reservation">
<div class="grid3" style="margin-top:0.6rem;">
  <div class="field">
    <label for="reservation_date">{esc(t("table.date", lang))}</label>
    <input type="date" id="reservation_date" name="reservation_date" value="2026-08-07" required>
  </div>
  <div class="field">
    <label for="reservation_time">{esc(t("table.time", lang))}</label>
    <input type="time" id="reservation_time" name="reservation_time" value="19:00" required>
  </div>
  <div class="field">
    <label for="party_size">{esc(t("table.party", lang))}</label>
    <input type="number" id="party_size" name="party_size" value="4" min="1" max="40" required>
    <span class="help">{esc(t("table.party.help", lang))}</span>
  </div>
  <div class="field">
    <label for="seating">{esc(t("table.seating", lang))}</label>
    <select id="seating" name="seating">
      <option value="any" selected>{esc(t("table.seating.any", lang))}</option>
      <option value="indoor">{esc(t("table.seating.indoor", lang))}</option>
      <option value="outdoor">{esc(t("table.seating.outdoor", lang))}</option>
    </select>
    <span class="help">{esc(t("table.seating.help", lang))}</span>
  </div>
  <div class="field">
    <label for="customer_name">{esc(t("form.name", lang))}</label>
    <input type="text" id="customer_name" name="customer_name" value="Alex" required>
  </div>
  <div class="field">
    <label for="food_prompt">{esc(t("table.wish", lang))}</label>
    <input type="text" id="food_prompt" name="food_prompt" value="Italienisch" required>
    <span class="help">{esc(t("table.wish.help", lang))}</span>
  </div>
</div>

<hr class="hr" style="margin:1.2rem 0;">
<h3 class="eyebrow">{esc(t("table.concessions.title", lang))}</h3>
<p class="help" style="margin:0.5rem 0 0.8rem;max-width:72ch;">{esc(t("table.concessions.help", lang))}</p>
<div class="checks">{checks}</div>
"""


def render_transport_controls(lang: str) -> str:
    """A real transport choice with a second, explicit live confirmation."""
    return f"""
<hr class="hr" style="margin:1.2rem 0;">
<h3 class="eyebrow">{esc(t("transport.title", lang))}</h3>
<div class="switch transport-switch">
  <input type="radio" id="transport-dry" name="transport" value="dry_run" checked
         onchange="HC.onTransportChange()">
  <label for="transport-dry">
    <span class="t">{esc(t("safety.mode.dry", lang))}</span>
    <span class="n">{esc(t("safety.mode.dry.explain", lang))}</span>
  </label>
  <input type="radio" id="transport-live" name="transport" value="live"
         onchange="HC.onTransportChange()">
  <label for="transport-live">
    <span class="t">{esc(t("safety.mode.live", lang))}</span>
    <span class="n"><strong>{esc(t("safety.live.warning", lang))}</strong> · {esc(t("safety.live.balance", lang))}</span>
  </label>
</div>
<div class="live-confirm" id="live-confirm-panel" hidden style="margin-top:0.7rem;">
  <strong>{esc(t("safety.live.warning", lang))}</strong>
  <p class="small">{esc(t("safety.live.confirm.help", lang))}</p>
  <label class="check" for="confirm-live">
    <input type="checkbox" id="confirm-live" name="confirm_live" value="yes">
    <span>{esc(t("safety.live.confirm", lang))}</span>
  </label>
</div>
"""


def render_limits(lang: str) -> str:
    """The live gate and remaining unverified boundaries, shown in context."""
    return f"""
<div class="notice warn" style="margin-top:0.7rem;">
  <strong>{esc(t("safety.live.warning", lang))}</strong><br>
  {esc(t("safety.live.why", lang))}
</div>
<div class="notice" style="margin-top:0.5rem;">
  <span class="tag">{esc(t("search.source.badge", lang))}</span> {esc(t("search.mode.explain", lang))}
</div>
<div class="notice" style="margin-top:0.5rem;">{esc(t("safety.dataflow", lang))}</div>
<div class="notice" style="margin-top:0.5rem;">{esc(t("safety.tiles", lang))}</div>"""


def render_search_loading(lang: str) -> str:
    return f"""
<div class="loading">
  <div class="ring" aria-hidden="true"></div>
  <div>
    <h3>{esc(t("search.loading.title", lang))}</h3>
    <p class="muted small">{esc(t("search.loading.sub", lang))}</p>
  </div>
</div>"""


# --------------------------------------------------------------------------
# Step 2: candidates
# --------------------------------------------------------------------------

def render_search_error(lang: str, error_code: str, radius_km: float) -> str:
    """Render a failed search without inventing a candidate list."""
    if error_code == "address_not_found":
        title = t("search.error.address.title", lang)
        body = t("search.error.address.body", lang)
    elif error_code == "no_restaurants":
        title = t("search.error.none.title", lang)
        body = t("search.error.none.body", lang, radius=f"{radius_km:g}")
    else:
        error_code = "service_unavailable"
        title = t("search.error.service.title", lang)
        body = t("search.error.service.body", lang)

    return f"""
<hr class="hr" style="margin:1.3rem 0 1rem;">
<div class="notice warn" role="alert" data-search-error="{esc(error_code)}">
  <strong>{esc(title)}</strong><br>
  <span class="small">{esc(body)}</span>
</div>"""

def render_candidate_step(
    lang: str,
    branch: Branch,
    ranked: List[Restaurant],
    skipped: List[tuple],
    lat: float,
    lon: float,
    radius_km: float,
    form_state: Dict[str, Any],
    source_count: int,
    test_mode: bool,
) -> str:
    """The list we will work down, in the order we will work down it."""
    if not ranked:
        return f'<div class="notice warn" style="margin-top:1rem;">{esc(t("candidates.none", lang))}</div>'

    cards = ""
    for rank, restaurant in enumerate(ranked, start=1):
        meta = [", ".join(restaurant.cuisines), mask_phone(restaurant.phone)]
        if restaurant.distance_km is not None:
            meta.append(f'{restaurant.distance_km:.1f} {t("candidates.distance", lang)}')
        if branch is Branch.TABLE:
            meta.append(t("candidates.seats", lang, n=restaurant.max_party_size))
            if restaurant.has_outdoor_seating:
                meta.append(t("candidates.outdoor", lang))
        if restaurant.is_favorite:
            meta.append("★ " + t("candidates.favorite", lang))

        cards += f"""
      <div class="cand" id="cand-{esc(restaurant.id)}" data-id="{esc(restaurant.id)}">
        <span class="cand-rank" data-rank>{rank}</span>
        <input type="checkbox" name="selected_restaurants" value="{esc(restaurant.id)}" checked
               aria-label="{esc(restaurant.name)}: {esc(t("candidates.include", lang))}"
               onchange="HC.onToggle(this)">
        <span class="cand-body">
          <span class="cand-name">{esc(restaurant.name)}</span>
          <span class="cand-meta">{esc(" · ".join(meta))}</span>
          <span class="cand-reason" id="reason-{esc(restaurant.id)}"></span>
        </span>
        <span class="cand-tools">
          <button type="button" class="mini" onclick="HC.move('{esc(restaurant.id)}',-1)"
                  aria-label="{esc(t("candidates.order.up", lang))}">▲</button>
          <button type="button" class="mini" onclick="HC.move('{esc(restaurant.id)}',1)"
                  aria-label="{esc(t("candidates.order.down", lang))}">▼</button>
        </span>
        <span class="state" id="state-{esc(restaurant.id)}" aria-live="polite"></span>
      </div>"""

    skipped_html = ""
    if skipped:
        rows = "".join(
            f"<div class='cand off'><span class='cand-rank'>—</span>"
            f"<span class='cand-body'><span class='cand-name'>{esc(r.name)}</span>"
            f"<span class='cand-meta'>{esc(reason)}</span></span></div>"
            for r, reason in skipped
        )
        skipped_html = f"""
      <div class="small muted" style="display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-top:0.5rem;">
        <span>{esc(t("candidates.closed.count", lang, n=len(skipped)))}</span>
        <button type="button" class="mini" onclick="HC.toggleSkipped(this)"
                data-show="{esc(t("candidates.closed.show", lang))}"
                data-hide="{esc(t("candidates.closed.hide", lang))}">{esc(t("candidates.closed.show", lang))}</button>
      </div>
      <div id="skipped" hidden>{rows}</div>"""

    hidden_state = "".join(
        f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">'
        for k, v in form_state.items()
        if v is not None and k != "concessions"
    )
    for key in form_state.get("concessions", []) or []:
        hidden_state += f'<input type="hidden" name="concessions" value="{esc(key)}">'

    start_key = "cascade.start.food" if branch is Branch.FOOD else "cascade.start.table"
    if test_mode:
        source_banner = (
            '<div class="notice warn" role="status" data-test-mode="active" '
            'style="margin-bottom:0.9rem;">'
            f'<strong>{esc(t("search.test_mode.active.title", lang))}</strong><br>'
            f'<span class="small">{esc(t("search.test_mode.active.body", lang, n=source_count))}</span>'
            '</div>'
        )
    else:
        source_banner = (
            '<div class="notice" role="status" data-search-source="overpass" '
            'style="margin-bottom:0.9rem;">'
            f'{esc(t("search.source.overpass", lang, n=source_count, radius=f"{radius_km:g}"))}'
            '</div>'
        )
    transport_banner = ""
    if form_state.get("transport") == "live":
        transport_banner = (
            '<div class="live-confirm" style="margin-bottom:0.9rem;">'
            f'<strong>{esc(t("safety.live.warning", lang))}</strong><br>'
            f'<span class="small">{esc(t("safety.live.confirmed", lang))}</span>'
            "</div>"
        )

    return f"""
<hr class="hr" style="margin:1.3rem 0 1rem;">
<div class="panel-head" style="border:none;padding:0;">
  <h3>{esc(t("candidates.title", lang))}</h3>
  <span class="small muted mono">{len(ranked)}</span>
</div>
<p class="help" style="margin:0.4rem 0 0.9rem;">{esc(t("candidates.hint", lang))}</p>

<form id="cascade-form" hx-post="/api/start-cascade?lang={lang}" hx-target="#monitor" hx-swap="innerHTML">
  {hidden_state}
  {source_banner}
  {transport_banner}
  <input type="hidden" name="candidate_order" id="candidate_order" value="{esc(",".join(r.id for r in ranked))}">
  <div class="candidates" id="candidate-list">{cards}</div>
  {skipped_html}

  <div class="panel" style="margin-top:1.1rem;background:var(--ink);">
    <div class="panel-head" style="padding-bottom:0.5rem;">
      <h3>{esc(t("goal.title", lang))}</h3>
      <button type="button" class="mini" onclick="HC.previewGoal()">{esc(t("goal.show", lang))}</button>
    </div>
    <p class="help">{esc(t("goal.help", lang))}</p>
    <pre id="goal-preview" class="mono">{esc(t("goal.empty", lang))}</pre>
  </div>

  <div class="btn-row" style="margin-top:1.1rem;">
    <button type="submit" class="btn">{esc(t(start_key, lang))}</button>
  </div>
</form>

<div id="monitor"></div>
<script>HC.initCandidates({json.dumps([{"id": r.id, "name": r.name, "lat": r.lat, "lon": r.lon,
                                        "phone": mask_phone(r.phone),
                                        "cuisines": r.cuisines} for r in ranked])},
                          {lat}, {lon}, {radius_km});</script>
"""


# --------------------------------------------------------------------------
# Cascade monitor
# --------------------------------------------------------------------------

def render_cascade_monitor(
    lang: str,
    order_id: str,
    mode: Mode,
    max_budget_eur: Optional[float],
    criteria_line: str,
    concession_keys: List[str],
    live_mode: bool = False,
) -> str:
    """The waiting screen. Waiting is not idleness, it is not knowing."""
    if mode is Mode.RESERVATION:
        band_key, band_value = t("cascade.band.criteria", lang), criteria_line
    else:
        band_key = t("cascade.band.budget", lang)
        band_value = (
            f"{max_budget_eur:.2f} €" if max_budget_eur is not None
            else t("cascade.band.budget.none", lang)
        )

    concession_text = (
        ", ".join(t("table.concession." + k, lang) for k in concession_keys)
        if concession_keys else t("cascade.band.concessions.none", lang)
    )
    live_banner = (
        f'<div class="live-confirm"><strong>{esc(t("safety.live.warning", lang))}</strong></div>'
        if live_mode else ""
    )

    return f"""
<div class="panel" style="margin-top:1.2rem;" id="monitor-panel">
  {live_banner}
  <div class="band">
    <span class="k">{esc(band_key)}</span>
    <span class="v">{esc(band_value)}</span>
  </div>
  <div class="band">
    <span class="k">{esc(t("cascade.band.concessions", lang))}</span>
    <span class="v">{esc(concession_text)}</span>
  </div>

  <div class="panel-head" style="padding-bottom:0.5rem;">
    <h3>{esc(t("cascade.running", lang))}</h3>
    <button type="button" class="btn danger" id="cancel-btn"
            onclick="HC.cancel('{esc(order_id)}')">{esc(t("cascade.cancel", lang))}</button>
  </div>

  <p class="status" id="cascade-status">{esc(t("cascade.init", lang))}</p>

  <h4 class="eyebrow">{esc(t("cascade.activity", lang))}</h4>
  <div class="log" id="activity-log" aria-live="polite"></div>

  <div id="outcome"></div>
</div>
<script>HC.startStream("{esc(order_id)}");</script>
"""


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------

def render_result_sentence(
    lang: str,
    mode: Mode,
    restaurant: Restaurant,
    structured: Dict[str, Any],
    food_prompt: str,
    party_size: Optional[int],
    reservation_date: Optional[str],
    reservation_time: Optional[str],
) -> str:
    """The sentence a person could read out loud, in their language.

    The engine builds an English one for the CLI and the library. The screen
    needs the reader's language, so it is composed here instead of translating
    a finished English sentence back.
    """
    callback = mask_phone(structured.get("callback_number") or restaurant.phone)

    if mode is Mode.DELIVERY:
        return t(
            "result.sentence.delivery", lang,
            name=restaurant.name,
            eta=structured.get("eta_minutes", 0),
            items=food_prompt,
            price=f'{structured.get("total_price_eur", 0.0):.2f}',
            callback=callback,
        )

    if mode is Mode.PICKUP:
        return t(
            "result.sentence.pickup", lang,
            name=restaurant.name,
            prep=structured.get("prep_time_minutes", 0),
            price=f'{structured.get("total_price_eur", 0.0):.2f}',
            address=restaurant.address or restaurant.name,
            callback=callback,
        )

    seating = structured.get("seating_confirmed")
    return t(
        "result.sentence.reservation", lang,
        name=restaurant.name,
        party=party_size or "?",
        date=reservation_date or "?",
        time=reservation_time or "?",
        seating=t(f"result.sentence.seating.{seating}", lang) if seating else "",
        callback=callback,
    )


def render_result_card(
    lang: str,
    mode: Mode,
    restaurant: Restaurant,
    structured: Dict[str, Any],
    post_summary: str,
    raw_transcript_text: str,
    message: str,
    order_id: str,
    calls_made: int,
    concession_used: Optional[str] = None,
) -> str:
    """What came back, in the user's terms — and what it commits them to."""
    title = t(f"result.title.{mode.value}", lang)
    callback = structured.get("callback_number") or restaurant.phone

    facts: List[tuple] = []
    if mode in (Mode.DELIVERY, Mode.PICKUP):
        facts.append((t("result.price", lang), f'{structured.get("total_price_eur", 0.0):.2f} €'))
        if mode is Mode.DELIVERY:
            facts.append((t("result.eta", lang), f'{structured.get("eta_minutes", 0)} {t("result.minutes", lang)}'))
        else:
            facts.append((t("result.prep", lang), f'{structured.get("prep_time_minutes", 0)} {t("result.minutes", lang)}'))
            facts.append((t("result.pickup.at", lang), restaurant.address or restaurant.name))
    else:
        facts.append((t("result.when", lang), f'{structured.get("reservation_time_confirmed", "")}'.strip() or "—"))
        facts.append((t("result.party", lang), str(structured.get("party_size_confirmed", "") or "—")))
        seating = structured.get("seating_confirmed")
        if seating:
            facts.append((t("result.seating", lang), t(f"table.seating.{seating}", lang)))

    facts_html = "".join(
        f'<div class="fact"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>'
        for k, v in facts
    )

    concession_html = ""
    if concession_used:
        concession_html = f"""
  <div class="notice">
    <strong>{esc(t("result.concession", lang))}:</strong>
    {esc(t("table.concession." + concession_used, lang))}<br>
    <span class="small">{esc(t("result.concession.note", lang))}</span>
  </div>"""

    return f"""
<div class="result" style="margin-top:1.1rem;">
  <div class="panel-head" style="border:none;padding:0;">
    <h2>{esc(title)}</h2>
    <span class="small mono">{esc(calls_made_text(lang, calls_made))}</span>
  </div>

  <p class="result-sentence">{esc(message)}</p>
  <div class="facts">{facts_html}</div>
  {concession_html}

  <div class="callback">
    <span>
      <span class="eyebrow" style="display:block;">{esc(t("result.callback", lang))}</span>
      <span class="small muted">{esc(t("result.callback.note", lang))}</span>
    </span>
    <span class="num">{esc(mask_phone(callback))}</span>
  </div>

  <details>
    <summary>{esc(t("result.transcript", lang))}</summary>
    <p class="small muted" style="margin-top:0.6rem;">{esc(t("result.transcript.note", lang))}</p>
    <pre>{esc(raw_transcript_text or post_summary)}</pre>
  </details>

  <form hx-post="/api/save-result?lang={lang}" hx-target="#save-status" hx-swap="innerHTML">
    <input type="hidden" name="order_id" value="{esc(order_id)}">
    <input type="hidden" name="restaurant_id" value="{esc(restaurant.id)}">
    <div class="btn-row">
      <button type="submit" class="btn">{esc(t("result.save", lang))}</button>
      <span id="save-status" class="small mono"></span>
    </div>
  </form>
</div>"""


def calls_made_text(lang: str, calls_made: int) -> str:
    """One call is not '1 Anrufe'."""
    key = "result.calls.made.one" if calls_made == 1 else "result.calls.made"
    return t(key, lang, n=calls_made)


def render_failure(lang: str, calls_made: int) -> str:
    return f"""
<div class="notice warn" style="margin-top:1.1rem;">
  {esc(t("cascade.exhausted", lang))}
  <span class="small mono"> — {esc(calls_made_text(lang, calls_made))}</span>
</div>"""


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------

def render_history(lang: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        body = f'<p class="muted">{esc(t("history.empty", lang))}</p>'
    else:
        cells = ""
        for row in rows:
            price = row.get("total_price_eur")
            price_text = f"{price:.2f} €" if price else "—"
            cells += (
                "<tr>"
                f'<td class="num">{esc(row.get("created_at", ""))}</td>'
                f'<td>{esc(row.get("restaurant_name", ""))}</td>'
                f'<td class="num">{esc(row.get("mode", ""))}</td>'
                f'<td class="num">{esc(price_text)}</td>'
                f'<td class="num">{esc(row.get("masked_phone", ""))}</td>'
                "</tr>"
            )
        body = f"""
<table>
  <thead><tr>
    <th>{esc(t("result.when", lang))}</th><th>{esc(t("candidates.title", lang))}</th>
    <th>{esc(t("food.mode.title", lang))}</th><th>{esc(t("result.price", lang))}</th>
    <th>{esc(t("result.callback", lang))}</th>
  </tr></thead>
  <tbody>{cells}</tbody>
</table>
<p class="small muted" style="margin-top:0.8rem;">{esc(t("history.masked.note", lang))}</p>"""

    return f"""
<div class="panel">
  <div class="panel-head">
    <h2>{esc(t("history.title", lang))}</h2>
    <a class="small" href="/?lang={lang}">← {esc(t("nav.back", lang))}</a>
  </div>
  {body}
</div>"""
