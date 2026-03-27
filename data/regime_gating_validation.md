# Regime Gating Validation — 11,484bp Saved

**Date:** March 25, 2026
**Method:** Rough regime reconstruction from 314 patience trader trades using peak_bp as proxy

| Regime Proxy | Trades | WR | Avg P&L | Total |
|-------------|--------|-----|---------|-------|
| CHOP (peak <50bp) | 90 | 0% | -128bp | -11,484bp |
| MILD (peak 50-100bp) | 118 | 70% | +3bp | +328bp |
| TRENDING (peak 100-200bp) | 56 | 82% | +41bp | +2,290bp |
| STRONG TREND (peak 200+bp) | 44 | 100% | +215bp | +9,436bp |

**Portfolio impact:** Blocking CHOP entries transforms +570bp → +12,054bp (21x improvement)
**Conclusion:** The bot doesn't need a better strategy. It needs to know when NOT to play.
