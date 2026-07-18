# TODO - Render deployment fixes

- [x] Update Python version pins for Render compatibility
- [x] Replace requirements.txt with Render-safe pinned versions (avoid scipy source builds)
- [ ] Remove/adjust any unnecessary dependencies that trigger compilation
- [x] Ensure Procfile exists and uses correct gunicorn command
- [ ] Sanity-check ML artifact loading (model.pkl, vectorizer.pkl)
- [ ] Run local pip install and minimal import test
- [ ] Show modified files and provide Render redeploy steps


