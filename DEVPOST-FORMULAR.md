# DevPost submission form — HungryCall

> **Copy-and-paste sheet.** Every heading below is a field of the DevPost submission
> form. The text under it is finished and goes into that field unchanged.
>
> **Nothing here has been submitted.** Submitting, publishing the repository and
> uploading the video are the user's steps.
>
> **No Markdown tables anywhere below.** The DevPost editor does not render them, so
> everything comparative is written as a list on purpose.
>
> **Every placeholder is marked with an `ATTRAPPE` comment.** Search this file for
> `ATTRAPPE` before submitting and replace each one. The list is repeated at the end.

---

## Project name

```
HungryCall
```

---

## Elevator pitch

*(DevPost limit: 200 characters. The text below is 137.)*

```
Stop dialling one by one: HungryCall runs a budget-capped cascade of calls across local businesses and stops the second one of them fits.
```

---

## Project story

*(DevPost calls this "About the project". The seven headings below are DevPost's own
suggested structure — keep them as headings in the editor.)*

### Inspiration

Outside the big cities there is no delivery app. The restaurants down the road are on no
platform, so finding out who delivers to your street, what it actually costs at the door,
and how long it takes means calling them one after another — and starting over each time
the answer is no.

That is not a hard problem. It is a *tedious* one, which is worse: people stop asking and
order from the same single place forever. For anyone who dreads phone calls, or has a
speech or hearing impairment, the tedium is a wall.

The interesting part is that "call candidates until one fits" is not about food at all. It
is the shape of an urgent dentist appointment, a brake repair before the weekend, a spare
part in stock, a respite care slot. We wanted the pattern, and used food to demonstrate it.

### What it does

- Takes one brief — what you want, where you are, what you will pay — and turns it into a
  sequential cascade of calls to ranked local candidates.
- Before dialling anything it geocodes the address, drops businesses that are closed at
  that hour, and orders the rest by craving and distance.
- Enforces a hard doorstep budget. If the total at your door exceeds the cap, the agent
  declines politely and moves to the next candidate. It cannot spend authority it was not
  given.
- Refuses a price it would have to guess. "About 30 euros, depends on the driver" is
  recorded as `price_known: false` and rejected — a guessed price is not a price.
- Holds concessions back. What you would settle for (a longer ETA for a lower price, an
  indoor table when the terrace is full) is only played when the primary path has failed,
  and the result states which step was used.
- Stops the entire cascade the second a candidate meets every condition. The remaining
  candidates are never called.
- Keeps a timestamped transcript of what was agreed, as evidence of the spoken contract,
  next to a masked callback number.
- Runs all of it with no account, no network and no telephone, against bundled fixtures.

### The one thing to try first

One command, about thirty seconds, no account and no API key:

- `pip install -e .`
- `hungrycall demo`

It runs the whole cascade: candidate 1 rejected for exceeding the budget, candidate 2
rejected for quoting a vague price, candidate 3 accepted and ordered, the remaining
candidates never dialled — and it prints the transcript as proof of what was agreed.

Note: `python -m hungrycall` does not work; the package has no `__main__` entry point.
Install first, then use the `hungrycall` command.

### Why not just use the CALL-E app?

Use it. For a single call the CALL-E chat is faster than anything we could build, and
HungryCall does not try to replace it.

The difference is the search, not the call:

- The app calls one number you already chose. This ranks a list and works down it.
- The app leaves the judgement to you after each call. This is given the criteria in
  advance and applies them during the conversation.
- The app has no spending limit, because a human is reading along. This has a cap the
  agent cannot exceed.
- The app returns prose. This returns a schema-validated result, so "does it fit" is a
  decision rather than an impression.
- The app stops when you stop. This stops itself the moment the goal is met, which is also
  what keeps it cheap.

### How we built it

- Python 3.11+, FastAPI, HTMX, SQLite and Leaflet. No bundler, no build step, no CDN.
- The cascade engine is the whole product; the three modes (delivery, table, pickup) are
  different criteria on the same engine, not three code paths.
- Agent authority is modelled in four tiers, and this is the part meant to be reused:
  musts that cannot be traded, hard boundaries that force a polite refusal, tiered
  concessions that stay hidden until the primary attempt fails, and wishes that only
  reorder the candidate list. The pattern is written up separately in `MUSTER.md`.
- Schema-validated results come from the REST API, because that is the only path that has
  them.
- The dry run is a real fixture framework, not a stub: user input is interpolated into
  transcripts, activity logs and summaries, so the offline run exercises the same parsing
  a live call would.
- Safety is code, not documentation: E.164 validation, phone masking in every output,
  deterministic idempotency keys, and a content guard that rejects medical, legal,
  financial and emergency briefs before a call is ever planned.

### Challenges we ran into

Everything below was measured against the real service in a real call, and several of
these contradict the documentation:

- `status` is useless as a progress indicator. It stayed on `PREPARING` for an entire
  conversation and only moved to `COMPLETED` after the call had ended. Live progress had
  to be read from `activity` instead.
- Speech recognition streams and then corrects itself. The same line arrives twice, a
  rough version and a correction moments later, so intermediate drafts have to be
  de-duplicated or the live log becomes unreadable.
- About 40 seconds of every call is dialling before a word is spoken, independent of how
  long anyone talks. Billing is per call; time is not.
- Result schemas are REST-only. `plan_call` over MCP/CLI has no `result_schema`, and a
  call started over MCP is not retrievable over REST at all — separate ID spaces, shared
  billing.
- Extending agent authority from time to money turned out to need a second rule nobody
  writes down: the agent must also refuse *unclear* prices. A cap alone is not enough if
  the agent is willing to estimate.

### Accomplishments that we're proud of

- 85 tests, all green, all in the dry run, none needing an account or a network.
- The concession mechanism is tested in both directions: an agent that spends authority it
  was not granted has its result rejected, and the same call succeeds once the concession
  is granted — with the result naming which step it used.
- A 30-second demo that shows the whole argument (budget rejection, vague-quote rejection,
  success, early exit, transcript proof) without any access.
- A web interface that is honest where you are working: real calls are locked, and it says
  so on screen instead of offering a "go live" switch that does nothing.
- Both languages complete, enforced by a test that fails the build if a key is missing in
  either one or a placeholder is lost in translation.

### What we learned

- Monetary limits are a workable form of agent authority — but only paired with a rule
  that forbids acting on an estimate. Otherwise the cap is advisory.
- Design the result schema before the prose. What the agent must fill in is what it must
  find out during the call.
- Streaming speech recognition needs de-duplication before it is shown to anyone.
- The cheapest optimisation was the early exit. Stopping at the first fit is both the
  correct behaviour and the one that saves the most money.

### What's next for HungryCall

- Packaging the cascade engine as a standalone library, so the medical, mechanic and
  spare-part cases are configuration rather than forks.
- A field test with real businesses, with disclosure. It has not happened yet.
- Multilingual negotiation prompts for providers outside German-speaking regions.
- Verifying the live OpenStreetMap candidate search, which exists in code but is never
  entered by the dry run.

---

## Built with

*(DevPost expects a list of tags. Enter them one at a time.)*

```
python
fastapi
htmx
sqlite
leaflet
openstreetmap
call-e
rest-api
pytest
```

---

## Try it out links

<!-- ATTRAPPE: the repository is private. Replace with the real URL once the user
     publishes it, or delete the line if the repository stays private. -->

```
https://www.youtube.de/coming-soon
```

Intended content once available:

- Repository: the public GitHub URL of this repository.
- Pull request to `CALLE-AI/awesome-phone-call-agents`: the PR URL (see `PR-VORSCHAU.md`
  for the drafted entry, title and description).

---

## Video demo link

<!-- ATTRAPPE: nothing has been uploaded. The finished video file exists at
     C:\_Local_DEV\_calle-videos\hungrycall\renders\ — what is missing is a public
     link, not the video. Replace with the real YouTube URL after upload. -->

```
https://www.youtube.de/coming-soon
```

Requirements to check at upload time: under three minutes, publicly visible, English
narration or English subtitles, and it must show the project functioning.

---

## Repository link

<!-- ATTRAPPE: the repository is private; the URL only exists after the user publishes
     it. Replace with the real GitHub URL. -->

```
https://www.youtube.de/coming-soon
```

---

## Pull request URL

*(Hackathon-specific required field: the PR to `CALLE-AI/awesome-phone-call-agents`.)*

<!-- ATTRAPPE: no pull request has been opened. Opening it is a user step. -->

```
https://www.youtube.de/coming-soon
```

---

## CALL-E account e-mail

<!-- ATTRAPPE: the user supplies this at submission time. It is deliberately never
     written into the repository. -->

```
<the user enters this directly in the form>
```

---

## Pre-existing project?

```
No. This repository was created during the hackathon submission period and every commit
in it is dated after 2026-07-23.
```

---

## Image gallery / thumbnail

Three thumbnail drafts, 1280x720, at
`C:\_Local_DEV\_calle-videos\hungrycall\thumbnails\`:

- `hungrycall-thumb-a.png` — the cascade with the early exit. Recommended: it shows what
  the project does in one glance.
- `hungrycall-thumb-b.png` — the vague-quote refusal and the hard cap.
- `hungrycall-thumb-c.png` — the pattern beyond food.

The repository banner (1200x300) is `banner.png` in the repository root.

---

## Checklist of every ATTRAPPE in this file

Replace all of these before submitting:

1. **Try it out links** — placeholder `https://www.youtube.de/coming-soon`; needs the
   public repository URL and the pull-request URL.
2. **Video demo link** — placeholder `https://www.youtube.de/coming-soon`; needs the real
   YouTube URL after upload.
3. **Repository link** — placeholder `https://www.youtube.de/coming-soon`; needs the
   public GitHub URL after the repository is made public.
4. **Pull request URL** — placeholder `https://www.youtube.de/coming-soon`; needs the real
   PR URL after it is opened.
5. **CALL-E account e-mail** — the user types it into the form directly; it is not stored
   here.

---

## Notes for whoever fills the form in

- Paste the sections as plain text. There is no Markdown table anywhere in this file
  because the DevPost editor will not render one.
- Do not add a number that is not in this file. The test count (85) was measured by test
  run on 2026-08-02; `EVIDENCE.md` is the record of what else was measured. Anything not
  in one of those two places is invention.
- The five items in the checklist above are the only things blocking the form, and every
  one of them is an action that belongs to the user.
