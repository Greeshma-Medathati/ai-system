import gradio as gr
import json
import os
import shutil
import subprocess
import requests
import sys

# using namespace std; // Keeping it simple and honest for the review!

def get_python_command():
    """Forces the system to use the virtual environment's Python if it exists!"""
    venv_python = os.path.join("venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def handle_upload(uploaded_files):
    """Saves user-uploaded PDFs into the workspace."""
    if not uploaded_files:
        return "⚠️ No files selected."
    
    save_dir = os.path.join("data", "raw_pdfs")
    
    # Clear old PDFs so we only analyze the new ones!
    if os.path.exists(save_dir):
        shutil.rmtree(save_dir)
    os.makedirs(save_dir, exist_ok=True)
    
    for f in uploaded_files:
        dest = os.path.join(save_dir, os.path.basename(f.name))
        shutil.copy(f.name, dest)
        
    return f"✅ Successfully added {len(uploaded_files)} PDF(s) to the workspace."

def run_pipeline_realtime(topic, mode):
    """
    100% Honest Pipeline using a Generator.
    Streams live terminal output directly to the UI.
    """
    if not topic.strip():
        yield "⚠️ Please enter a research topic.", gr.update(visible=False)
        return
    
    status_message = ""
    save_dir = os.path.join("data", "raw_pdfs")
    python_cmd = get_python_command()

    # --- PHASE 1: SEARCH & DOWNLOAD ---
    if mode == "Semantic Scholar Search":
        status_message += f"🔍 **Searching Semantic Scholar for '{topic}'...**\n"
        yield status_message, gr.update(visible=False)
        
        try:
            try:
                from search import search_papers
            except ImportError:
                from modules.search import search_papers
                
            papers = search_papers(topic, limit=3)
            paper_titles = [p.get("title", "Unknown Title") for p in papers]
            titles_bulleted = "\n".join([f"- {t}" for t in paper_titles])
            
            status_message += f"✅ **Found Top Papers:**\n{titles_bulleted}\n\n"
            status_message += "⬇️ **Downloading Open Access PDFs...**\n"
            yield status_message, gr.update(visible=False)
            
            if os.path.exists(save_dir):
                shutil.rmtree(save_dir)
            os.makedirs(save_dir, exist_ok=True)
            
            downloaded_count = 0
            for i, paper in enumerate(papers):
                pdf_info = paper.get("openAccessPdf")
                if pdf_info and isinstance(pdf_info, dict) and pdf_info.get("url"):
                    pdf_url = pdf_info.get("url")
                    try:
                        r = requests.get(pdf_url, timeout=15)
                        if r.status_code == 200:
                            pdf_path = os.path.join(save_dir, f"paper_search_{i+1}.pdf")
                            with open(pdf_path, "wb") as f:
                                f.write(r.content)
                            downloaded_count += 1
                            status_message += f"   - Downloaded PDF {downloaded_count}\n"
                            yield status_message, gr.update(visible=False)
                    except Exception:
                        pass
            
            if downloaded_count == 0:
                status_message += "\n⚠️ **Warning:** Could not download Open Access PDFs. Please try Manual Upload.\n"
                yield status_message, gr.update(visible=False)
                return
                
            status_message += f"\n✅ Successfully downloaded {downloaded_count} PDF(s).\n\n"
            yield status_message, gr.update(visible=False)

        except Exception as e:
            status_message += f"\n⚠️ Search Error: {e}\n"
            yield status_message, gr.update(visible=False)
            return

    elif mode == "Manual Upload":
        status_message += "📂 **Using Manually Uploaded PDFs...**\n\n"
        yield status_message, gr.update(visible=False)

    # --- PHASE 2: REAL-TIME ANALYSIS LOGGING ---
    status_message += "⚙️ **Running FULL Analysis...**\n"
    status_message += "*(Live Terminal Output below: Watch the AI process the papers!)*\n```text\n"
    yield status_message + "```", gr.update(visible=False)

    try:
        # Run milestone2.py and capture output line-by-line as it happens!
        process = subprocess.Popen(
            [python_cmd, "milestone2.py"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1 # Line buffered
        )
        
        for line in iter(process.stdout.readline, ''):
            status_message += line
            yield status_message + "```", gr.update(visible=False)
            
        process.stdout.close()
        process.wait()
        
        status_message += "```\n" # Close the markdown code block
        
        if process.returncode != 0:
            status_message += "\n❌ **Analysis Crashed.** Review the live logs above."
            yield status_message, gr.update(visible=False)
            return
            
    except Exception as e:
        status_message += f"