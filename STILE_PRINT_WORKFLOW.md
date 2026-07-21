# STILE print workflow — teacher notes + model answers for every activity

A ready-to-run process for **Claude Cowork (desktop app) + the Claude in Chrome
extension**, driven by Opus. It walks the whole Stile subject, opens each
activity, prints it **with teacher notes and model answers included**, and saves
one PDF per activity into `Downloads/STILE`.

> **Why Cowork + Chrome, not Claude Code:** the job needs your *logged-in*
> Stile session in your real browser, Chrome's print dialog, and your local
> Downloads folder. The Chrome extension can see and click your actual tabs;
> Cowork supervises the loop. Claude Code (CLI/remote) has none of that access.

---

## 1. One-time setup (2 minutes, you do this)

1. Install/open **Claude Cowork** on your desktop and make sure the
   **Claude in Chrome** extension is installed and connected.
2. In Chrome, log in to Stile and confirm you can open
   <https://stileapp.com/institutions/86/subjects/706216> and see the subject
   outline.
3. Create the folder **`Downloads/STILE`**.
4. In Chrome settings → **Downloads**, turn ON **"Ask where to save each file
   before downloading"**. This is what lets Claude pick the STILE folder and
   set the filename at every Save-as-PDF step.
5. Do one manual test print of any activity so Chrome's print destination is
   already set to **"Save as PDF"** (Chrome remembers the last destination).

## 2. The run prompt — paste this into Cowork (model: Opus)

Copy everything in the block below into a new Cowork conversation with browser
access enabled:

```text
You have access to my Chrome browser via the Claude in Chrome extension. I am
already logged in to Stile.

TASK: Print every activity in my Stile subject, with teacher notes and model
answers included, saving one PDF per activity into my Downloads/STILE folder.
Run fully autonomously end to end; give me a single summary report at the end.

SUBJECT URL: https://stileapp.com/institutions/86/subjects/706216

STEP 1 — BUILD THE CHECKLIST
- Open the subject URL and expand every unit/topic in the outline.
- List every activity (e.g. "1.1 Living or non-living?", "1.2 ...") in order,
  across ALL units. Include every item — lessons, quizzes, tests, everything.
- Keep this list as your checklist and work through it top to bottom.
- Before starting each activity, check Downloads/STILE: if a PDF matching that
  activity's number already exists, mark it done and skip it (this makes the
  run resumable).

STEP 2 — FOR EACH ACTIVITY, IN ORDER
1. Click into the activity from the subject outline.
2. Find the Print option (usually in the "..." / overflow / settings menu of
   the activity view, sometimes a printer icon). Click Print.
3. In Stile's print options dialog, tick BOTH:
   - "Teacher notes" (include teacher notes)
   - "Model answers" (include model/sample answers)
   Leave other options at defaults. Both must be ON before continuing.
4. Confirm/Print so Chrome's print dialog opens. Destination must be
   "Save as PDF" — change it if it isn't. Then click Save.
5. In the save dialog: navigate to Downloads/STILE and set the filename to
   the activity's number and title, e.g.:
     1.1 Living or non-living.pdf
   (strip characters that are illegal in filenames: ? / \ : * " < > |).
6. Confirm the file saved, close the activity, return to the subject outline,
   and move to the next item on the checklist.

RULES
- One combined PDF per activity (teacher notes + model answers together), not
  separate files.
- Never skip the print-options step: a PDF without teacher notes and model
  answers is a failure — redo it.
- If an activity has no Print option (some interactive-only items don't),
  note it in the report and move on.
- If a print fails or a dialog behaves unexpectedly, retry once; if it fails
  again, log it as failed and continue — do not stall the run.
- Do not change anything in Stile: no editing activities, no assigning to
  classes, no student data. Read + print only.
- If Stile logs me out mid-run, pause and tell me instead of trying to log in.

STEP 3 — FINAL REPORT
When the checklist is exhausted, give me one summary:
- Total activities found vs PDFs saved
- Full list of saved filenames
- Any activities skipped (no print option) or failed, with the reason
```

## 3. What to expect

- **Time:** roughly 1–2 minutes per activity; a 50-activity subject is about
  an hour. Leave the Chrome window visible and unattended — clicking around in
  it yourself mid-run will confuse the automation.
- **Resumable:** if the run is interrupted, just paste the same prompt again.
  The "skip if the PDF already exists" rule means it picks up where it left off.
- **Verification:** afterwards, spot-check 2–3 PDFs — confirm teacher notes
  and model answers actually appear in the output, and that filenames sort in
  lesson order.

## 4. Known wrinkles

- **Stile's menu labels move around.** The print entry is sometimes under the
  activity's "..." menu, sometimes a toolbar icon; the checkbox wording may be
  "Include teacher notes" / "Include model answers" or similar. The prompt
  tells Opus to find the equivalent controls rather than exact labels.
- **Chrome's save dialog is a native OS dialog.** The extension can drive it,
  but the "Ask where to save" setting (setup step 4) must be on, otherwise
  Chrome silently drops files in Downloads root with default names.
- **Very long activities** can take 10–20 s to generate the print preview.
  That's normal — the prompt allows one retry before logging a failure.
