# Blind hand labels (prereg A3)

`stage1_blind.csv` was written by the auditor (Opus 5.5) from `scripts/label_sheet.py` sheets:
question and options only, key hidden, no protocol, no model outcome seen. Columns: `pick` (my
answer), `m` (options a trained bench scientist would call a standard fix for the stated
problem), `class` (G: m = 1; D: m >= 2, choosing needs a protocol detail; N: m = 0), `conf` (1-3).
Committed before the key was revealed.

Caveat: before labelling, while checking the data format, the keys of 6 items were printed
(`250c9945`, `a548710c`, `cc814af4`, `8920c7b7`, `36cae278`, `81eb406f`). Their labels are not
blind to the key; analyses are repeated without them.

`labels.csv` (stage 2) adds the key's letter on the sheet, whether my pick is the key, and
`standard_key` = (class G and pick is the key).
