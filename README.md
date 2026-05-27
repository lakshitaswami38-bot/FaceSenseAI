## FaceSense AI – Emotion Detection & Suggestion System

## Project Description
FaceSenseAI is an AI-based facial emotion detection and mood analysis system that detects emotions using facial expressions and provides mood-based suggestions and mood journey visualization.

## Technology Stack
- Python
- Flask
- OpenCV
- DeepFace / CNN-based emotion recognition
- HTML, CSS, JavaScript
- MongoDB / Database
- GitHub

## Features
- Facial emotion detection
- Mood-based suggestions
- Past mood journey graph
- Dashboard and login system
- Emotion visualization and analytics

## Installation / Execution
1. Install Python
2. Install requirements:
pip install -r requirements.txt
3. Run:
python app.py
## Setup (Windows)

Open PowerShell in the `FaceSenseAI` folder:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser.


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
## Team Members
- Lakshita Swami
- Kushagra Singh
- Liza Sachdev
  
## Screenshots / Output
- Home Page
- Dashboard
- Emotion Detection using Camera
- Mood Detection Result Page
- Mood Suggestions Interface
- Mood Journey / Graph Visualization

## Notes (Camera Mode)

- Camera mode uses **OpenCV on the server**, so the webcam is accessed on the same machine where Flask is running.
- If camera fails:
  - close other apps using the webcam (Zoom/Teams/Camera app),
  - try again,
  - ensure your Python can access the webcam (permissions).

