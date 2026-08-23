# Dataset Acquisition — IEEE-CIS Fraud Detection

**Status as of this audit: NOT PRESENT LOCALLY.** A filesystem search of the
project directory, `~/Downloads`, and the Kaggle CLI config location found
no IEEE-CIS files and no Kaggle CLI installed. Nothing was downloaded from
any source, official or otherwise, to satisfy this requirement — per Phase 0
instructions, the dataset is not to be invented or fetched from an
unofficial source. This document exists so a human can acquire it correctly.

## 1. Required dataset

**IEEE-CIS Fraud Detection** — selected in the design doc (Section 5–6) as
the base for the ML risk-scoring layer: real, labeled e-commerce transaction
data with card/device/email features, ~590K transactions.

## 2. Official / recognized acquisition route

Kaggle competition page:
`https://www.kaggle.com/c/ieee-fraud-detection`

This is a **competition dataset**, not a plain Kaggle Dataset. Access
requires:

1. A Kaggle account (free).
2. Accepting the competition rules on the competition page (even though the
   competition itself closed in 2019 — Kaggle still gates the data behind
   rule acceptance).
3. Either the Kaggle CLI (`kaggle competitions download -c
   ieee-fraud-detection`) or manual download from the "Data" tab of the
   competition page.

No other source (Google searches turning up re-hosted copies, torrents,
GitHub mirrors, etc.) should be used — those are exactly the "unofficial
source" this phase is instructed to avoid, and their provenance/integrity
can't be verified.

## 3. Expected files

From the competition's "Data" tab, the archive contains:

| File | Purpose |
|---|---|
| `train_transaction.csv` | Training transactions — includes `isFraud` label |
| `train_identity.csv` | Training identity/device metadata, joins to `train_transaction` on `TransactionID` (not every transaction has a matching identity row) |
| `test_transaction.csv` | Test transactions — no `isFraud` label (this is the Kaggle leaderboard test set) |
| `test_identity.csv` | Test identity/device metadata |
| `sample_submission.csv` | Kaggle submission format template — not needed for this project's purposes but included in the standard download |

## 4. Expected schema

This is **documented from the publicly known Kaggle competition schema**,
not verified against a local copy — treat every field below as "expected,
pending confirmation once the files are actually read." `docs/DATASET_AUDIT.md`
will replace this section's role once the files are present and inspected.

`train_transaction.csv` / `test_transaction.csv`:
- `TransactionID` — row key
- `isFraud` — binary target (train only)
- `TransactionDT` — a timedelta (seconds) from a fixed reference point, **not** a wall-clock timestamp — this is the temporal field the design doc's temporal split (Section 11, 24) depends on
- `TransactionAmt` — transaction amount
- `ProductCD` — product/category code
- `card1`–`card6` — anonymized payment-card attributes (card network, issuer bank category, card type, etc.)
- `addr1`, `addr2` — anonymized address fields
- `dist1`, `dist2` — anonymized distance features
- `P_emaildomain`, `R_emaildomain` — purchaser/recipient email domain
- `C1`–`C14` — anonymized count features
- `D1`–`D15` — anonymized time-delta features
- `M1`–`M9` — anonymized match flags (e.g., name-on-card vs. address match)
- `V1`–`V339` — anonymized Vesta-engineered features (majority of column count; largely opaque, high missingness in places)

`train_identity.csv` / `test_identity.csv`:
- `TransactionID` — join key back to the transaction table
- `id_01`–`id_38` — anonymized identity/device signals
- `DeviceType` — e.g. mobile/desktop
- `DeviceInfo` — free-text-ish device fingerprint string

## 5. Licensing / usage considerations

- Data is provided under Kaggle's competition rules, which for IEEE-CIS
  restrict use to non-commercial purposes consistent with the competition
  terms (research/educational use). Re-hosting or redistributing the raw
  files is against those terms — this project must not commit the raw
  files to any repository (`.gitignore` already excludes `data/raw/*`).
- The data is anonymized (per IEEE-CIS's own documentation) but originates
  from real Vesta Corporation e-commerce transactions — treat it as
  sensitive even though fields are hashed/obfuscated, and never merge it
  with any other identifying dataset.
- Because access requires accepting Kaggle's competition rules under a
  specific account, **a human must perform the download** — this is not
  something that should be automated with scraped or stored credentials.

## 6. Exact steps for manual acquisition

**Option A — Kaggle CLI (recommended if available):**

```bash
pip install kaggle
# Place your Kaggle API token (kaggle.json) at ~/.kaggle/kaggle.json
# (Account -> Settings -> API -> "Create New Token" on kaggle.com)
kaggle competitions download -c ieee-fraud-detection -p data/raw/
cd data/raw && unzip ieee-fraud-detection.zip && cd ../..
```

You must have already accepted the competition rules on
`kaggle.com/c/ieee-fraud-detection` (via the website) before the CLI
download will succeed — it returns a 403 otherwise.

**Option B — Manual browser download:**

1. Go to `https://www.kaggle.com/c/ieee-fraud-detection/data`.
2. Sign in, click "Join Competition" / accept rules if not already done.
3. Download the full data archive.
4. Unzip it.

## 7. Where files go

Place the five files directly in `data/raw/` (no subfolder), matching
`configs/paths.yaml`:

```
data/raw/train_transaction.csv
data/raw/train_identity.csv
data/raw/test_transaction.csv
data/raw/test_identity.csv
data/raw/sample_submission.csv
```

Once present, re-run `pytest tests/unit/test_infrastructure.py -v -s` —
`test_raw_dataset_detection` will report all five as present, and the next
step (schema audit → `docs/DATASET_AUDIT.md`) can proceed with real,
inspected numbers instead of documented expectations.
