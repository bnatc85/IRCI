#!/usr/bin/env bash
set -euo pipefail

# --- locate repo root from this script's path ---
# scripts/comm/run_comm_pipeline.sh -> repo root is two directories up
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"

# --- config (override via env) ---
SYMBOL="${SYMBOL:-T}"             # seed symbol in Communications Services
K="${K:-12}"                      # number of peers (in addition to seed)
OUTDIR="${OUTDIR:-${REPO_ROOT}/out/comm}"   # output folder under repo
WEIGHTS="${WEIGHTS:-0.15,0.15,0.35,0.35}"   # C,T,L,V (sum to 1)

# --- expected scripts (actual locations in your repo) ---
PEERS_PY="${REPO_ROOT}/scripts/comm/peers_comm.py"
FETCH_EV_PY="${REPO_ROOT}/scripts/comm/fetch_ev_ev_ebitda.py"
DUMMY_PARTS_PY="${REPO_ROOT}/scripts/comm/make_comm_parts_dummy.py"
MERGE_PARTS_PY="${REPO_ROOT}/scripts/comm/build_with_dials_from_parts.py"
BUILD_PANEL_PY="${REPO_ROOT}/scripts/comm/build_comm_panel.py"

# --- outputs ---
PEERS_CSV="${OUTDIR}/peers_${SYMBOL}.csv"
EV_CSV="${OUTDIR}/ev_comm.csv"
VAL_CSV="${OUTDIR}/valuation_comm.csv"
COV_CSV="${OUTDIR}/coverage_comm.csv"
TRU_CSV="${OUTDIR}/trust_comm.csv"
LIQ_CSV="${OUTDIR}/liquidity_comm.csv"
DIALS_MERGED="${OUTDIR}/irci_comm_quarterly.csv"
PANEL_WITH_DIALS="${OUTDIR}/irci_comm_quarterly_with_dials.csv"

# --- sanity checks ---
if [[ -z "${FMP_API_KEY:-}" ]]; then
  echo "[ERROR] FMP_API_KEY is not set. Run: export FMP_API_KEY=YOUR_KEY" >&2
  exit 1
fi

for f in "$PEERS_PY" "$FETCH_EV_PY" "$DUMMY_PARTS_PY" "$MERGE_PARTS_PY" "$BUILD_PANEL_PY"; do
  [[ -f "$f" ]] || { echo "[ERROR] Missing script: $f" >&2; exit 1; }
done

mkdir -p "${OUTDIR}"

echo "== Step 1: Build peers for ${SYMBOL} (k=${K}) =="
python "$PEERS_PY" \
  --symbol "${SYMBOL}" \
  --k "${K}" \
  --out "${PEERS_CSV}"
    # Clean out preferreds/notes so downstream APIs work
    python "$REPO_ROOT/scripts/comm/filter_peers.py" --in "${PEERS_CSV}" --out "${PEERS_CSV}"


echo "== Step 2: Fetch EV and EV/EBITDA =="
echo "== Step 2: Fetch EV and EV/EBITDA (Alpha Vantage fallback) =="
python "$REPO_ROOT/scripts/comm/fetch_ev_with_alpha_vantage.py" \
  --peers "${PEERS_CSV}" \
  --out-ev "${EV_CSV}" \
  --out-val "${VAL_CSV}" \
  --quarters 4


# If you already have real coverage/trust/liquidity CSVs in OUTDIR, this will just skip.
if [[ ! -f "${COV_CSV}" || ! -f "${TRU_CSV}" || ! -f "${LIQ_CSV}" ]]; then
  echo "== Step 3: Creating TEMP dummy coverage/trust/liquidity (replace with your real exports later) =="
  python "$DUMMY_PARTS_PY" \
    --peers "${PEERS_CSV}" \
    --outdir "${OUTDIR}"
else
  echo "== Step 3: Using existing ${COV_CSV}, ${TRU_CSV}, ${LIQ_CSV} =="
fi

echo "== Step 4: Merge dials + EV into quarterly panel =="
python "$MERGE_PARTS_PY" \
  --coverage  "${COV_CSV}" \
  --trust     "${TRU_CSV}" \
  --liquidity "${LIQ_CSV}" \
  --valuation "${VAL_CSV}" \
  --ev        "${EV_CSV}" \
  --peers     "${PEERS_CSV}" \
  --out       "${DIALS_MERGED}"

echo "== Step 5: Compute composite panel =="
python "$BUILD_PANEL_PY" \
  --in-dials "${DIALS_MERGED}" \
  --peers    "${PEERS_CSV}" \
  --out      "${PANEL_WITH_DIALS}" \
  --w        "${WEIGHTS}"

echo
echo "[OK] Wrote:"
echo "  Peers:            ${PEERS_CSV}"
echo "  EV:               ${EV_CSV}"
echo "  Valuation metric: ${VAL_CSV}"
echo "  Coverage:         ${COV_CSV}"
echo "  Trust:            ${TRU_CSV}"
echo "  Liquidity:        ${LIQ_CSV}"
echo "  Merged dials:     ${DIALS_MERGED}"
echo "  Final panel:      ${PANEL_WITH_DIALS}"
