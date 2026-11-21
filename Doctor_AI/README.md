

## Pro features (v2)

- **AI Chatbot**: remembers the whole conversation, accepts attached files (PDF, images, text).
- **Image Diagnosis**: camera or upload, possible conditions plus urgency level.
- **Report Analysis**: lab reports explained, abnormal values flagged, questions for the doctor.
- **History & Profile**: chats saved in `data/doctor_ai.db` (local only), patient profile used in every answer.

### Run

```bash
pip install -r requirements.txt
copy .env.example .env      # then paste your NEW keys into .env
streamlit run app.py
```

Image and scanned-PDF analysis needs `GEMINI_API_KEY` (or `OPENAI_API_KEY`).
Text chat uses Groq first, then Gemini, then OpenAI.
Educational project only. Not medical advice.
