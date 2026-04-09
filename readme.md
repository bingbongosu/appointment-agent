# Appointment Agent

An AI-powered scheduling assistant that:

- Reads emails via Gmail API
- Extracts scheduling intent using structured LLM output
- Checks Google Calendar availability
- Proposes meeting times
- Generates reply drafts

## Tech Stack
- Python
- Pydantic
- OpenAI API
- Google Gmail + Calendar APIs

## Setup
1. Add credentials.json from Google Cloud
2. Create a .env file with your API key
3. Run main.py