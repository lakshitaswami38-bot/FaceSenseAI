## FaceSense AI – Emotion Detection & Suggestion System

A mini full-stack Flask project that detects emotion via:
- **Manual mood selection**
- **Camera (OpenCV + DeepFace)**
- **Text input (keyword-based)**

Then it shows a **rule-based suggestion system** (message + activity + entertainment links).

## Project Structure

```text
FaceSenseAI/
  app.py
  requirements.txt
  README.md
  templates/
    base.html
    index.html
    select.html
    camera.html
    text.html
    result.html
  static/
    css/
      styles.css
    js/
      app.js
```

## Setup (Windows)

Open PowerShell in the `FaceSenseAI` folder:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser.

## Notes (Camera Mode)

- Camera mode uses **OpenCV on the server**, so the webcam is accessed on the same machine where Flask is running.
- If camera fails:
  - close other apps using the webcam (Zoom/Teams/Camera app),
  - try again,
  - ensure your Python can access the webcam (permissions).

