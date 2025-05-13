# Finstage-Market-Data

## Introduction

**Finstage-Market-Data** is a Python-based microservice that provides financial statement data for publicly traded companies.  
If a requested company's data is missing, the service automatically submits a registration request to Kafka, where a separate process can later fetch and store the data asynchronously.

This service complements the Finstage platform by ensuring financial data availability while maintaining responsiveness and scalability.

---

## Purpose

- Serve income statement, balance sheet, and cash flow data for listed companies.
- If data is missing, trigger an asynchronous registration flow without blocking the main service.
- Build a loosely coupled, reliable data-fetching pipeline with clear separation between read and write responsibilities.
- Ensure the system is ready for large-scale, event-driven data ingestion in the future.

---

## Currently Available Features

- Retrieve financial statements by company symbol.
- Automatically send a registration request if the data is missing.
- Kafka-based registration request pipeline decouples request handling from data fetching.
- REST API support for querying available financial data.

---

## Why Kafka?

The system uses Kafka to submit data registration requests when financial statements are missing.  
This design addresses two critical issues in real-time backend systems:

### 1. Prevent blocking the main thread

Attempting to fetch financial data immediately from external sources would block the API thread, resulting in slow responses and unpredictable user experience.  
Instead, the system quickly responds to the client and delegates the registration request to Kafka.

### 2. Handle the limitations of asynchronous processing

Typical asynchronous approaches make it hard to:

- Track whether the request succeeded or failed
- Retry failed operations safely
- Prevent duplicated or race-condition-prone behavior

By using Kafka:

- Registration requests are logged and persisted
- Consumers can handle failures gracefully with retry logic or dead-letter queues
- Requests are processed in a distributed and traceable way

Kafka enables this service to maintain responsiveness, improve reliability, and support future scaling needs.

---

## Getting Started

### Prerequisites

- Python 3.12
- Kafka (locally or remotely available)
- MySQL 8.x
- Chrome WebDriver (if applicable to future crawling use)

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/your-username/finstage-market-data.git
cd finstage-market-data

# Set up a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8081
```
