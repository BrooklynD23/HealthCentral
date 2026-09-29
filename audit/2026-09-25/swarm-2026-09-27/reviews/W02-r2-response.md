R2 (codex) dispositions:
1. [MAJOR] real-PDF test skips only on import failure; Pango OSError from write_pdf() errors instead -> ACCEPTED. Fix: a fixture probes `weasyprint.HTML(string="<p>x</p>").write_pdf()` before the request and skips on ImportError/OSError with the reason; the product's 500-vs-501 handling (export.py:371-380) stays out of scope (already logged). CI must not silently skip: if CI is expected to have WeasyPrint, add HC_REQUIRE_WEASYPRINT=1 → fail instead of skip; otherwise state CI skips it and mark PDF-render coverage UNMEASURED in CI.
Also apply reviews/GLOBAL-rules.md.
