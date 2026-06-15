"""
Views for the RAG Chat application.
This file contains the main logic for rendering pages and handling API requests.
"""

import json
import os
import traceback
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from . import rag_service


def _ensure_session(request):
    """
    Helper function: Make sure the request has a session key.
    Django sessions are used to store data specific to each user (like chat history
    and uploaded file lists). This creates a session if one doesn't exist and returns its key.
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_groq_key(request):
    """
    Helper function: Get the Groq API key.
    It first checks if the user provided one in their session. If not, it falls back
    to the default API key specified in the Django settings (from the .env file).
    """
    return request.session.get("groq_api_key") or getattr(settings, "GROQ_API_KEY", "")


# ---------- Page views ----------

# The @login_required decorator ensures only authenticated users can access this view.
@login_required
def upload_view(request):
    """
    Landing page — upload PDFs and optionally enter a Groq API key.
    This view handles the main interface where users upload their documents.
    """
    session_id = _ensure_session(request)
    default_key = getattr(settings, "GROQ_API_KEY", "")

    # If it's a POST request, the user is submitting the form (uploading files).
    if request.method == "POST":
        # Get the API key from the form, or use the default if left blank.
        groq_key = request.POST.get("groq_api_key", "").strip() or default_key
        # Get the list of uploaded files from the request.
        files = request.FILES.getlist("pdf_files")

        # Validation: check if an API key is available.
        if not groq_key:
            return render(request, "chat/upload.html", {
                "error": "Please enter your Groq API key.",
                "has_default_key": bool(default_key),
            })

        # Validation: check if at least one file was uploaded.
        if not files:
            return render(request, "chat/upload.html", {
                "error": "Please upload at least one PDF file.",
                "has_default_key": bool(default_key),
            })

        # Validate all uploaded files to ensure they are PDFs.
        for f in files:
            if not f.name.lower().endswith(".pdf"):
                return render(request, "chat/upload.html", {
                    "error": f"'{f.name}' is not a PDF file. Only PDFs are accepted.",
                    "has_default_key": bool(default_key),
                })

        # Define the directory where these PDFs will be saved temporarily.
        # We use the session_id so each user's files are kept separate.
        upload_dir = os.path.join(settings.MEDIA_ROOT, "pdfs", session_id)
        os.makedirs(upload_dir, exist_ok=True)

        saved_paths = []
        file_names = []
        
        # Save each file to disk
        for f in files:
            safe_name = f.name.replace(" ", "_")
            path = os.path.join(upload_dir, safe_name)
            # Write the file chunk by chunk to avoid loading huge files entirely into memory.
            with open(path, "wb") as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            saved_paths.append(path)
            file_names.append(f.name)

        # Process the PDFs (extract text, chunk it, embed it, and store in ChromaDB)
        # We use a unique directory ID for Chroma to prevent SQLite caching errors (1032)
        chroma_dir_name = f"{session_id}_{uuid.uuid4().hex[:8]}"
        try:
            num_chunks = rag_service.process_pdfs(saved_paths, chroma_dir_name)
        except Exception as e:
            traceback.print_exc() # Print the full error stack to the console for debugging
            return render(request, "chat/upload.html", {
                "error": f"Error processing PDFs: {e}",
                "has_default_key": bool(default_key),
            })

        # If successful, store the metadata in the user's session.
        request.session["chroma_dir"] = chroma_dir_name
        request.session["groq_api_key"] = groq_key
        request.session["pdf_files"] = file_names
        request.session["num_chunks"] = num_chunks
        request.session["documents_ready"] = True
        request.session["chat_history"] = []

        # Redirect the user to the chat interface.
        return redirect("chat_page")

    # If it's a GET request, just render the upload page.
    return render(request, "chat/upload.html", {
        "has_default_key": bool(default_key),
    })


@login_required
def chat_view(request):
    """
    Chat page — only accessible after documents are loaded.
    Displays the chat interface where the user can ask questions about their PDFs.
    """
    _ensure_session(request)

    # Prevent access to the chat page if no documents have been uploaded yet.
    if not request.session.get("documents_ready"):
        return redirect("upload_page")

    # Pass the user's session data (files, chunks, history) to the template.
    return render(request, "chat/chat.html", {
        "pdf_files": request.session.get("pdf_files", []),
        "num_chunks": request.session.get("num_chunks", 0),
        "chat_history": request.session.get("chat_history", []),
    })


@login_required
def reset_view(request):
    """
    Clear session data and redirect to upload page.
    This allows a user to "start over" with new documents.
    """
    session_id = _ensure_session(request)
    
    # Delete the ChromaDB vector store and uploaded PDFs from disk for this session.
    chroma_dir = request.session.get("chroma_dir")
    rag_service.clear_session_data(session_id, chroma_dir)

    # Remove all session variables related to the chat context.
    for key in ["groq_api_key", "pdf_files", "num_chunks", "documents_ready", "chat_history", "chroma_dir"]:
        request.session.pop(key, None)

    return redirect("upload_page")


# ---------- API endpoints ----------

# This view is called via AJAX from the frontend JavaScript.
@login_required
@require_POST
def chat_api(request):
    """
    AJAX endpoint for chat.
    Expects JSON body: { "question": "..." }
    Returns JSON: { "answer": "..." } or { "error": "..." }
    """
    session_id = _ensure_session(request)

    # Ensure documents have been processed before attempting to answer questions.
    if not request.session.get("documents_ready"):
        return JsonResponse({"error": "No documents uploaded. Please upload PDFs first."}, status=400)

    # Ensure we have an API key to communicate with Groq.
    groq_key = _get_groq_key(request)
    if not groq_key:
        return JsonResponse({"error": "Groq API key not found. Please re-upload your documents."}, status=400)

    # Parse the incoming JSON request.
    try:
        body = json.loads(request.body)
        question = body.get("question", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)

    # Pass the question to our RAG service to query the LLM.
    chroma_dir = request.session.get("chroma_dir")
    try:
        answer = rag_service.ask_question(question, chroma_dir, groq_key)
    except Exception as e:
        traceback.print_exc()
        error_msg = str(e)
        # Give a friendlier error if the issue is with the API key.
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            error_msg = "Invalid Groq API key. Please start a new session with a valid key."
        return JsonResponse({"error": error_msg}, status=500)

    # Persist the conversation history in the session so it survives page reloads.
    history = request.session.get("chat_history", [])
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    request.session["chat_history"] = history

    # Return the answer back to the frontend.
    return JsonResponse({"answer": answer})
