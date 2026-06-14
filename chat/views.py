"""
Views for the RAG Chat application.
"""

import json
import os
import traceback

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from . import rag_service


def _ensure_session(request):
    """Make sure the request has a session key. Return it."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_groq_key(request):
    """Get the Groq API key — session override or settings default."""
    return request.session.get("groq_api_key") or getattr(settings, "GROQ_API_KEY", "")


# ---------- Page views ----------

@login_required
def upload_view(request):
    """Landing page — upload PDFs and optionally enter a Groq API key."""
    session_id = _ensure_session(request)
    default_key = getattr(settings, "GROQ_API_KEY", "")

    if request.method == "POST":
        groq_key = request.POST.get("groq_api_key", "").strip() or default_key
        files = request.FILES.getlist("pdf_files")

        if not groq_key:
            return render(request, "chat/upload.html", {
                "error": "Please enter your Groq API key.",
                "has_default_key": bool(default_key),
            })

        if not files:
            return render(request, "chat/upload.html", {
                "error": "Please upload at least one PDF file.",
                "has_default_key": bool(default_key),
            })

        # Validate all files are PDFs
        for f in files:
            if not f.name.lower().endswith(".pdf"):
                return render(request, "chat/upload.html", {
                    "error": f"'{f.name}' is not a PDF file. Only PDFs are accepted.",
                    "has_default_key": bool(default_key),
                })

        # Save files to disk
        upload_dir = os.path.join(settings.MEDIA_ROOT, "pdfs", session_id)
        os.makedirs(upload_dir, exist_ok=True)

        saved_paths = []
        file_names = []
        for f in files:
            safe_name = f.name.replace(" ", "_")
            path = os.path.join(upload_dir, safe_name)
            with open(path, "wb") as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            saved_paths.append(path)
            file_names.append(f.name)

        # Process PDFs into ChromaDB
        try:
            num_chunks = rag_service.process_pdfs(saved_paths, session_id)
        except Exception as e:
            traceback.print_exc()
            return render(request, "chat/upload.html", {
                "error": f"Error processing PDFs: {e}",
                "has_default_key": bool(default_key),
            })

        # Store metadata in session
        request.session["groq_api_key"] = groq_key
        request.session["pdf_files"] = file_names
        request.session["num_chunks"] = num_chunks
        request.session["documents_ready"] = True
        request.session["chat_history"] = []

        return redirect("chat_page")

    return render(request, "chat/upload.html", {
        "has_default_key": bool(default_key),
    })


@login_required
def chat_view(request):
    """Chat page — only accessible after documents are loaded."""
    _ensure_session(request)

    if not request.session.get("documents_ready"):
        return redirect("upload_page")

    return render(request, "chat/chat.html", {
        "pdf_files": request.session.get("pdf_files", []),
        "num_chunks": request.session.get("num_chunks", 0),
        "chat_history": request.session.get("chat_history", []),
    })


@login_required
def reset_view(request):
    """Clear session data and redirect to upload page."""
    session_id = _ensure_session(request)
    rag_service.clear_session_data(session_id)

    for key in ["groq_api_key", "pdf_files", "num_chunks", "documents_ready", "chat_history"]:
        request.session.pop(key, None)

    return redirect("upload_page")


# ---------- API endpoints ----------

@login_required
@require_POST
def chat_api(request):
    """
    AJAX endpoint for chat.
    Expects JSON body: { "question": "..." }
    Returns JSON: { "answer": "..." } or { "error": "..." }
    """
    session_id = _ensure_session(request)

    if not request.session.get("documents_ready"):
        return JsonResponse({"error": "No documents uploaded. Please upload PDFs first."}, status=400)

    groq_key = _get_groq_key(request)
    if not groq_key:
        return JsonResponse({"error": "Groq API key not found. Please re-upload your documents."}, status=400)

    try:
        body = json.loads(request.body)
        question = body.get("question", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)

    try:
        answer = rag_service.ask_question(question, session_id, groq_key)
    except Exception as e:
        traceback.print_exc()
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            error_msg = "Invalid Groq API key. Please start a new session with a valid key."
        return JsonResponse({"error": error_msg}, status=500)

    # Persist chat history in session
    history = request.session.get("chat_history", [])
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    request.session["chat_history"] = history

    return JsonResponse({"answer": answer})
