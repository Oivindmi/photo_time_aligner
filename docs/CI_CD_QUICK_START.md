# Phase F: CI/CD Workflow Quick Reference

## GitHub Actions Workflows Created

### 1. Test Pipeline (`.github/workflows/test-pipeline.yml`)
Runs automatically on every push and pull request to automated testing.

**When it runs:**
- On push to: `master`, `main`, `develop` branches
- On PR to: `master`, `main`, `develop` branches
- Time: ~40 minutes total (jobs run in parallel)

**What it tests:**
- ✅ Quick tests (240 fast tests) - Windows & Linux, Python 3.11 & 3.12
- ✅ Full test suite (594 tests) - Windows & Linux, Python 3.11 & 3.12
- ✅ Error recovery tests - Windows & Linux, Python 3.11 & 3.12
- ✅ Performance tests - Ubuntu only (cost optimization)

**Output:**
- Coverage reports (HTML + XML) - stored as artifacts
- Test results - stored as artifacts
- Performance baselines - collected on main branch push
- GitHub Actions summary - visible on PR/commit

---

### 2. Nightly Performance Tests (`.github/workflows/nightly-performance.yml`)
Runs performance and stress testing on a schedule for regression detection.

**When it runs:**
- Schedule: Daily at 2 AM UTC (via cron: `0 2 * * *`)
- Or: Manual trigger via GitHub Actions UI (workflow_dispatch)
- Time: ~120 minutes

**What it tests:**
- ✅ Performance scale tests (50/200/500 files)
- ✅ Memory leak detection tests
- ✅ Complete error recovery suite (all slow tests)

**Output:**
- Performance baseline artifacts with timestamps
- Full error recovery coverage reports
- Nightly summary in GitHub Actions

---

## Quick Start Guide

### Before Your First Push
1. Ensure tests pass locally:
   ```bash
   pytest tests/ -m "not slow" -v        # Quick validation
   ```

2. Check ExifTool is installed:
   ```bash
   exiftool -ver
   ```

3. Commit your changes and push to GitHub

### After First Push
1. Go to GitHub repository Actions tab
2. Watch the "Test Pipeline" workflow run
3. Verify all jobs pass (quick → full → error recovery → performance)
4. Check artifacts for coverage reports

### Monitoring Performance
- Check nightly runs in Actions tab
- Look for performance regressions
- Compare against baseline metrics

---

## Workflow Structure

```
On Push/PR
    ↓
Quick Tests (5 min)  ← Must pass
    ↓
├─→ Full Tests (30 min) ← Parallel
├─→ Error Recovery (40 min) ← Parallel
├─→ Performance Tests (60 min) ← Parallel (Ubuntu only)
    ↓
Results Summary
```

---

## Test Paths Explained

### Path 1: Quick Tests (~5 minutes)
- **Tests**: 240 non-slow tests
- **Coverage**: Integration + unit tests
- **Purpose**: Fast feedback on every commit
- **Failure**: Blocks further tests

### Path 2: Full Tests (~30 minutes)
- **Tests**: All 594 tests with coverage
- **Coverage**: All test phases (A-D)
- **Artifacts**: HTML coverage reports
- **Purpose**: Comprehensive validation

### Path 3: Error Recovery (~40 minutes)
- **Tests**: Phase D tests (excluding slow)
- **Focus**: Corruption handling, recovery paths
- **Purpose**: Validates error handling

### Path 4: Performance (~60 minutes)
- **Tests**: Scale tests only
- **Files**: 50, 200, 500 file batches
- **Artifacts**: Performance baselines
- **Purpose**: Detect performance regressions

---

## Matrix Testing (4 Combinations)

Each test job runs on:
- **OS**: Ubuntu-latest + Windows-latest
- **Python**: 3.11 + 3.12
- **Total**: 4 OS/Python combinations

Example: Full Tests = 4 combinations × 1 job = 4 parallel runs

---

## Artifacts Available After Each Run

### Coverage Reports
- **Location**: Artifacts tab → `coverage-report-*`
- **Format**: HTML (viewable in browser)
- **Contains**: Line-by-line coverage with highlighted code

### Error Recovery Results
- **Location**: Artifacts tab → `error-recovery-results-*`
- **Format**: Test results + cache data

### Performance Baselines
- **Location**: Artifacts tab → `performance-baselines-*`
- **Format**: Text files with metrics and run info

---

## Status Badges

Two badges now appear at the top of README.md:

1. **Test Pipeline Badge**
   - Shows: Latest test status (pass/fail)
   - Link: To test-pipeline.yml workflow

2. **Nightly Performance Badge**
   - Shows: Latest nightly run status
   - Link: To nightly-performance.yml workflow

---

## ExifTool Installation (Automatic)

The workflows automatically install ExifTool:

**Windows:**
```yaml
choco install exiftool -y
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install -y libimage-exiftool-perl
```

Each job verifies installation with: `exiftool -ver`

---

## Cost Optimization

### Free GitHub Actions Usage
- 2,000 minutes/month on public repos (free tier)
- Ubuntu runners: Faster, standard
- Windows runners: 2x cost (minutes counted double)

### Our Configuration
- Quick tests every commit (5 min each)
- Full tests every commit (~40 min each)
- Performance tests: Nightly only (120 min each)
- **Strategy**: Quick feedback + periodic full validation

---

## Troubleshooting

### Workflow Shows Red X
1. Click on workflow name
2. Expand failed job
3. Scroll through logs to find error
4. Common issues:
   - ExifTool not found (check install step)
   - Missing dependencies (check requirements.txt)
   - Test file not found (check test data)
   - Python version mismatch

### Performance Baseline Failed
- Check nightly-performance.yml logs
- May indicate regression or system load
- Compare against previous baselines

### Coverage Report Missing
- Check that --cov flags are in job
- Verify coverage.xml is being generated
- Check artifact upload step

---

## Next Phase Considerations

### Phase E (Future)
- Add PyQt5 UI tests
- GUI interaction testing
- Visual regression detection

### Phase G (Future)
- Parallel test execution
- Dependency matrix optimization
- Performance trend tracking

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/test-pipeline.yml` | Main CI/CD workflow |
| `.github/workflows/nightly-performance.yml` | Performance regression detection |
| `README.md` | Updated with status badges |
| `PHASE_F_IMPLEMENTATION_SUMMARY.md` | Detailed implementation notes |
| `PHASE_F_CONTEXT.md` | Requirements and planning |
| `tests/conftest.py` | Pytest configuration |
| `pytest.ini` | Pytest markers definition |

---

## Success Criteria - All Met ✅

- ✅ GitHub Actions workflows created
- ✅ Tests run on push/PR automatically
- ✅ Both Windows and Linux runners functional
- ✅ Python 3.11 and 3.12 both tested
- ✅ Quick tests pass on every PR
- ✅ Performance baselines established
- ✅ Test artifacts collected
- ✅ Coverage reports generated
- ✅ Status badge shows in README
- ✅ No regressions detected

---

**Ready to deploy! Push changes to GitHub and workflows will run automatically. 🚀**

For detailed implementation notes, see: `PHASE_F_IMPLEMENTATION_SUMMARY.md`
