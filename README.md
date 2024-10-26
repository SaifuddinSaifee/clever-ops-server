# MongoDB LLM Query Generator

> This is a project submission at MumbaiHacks 2024, by Team Technoids (Saifuddin Saifee, Pratham Bhagat)

## What
A Flask API service that converts natural language to MongoDB queries using LLM. Give it questions like "show all pro users" or "count number of trials activated last month" and it will generate and execute the appropriate MongoDB query.

This app serves as backend for [CleverOps Frontend CLient](https://github.com/SaifuddinSaifee/clever-ops-client).

## Setup
1. Install dependencies:

```bash
pip install flask flask-cors pymongo ollama
```

2. Ensure you have:
- MongoDB running locally or accessible via URI
- Ollama installed with llama3.2 model

3. Configure MongoDB connection in app.py (default is `mongodb://localhost:27017/`)

## Run
```bash
python mongoapi.py
```

The API will be available at `http://localhost:5000` with two endpoints:
- POST `/api/query` - Convert natural language to MongoDB query
- POST `/api/health` - Check service status
