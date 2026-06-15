# Django RAG ChatBot

**Live Demo:** [https://my-own-rag-chatbot.onrender.com](https://my-own-rag-chatbot.onrender.com)

A Retrieval-Augmented Generation (RAG) web application built with Django, LangChain, and Groq. This application allows users to upload PDF documents and ask questions based on the content of those documents using a large language model.

## Features

- **User Authentication:** Secure signup, login, and session-based interactions.
- **Document Ingestion:** Upload multiple PDF files per session.
- **Vector Search:** Automatically extracts text, splits it into chunks, and stores embeddings using **HuggingFace (`BAAI/bge-small-en-v1.5`)** and **ChromaDB**.
- **LLM Chat:** Asks questions against the uploaded context using **LangChain** and **Groq (`llama-3.3-70b-versatile`)**.
- **Production Ready:** Configured with `gunicorn`, `whitenoise`, and `python-dotenv` for secure and scalable deployment.

## Prerequisites

- Python 3.9+
- A [Groq API Key](https://console.groq.com/) for the LLM.
- A [Hugging Face Access Token](https://huggingface.co/settings/tokens) for generating cloud embeddings.

## Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd "Rag ChatBot Using Djnago Frmawork"
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root of your project and add the following:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   HF_TOKEN=your_huggingface_api_token_here
   SECRET_KEY=your_secure_django_secret_key
   DEBUG=True
   ALLOWED_HOSTS=*
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   Open your browser and navigate to `http://127.0.0.1:8000`.

## Production Deployment (Render)

This project is fully configured for deployment on **Render** as a "Web Service". 

> **⚠️ Important Data Persistence Note for Render:** 
> By default, Render's free tier provides an *ephemeral* file system. This means that every time your app restarts, your `db.sqlite3` database, ChromaDB vector stores, and uploaded PDFs will be deleted. For a production app where you want to keep your users and data permanently, you must add a **Persistent Disk** to your Render Web Service.

### Render Setup Instructions

1. **Connect your GitHub:** Create a new "Web Service" on Render and link your GitHub repository.
2. **Environment Configuration:** In the Render dashboard, add the following Environment Variables:
   - `GROQ_API_KEY`: Your Groq API key
   - `HF_TOKEN`: Your Hugging Face API token (Required for cloud embeddings to prevent Out of Memory errors on the free tier)
   - `SECRET_KEY`: A long, randomly generated secure string
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `*` (or your specific render domain like `.onrender.com`)

3. **Build Command:** Tell Render how to install dependencies, run migrations, and prepare static files.
   ```bash
   # Installs packages, runs database migrations, and collects static files
   pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
   ```

4. **Start Command:** Tell Render how to boot the production server.
   ```bash
   # Starts the application using the production-ready gunicorn server
   gunicorn rag_chatbot.wsgi:application
   ```

## Architecture

- **Web Framework:** Django
- **Orchestration:** LangChain
- **Embeddings:** HuggingFace (`BAAI/bge-small-en-v1.5`)
- **Vector Database:** ChromaDB (Persisted locally per session)
- **LLM Provider:** Groq
