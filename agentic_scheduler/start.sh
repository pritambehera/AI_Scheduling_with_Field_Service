#!/usr/bin/env bash

# Start the Agentic Scheduler suite: Backend API & Frontend Streamlit

echo "Starting FastAPI Orchestrator on port 8080..."
uvicorn api:app --host 0.0.0.0 --port 8080 &
FASTAPI_PID=$!

echo "Starting Java Backend App on port 8081..."
(cd ../scheduling && ./mvnw spring-boot:run) &
JAVA_PID=$!

echo "Starting Streamlit UI over port 8501..."
streamlit run app.py

# When Streamlit exits, cleanup the FastAPI orchestrator and Java backend
kill $FASTAPI_PID $JAVA_PID
