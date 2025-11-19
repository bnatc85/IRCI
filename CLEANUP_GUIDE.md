# Disk Space Cleanup Guide

**Current Status:** 29GB/32GB used (97% full, 941MB free)

## 🎯 Priority 1: Free ~5.6GB Immediately (SAFEST)

### **Pip Cache: 5.6GB**
This is downloaded packages that can be re-downloaded if needed.

```bash
# Clear pip cache (FREE 5.6GB!)
pip cache purge
```

**Impact:** ✅ Safe, ✅ Instant 5.6GB freed, ✅ No risk

---

## 🎯 Priority 2: Remove Unnecessary GPU Libraries (~4GB)

You're running on **CPU**, but have **CUDA/GPU libraries** installed (4GB wasted).

### **What's Using Space:**
```
717MB - libcublasLt.so.12         (GPU matrix operations)
523MB - libcudnn_engines.so.9     (GPU neural networks)
457MB - libtorch_cpu.so           (CPU - KEEP)
432MB - libcusparseLt.so.0        (GPU sparse matrices)
410MB - libnccl.so.2              (GPU multi-GPU)
383MB - libtriton.so              (GPU compiler)
371MB - libcusparse.so.12         (GPU sparse)
```

### **Option A: Reinstall PyTorch CPU-Only**
```bash
# Uninstall current torch
pip uninstall -y torch torchvision torchaudio

# Install CPU-only version (saves ~4GB)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### **Option B: Remove Specific CUDA Packages**
```bash
pip uninstall -y nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-nccl-cu12 \
  nvidia-cufft-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 \
  nvidia-cusolver-cu12 nvidia-curand-cu12 nvidia-nvshmem-cu12
```

**Impact:** ⚠️ Moderate risk, ✅ ~4GB freed, ⚠️ May break torch temporarily

---

## 🎯 Priority 3: Clean Old Output Files (~100KB)

Small impact but good housekeeping.

```bash
# Remove old quarterly output files (from Sep)
rm -f outputs/coverage_2022-*.csv
rm -f outputs/trust_2022-*.csv
rm -f outputs/trust_2023-*.csv
rm -f outputs/trust_2024-*.csv
rm -f outputs/valuation_2022-*.csv
rm -f outputs/valuation_2023-*.csv
rm -f outputs/valuation_2024-*.csv
rm -f outputs/coverage_2023-*.csv
rm -f outputs/coverage_2024-*.csv
rm -f outputs/liquidity_2024q4.csv
rm -f outputs/liquidity_2025q1.csv
rm -f outputs/valuation_2024q*.csv
rm -f outputs/coverage_q2.csv
rm -f outputs/valuation_q2.csv
rm -f outputs/irci_composite_q2.csv
rm -f outputs/*_canon.csv
rm -f outputs/*_norm.csv
```

**Impact:** ✅ Safe, ✅ ~100KB freed, ✅ No risk

---

## 🎯 Priority 4: Clean Other Caches

```bash
# Clean system cache
rm -rf ~/.cache/matplotlib
rm -rf ~/.cache/huggingface
rm -rf ~/.local/share/virtualenv

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
```

**Impact:** ✅ Safe, ✅ ~500MB freed, ✅ No risk

---

## 📋 Recommended Cleanup Sequence

```bash
# Step 1: Clear pip cache (SAFEST - 5.6GB)
pip cache purge

# Step 2: Check space
df -h /workspaces

# Step 3: Clean old outputs
rm -f outputs/coverage_202[2-4]-*.csv
rm -f outputs/trust_202[2-4]-*.csv
rm -f outputs/valuation_202[2-4]-*.csv
rm -f outputs/*_canon.csv
rm -f outputs/*_norm.csv

# Step 4: Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Step 5: Clean other caches
rm -rf ~/.cache/matplotlib
rm -rf ~/.cache/huggingface

# Step 6: Check final space
df -h /workspaces
```

---

## ⚠️ Optional: Nuclear Option (If Still Needed)

If you still need more space after above:

```bash
# Reinstall PyTorch CPU-only (saves 4GB but requires reinstall)
pip uninstall -y torch
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Remove transformers cache (models will re-download when needed)
rm -rf ~/.cache/huggingface/hub
```

---

## 🔍 After Cleanup: Verify

```bash
# Check disk usage
df -h /workspaces

# Check .venv size
du -sh .venv

# Check pip cache (should be 0)
du -sh $(pip cache dir)
```

---

## ✅ Expected Results

| Action | Space Freed | Risk | Time |
|--------|-------------|------|------|
| Pip cache purge | **5.6GB** | None | 10s |
| Old output files | 100KB | None | 5s |
| Python cache | 50-200MB | None | 30s |
| Other caches | 200-500MB | None | 30s |
| **CPU-only PyTorch** | **4GB** | Medium | 5min |
| **TOTAL** | **~10GB** | Low-Med | 6min |

After cleanup, you should have **~11GB free** (65% usage instead of 97%).

---

## 🚫 DO NOT DELETE

- `.venv/` (entire directory - will break environment)
- `data/` (your news and price data)
- `irci/` (source code)
- `outputs/irci_composite_2025q3.csv` (latest results)
- `outputs/trust.csv` (latest results)
- `outputs/valuation_2025q3.csv` (latest results)
- `outputs/coverage_2025q3.csv` (latest results)
- `outputs/liquidity.csv` (latest results)

---

**Recommended: Start with Step 1 (pip cache purge) - that alone frees 5.6GB!**
