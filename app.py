import os
import json
import uuid
import base64
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, make_response, url_for, send_from_directory
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from PIL import Image, ImageDraw, ImageFont
import traceback
import mimetypes
import time
from gtts import gTTS
import re

load_dotenv()
app = Flask(__name__)

# Define PROOF_DIR as an absolute path for maximum robustness and consistency
PROOF_DIR = os.path.abspath(os.path.join(app.root_path, 'doc', 'proofs'))

# Define AUDIO_OUTPUT_DIR in the project root
AUDIO_OUTPUT_DIR = os.path.abspath(os.path.join(app.root_path, 'audio_files'))

# Define SAVED_EXCUSES_FILE in the project root
SAVED_EXCUSES_FILE = os.path.abspath(os.path.join(app.root_path, 'saved_excuses.json'))

# Ensure directories exist at startup
os.makedirs(PROOF_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

print(f"Flask App Root Path: {app.root_path}")
print(f"Absolute PROOF_DIR: {PROOF_DIR}")
print(f"Absolute AUDIO_OUTPUT_DIR: {AUDIO_OUTPUT_DIR}")
print(f"Absolute SAVED_EXCUSES_FILE: {SAVED_EXCUSES_FILE}")

# Route to serve files from the 'doc/proofs' directory
@app.route('/proofs/<path:filename>')
def serve_proof(filename):
    if not os.path.isdir(PROOF_DIR):
        print(f"Error: Proof directory not found at {PROOF_DIR}")
        return "Internal Server Error: Proofs directory missing.", 500
    
    full_filepath = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to serve file: {filename} from full path: {full_filepath}")
    
    if not os.path.exists(full_filepath):
        print(f"Error: Requested file not found on disk at {full_filepath}")
        return "Not Found", 404

    try:
        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype is None:
            if filename.endswith('.pdf'):
                mimetype = 'application/pdf'
            elif filename.endswith('.png'):
                mimetype = 'image/png'
            elif filename.endswith('.json'):
                mimetype = 'application/json'
            else:
                mimetype = 'application/octet-stream'

        with open(full_filepath, 'rb') as f:
            file_content = f.read()

        response = make_response(file_content)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"

        print(f"Successfully prepared response headers for {filename}. Mimetype: {mimetype}, Disposition: {response.headers['Content-Disposition']}")
        return response
    except Exception as e:
        print(f"Error serving file {filename} from {PROOF_DIR}: {e}")
        traceback.print_exc()
        return "Internal Server Error: Failed to serve file.", 500


#SERVING AUDIO FILES FROM THE NEW DIRECTORY
@app.route('/audio_files/<path:filename>')
def serve_audio_file(filename):
    return send_from_directory(AUDIO_OUTPUT_DIR, filename)

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
# Using the specific Mixtral model URL
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
VALID_SCENARIOS = ["late for work", "missed class", "forgot anniversary", "missed deadline", "didn't text back"]

insights_db = {
    "frequent_scenarios": {},
    "daily_counts": {},
    "excuse_feedback": {}
}

excuses_db = {}


def get_excuse_from_huggingface(prompt):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 100, "temperature": 0.7, "top_p": 0.9}
    }
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        response = session.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"Raw Hugging Face API response: {result}")

        raw_text = ""
        if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
            raw_text = result[0]["generated_text"]
        elif isinstance(result, dict) and "generated_text" in result:
            raw_text = result["generated_text"]
        else:
            print("Warning: Hugging Face API response did not contain 'generated_text' in expected format.")
            return None
        
        if "[/INST]" in raw_text:
            excuse = raw_text.split("[/INST]", 1)[1].strip()
        else:
            excuse = raw_text.strip()
        
        excuse = excuse.replace('"', '').strip()
        
        undesired_prefixes = [
            "here's an excuse:",
            "translation:",
            "english:",
            "spanish:",
            "french:",
            "german:",
            "italian:",
            "portuguese:",
            "hindi:",
            "bengali:",
            "in english:",
            "here's the excuse:",
            "the excuse is:",
            "your excuse:",
            "excuse:"
        ]
        
    
        prefix_pattern = re.compile(r'^(?:' + '|'.join(re.escape(p) for p in undesired_prefixes) + r')\s*(?::\s*)?', re.IGNORECASE)

        match = prefix_pattern.match(excuse)
        if match:
            excuse = excuse[match.end():].strip()
        if re.search(r'\b(Translation|English|Spanish|French|German|Italian|Portuguese|Hindi|Bengali)\s*:', excuse, re.IGNORECASE):
            parts = re.split(r'\b(Translation|English|Spanish|French|German|Italian|Portuguese|Hindi|Bengali)\s*:', excuse, 1, re.IGNORECASE)
            if len(parts) > 1:
                excuse = parts[0].strip()

        print(f"Hugging Face API returned cleaned excuse: {excuse}")
        return excuse if excuse else "Error generating excuse, please try again later."
    except requests.exceptions.RequestException as e:
        print(f"Error calling Hugging Face API: {e}")
        if e.response is not None:
            print(f"HTTP Status: {e.response.status_code}")
            print(f"Response Content: {e.response.text}")
        traceback.print_exc()
        return None

def generate_doctor_doc(excuse_id, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"doctor_doc_{uuid.uuid4().hex}.pdf"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate doctor note at: {full_path}")
    
    prompt = f"""
    [INST] Generate a concise, realistic medical detail for a doctor's note supporting the scenario '{scenario}'.
    Keep it under 50 words, professional, and believable (e.g., minor illness or issue). Do not include the excuse itself or any translations. [/INST]
    """
    medical_detail = get_excuse_from_huggingface(prompt)
    medical_detail = medical_detail.replace('"', '').strip() if medical_detail else "Unknown medical issue preventing attendance."
    
    # Further clean medical detail, specifically for doctor's note
    if medical_detail.lower().startswith("here's a medical detail:"):
        medical_detail = medical_detail[len("here's a medical detail:"):].strip()
    if re.search(r'\b(Translation|English)\s*:', medical_detail, re.IGNORECASE):
        medical_detail = re.split(r'\b(Translation|English)\s*:', medical_detail, 1, re.IGNORECASE)[0].strip()

    if len(medical_detail.split()) > 40:
        medical_detail = " ".join(medical_detail.split()[:40]) + "..."

    try:
        c = canvas.Canvas(full_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(letter[0]/2, 750, "Doctor's Note")
        
        c.setFont("Helvetica", 10)
        c.drawRightString(letter[0]-50, 780, f"Date: {datetime.now().strftime('%B %d, %Y')}")

        c.setFont("Helvetica", 12)
        c.drawString(50, 700, "To Whom It May Concern,")
        c.drawString(50, 680, f"This note confirms that a patient was seen on {datetime.now().strftime('%B %d, %Y')}.")
        
        c.setFont("Helvetica-Oblique", 12)
        c.drawString(50, 650, "Diagnosis/Reason:")
        c.setFont("Helvetica", 12)
        
        lines = simpleSplit(medical_detail, "Helvetica", 12, letter[0] - 100)
        y_pos = 630
        for line in lines:
            c.drawString(50, y_pos, line)
            y_pos -= 15
        
        y_pos -= 30
        c.drawString(50, y_pos, "Patient is advised to rest and is excused from activities.")
        y_pos -= 15
        c.drawString(50, y_pos, f"Expected return: { (datetime.now() + timedelta(days=2)).strftime('%B %d, %Y') }")
        
        c.setFont("Helvetica-Bold", 12)
        y_pos -= 40
        c.drawString(50, y_pos, "Sincerely,")
        y_pos -= 20
        c.drawString(50, y_pos, "Dr. A.I. Goodtrust, MD")
        y_pos -= 15
        c.drawString(50, y_pos, "Neural Networks Clinic")
        y_pos -= 15
        c.drawString(50, y_pos, "101 Digital Highway, AILand")

        c.save()
        print(f"Finished writing doctor note to: {full_path}")
        
        if os.path.exists(full_path):
            print(f"Confirmation: PDF file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: PDF file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
            
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating PDF for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

def get_font_path():
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    print("Warning: Arial.ttf or DejaVuSans.ttf not found. Using Pillow's default font.")
    return None

ARIAL_FONT_PATH = get_font_path()

def wrap_text(draw, text, font, max_width):
    lines = []
    if not text:
        return [""]
    words = text.split(' ')
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
        except TypeError:
            text_width = len(test_line) * (font.size * 0.6) if font else len(test_line) * 10
            print(f"Warning: textbbox failed with current font, using approximate width for '{test_line}'.")

        if text_width <= max_width:
            current_line.append(word)
        else:
            if not current_line:
                lines.append(word)
                current_line = []
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def generate_chat_screenshot(excuse_id, excuse, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"chat_screenshot_{uuid.uuid4().hex}.png"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate chat screenshot at: {full_path}")
    
    img_width = 600
    img_height = 400 
    img = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(img)

    font_size = 18
    font = ImageFont.load_default()
    if ARIAL_FONT_PATH:
        try:
            font = ImageFont.truetype(ARIAL_FONT_PATH, font_size)
        except IOError as e:
            print(f"Could not load specified font '{ARIAL_FONT_PATH}': {e}. Using default font.")
            traceback.print_exc()
            font = ImageFont.load_default()
        except Exception as e:
            print(f"Unexpected error loading font '{ARIAL_FONT_PATH}': {e}. Using default font.")
            traceback.print_exc()
            font = ImageFont.load_default()
            
    margin = 30
    current_y = 30
    line_height = font_size + 5

    friend_text_template = {
        "late for work": "Hey, where are you? You're late for work!",
        "missed class": "Did you miss class today? We had a pop quiz!",
        "forgot anniversary": "Happy Anniversary! ... wait, did you forget?",
        "missed deadline": "Just checking in, did you get that report done? Deadline was today.",
        "didn't text back": "Hey, I texted you earlier. Everything okay? Why didn't you text back?"
    }
    friend_initial_message = friend_text_template.get(scenario, "Hello?")
    
    bubble_color_friend = (229, 229, 229)
    bubble_color_you = (220, 248, 198)

    wrapped_lines = wrap_text(draw, friend_initial_message, font, img_width * 0.7 - (2 * 15))
    bubble_height = (len(wrapped_lines) * line_height) + (2 * 10)
    
    bubble_width = max((draw.textbbox((0,0), line, font=font)[2] - draw.textbbox((0,0), line, font=font)[0] for line in wrapped_lines), default=0) + (2 * 15)
    bubble_width = min(bubble_width, img_width * 0.7)

    draw.rounded_rectangle((margin, current_y, margin + bubble_width, current_y + bubble_height), radius=15, fill=bubble_color_friend)
    text_y = current_y + 10
    for line in wrapped_lines:
        draw.text((margin + 15, text_y), line, fill="black", font=font)
        text_y += line_height
    current_y += bubble_height + 20

    wrapped_lines = wrap_text(draw, excuse, font, img_width * 0.7 - (2 * 15))
    bubble_height = (len(wrapped_lines) * line_height) + (2 * 10)

    bubble_width = max((draw.textbbox((0,0), line, font=font)[2] - draw.textbbox((0,0), line, font=font)[0] for line in wrapped_lines), default=0) + (2 * 15)
    bubble_width = min(bubble_width, img_width * 0.7)

    you_x_start = img_width - margin - bubble_width
    draw.rounded_rectangle((you_x_start, current_y, img_width - margin, current_y + bubble_height), radius=15, fill=bubble_color_you)
    text_y = current_y + 10
    for line in wrapped_lines:
        draw.text((you_x_start + 15, text_y), line, fill="black", font=font)
        text_y += line_height
    current_y += bubble_height + 20

    friend_closing_message = "Oh, okay! Hope everything's alright. Take care!"
    wrapped_lines = wrap_text(draw, friend_closing_message, font, img_width * 0.7 - (2 * 15))
    bubble_height = (len(wrapped_lines) * line_height) + (2 * 10)

    bubble_width = max((draw.textbbox((0,0), line, font=font)[2] - draw.textbbox((0,0), line, font=font)[0] for line in wrapped_lines), default=0) + (2 * 15)
    bubble_width = min(bubble_width, img_width * 0.7)

    draw.rounded_rectangle((margin, current_y, margin + bubble_width, current_y + bubble_height), radius=15, fill=bubble_color_friend)
    text_y = current_y + 10
    for line in wrapped_lines:
        draw.text((margin + 15, text_y), line, fill="black", font=font)
        text_y += line_height
    current_y += bubble_height + 20

    if current_y > img_height:
        new_img_height = current_y + margin
        new_img = Image.new("RGB", (img_width, new_img_height), color="white")
        new_img.paste(img, (0, 0))
        img = new_img
        draw = ImageDraw.Draw(img)

    try:
        img.save(full_path)
        print(f"Successfully generated chat screenshot: {full_path}")
        if os.path.exists(full_path):
            print(f"Confirmation: PNG file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: PNG file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating PNG for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

def generate_location_log(excuse_id, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"location_log_{uuid.uuid4().hex}.json"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate location log at: {full_path}")
    
    base_lat = 22.5726
    base_lon = 88.3639

    log = {
        "timestamp": datetime.now().isoformat(),
        "latitude": base_lat + (random.random() - 0.5) * 0.05,
        "longitude": base_lon + (random.random() - 0.5) * 0.05,
        "accuracy_meters": 10 + random.randint(0, 50),
        "event_type": "Unexpected Location Activity",
        "notes": f"Device detected unusual movement patterns related to '{scenario.replace('_', ' ').title()}'."
    }
    try:
        with open(full_path, "w") as f:
            json.dump(log, f, indent=2)
        print(f"Successfully generated location log: {full_path}")
        if os.path.exists(full_path):
            print(f"Confirmation: JSON file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: JSON file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating JSON for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

def _load_saved_excuses():
    if not os.path.exists(SAVED_EXCUSES_FILE):
        return {}
    try:
        with open(SAVED_EXCUSES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {SAVED_EXCUSES_FILE} is empty or malformed. Starting with empty saved excuses.")
        return {}
    except Exception as e:
        print(f"Error loading saved excuses from {SAVED_EXCUSES_FILE}: {e}")
        return {}

def _save_saved_excuses(data):
    try:
        with open(SAVED_EXCUSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving excuses to {SAVED_EXCUSES_FILE}: {e}")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_excuse():
    data = request.get_json()
    scenario = data.get("scenario", "generic situation")
    user_role = data.get("user_role", "generic")
    recipient = data.get("recipient", "generic")
    urgency = data.get("urgency", "medium")
    believability = data.get("believability", "5")
    language = data.get("language", "en")

    if scenario not in VALID_SCENARIOS:
        return jsonify({"excuse": "Invalid scenario provided.", "excuse_id": None}), 400
    
    language_map = {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese", "hi": "Hindi", "bn": "Bengali"
    }
    target_language = language_map.get(language, "English")

    prompt = f"""
    [INST] Generate a concise, realistic, and believable excuse for a {user_role} who needs an excuse for '{scenario}' to their {recipient}. The urgency is {urgency} and believability is {believability}/10 (1=simple, 10=highly detailed). The excuse should be **solely in {target_language}**.
    Do NOT include any conversational filler, introductions, or explicit translations (e.g., do not say "Translation: [English excuse]"). Provide only the excuse itself.
    [/INST]
    """
    
    excuse = get_excuse_from_huggingface(prompt)
    if excuse is None:
        print("Failed to get excuse from AI. Check API key, model access, and network.")
        return jsonify({"excuse": "Failed to get excuse from AI. Please try again.", "excuse_id": None}), 500
    
    excuse_id = str(uuid.uuid4())
    
    current_time_iso = datetime.now().isoformat()
    excuses_db[excuse_id] = {
        "excuse_text": excuse,
        "scenario": scenario,
        "user_role": user_role,
        "recipient": recipient,
        "believability": believability,
        "timestamp": current_time_iso,
        "feedback": {"effective_count": 0, "total_feedback": 0}
    }
    
    insights_db["frequent_scenarios"][scenario] = insights_db["frequent_scenarios"].get(scenario, 0) + 1
    today_str = datetime.now().strftime("%Y-%m-%d")
    insights_db["daily_counts"][today_str] = insights_db["daily_counts"].get(today_str, 0) + 1

    print(f"Generated excuse ID: {excuse_id}")
    return jsonify({"excuse": excuse, "excuse_id": excuse_id})

@app.route("/speak_excuse", methods=["POST"])
def speak_excuse():
    data = request.get_json()
    excuse_text = data.get("excuse", "")
    excuse_id = data.get("excuse_id", str(uuid.uuid4()))
    language_code = data.get("language", "en")

    if not excuse_text:
        return jsonify({"error": "No excuse text provided"}), 400

    try:
        tts = gTTS(text=excuse_text, lang=language_code)

        audio_filename = f"excuse_{excuse_id}_{language_code}.mp3"
        audio_filepath = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
        
        print(f"Attempting to save audio to: {audio_filepath}")
        tts.save(audio_filepath)
        
        time.sleep(0.5)

        if os.path.exists(audio_filepath):
            print(f"SUCCESS: Audio file '{audio_filename}' found on disk at {audio_filepath}")
        else:
            print(f"ERROR: Audio file '{audio_filename}' NOT FOUND on disk at {audio_filepath} after tts.save()")
            return jsonify({"error": "Failed to save audio file to disk."}), 500

        audio_url = url_for('serve_audio_file', filename=audio_filename)
        print(f"Generated audio URL: {audio_url}")
        return jsonify({"audio_url": audio_url})
    except Exception as e:
        print(f"Error generating speech: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/generate_proof/<excuse_id>", methods=["POST"])
def generate_proof(excuse_id):
    data = request.get_json() or {}
    proof_type = data.get("proof_type", "doctor_note")
    excuse = data.get("excuse", "")
    scenario = data.get("scenario", "generic situation")
    print(f"\n--- Attempting to generate proof: excuse_id={excuse_id}, proof_type={proof_type}, scenario={scenario} ---")
    
    proof_path = None
    try:
        if proof_type == "doctor_note":
            proof_path = generate_doctor_doc(excuse_id, scenario)
        elif proof_type == "chat_screenshot":
            proof_path = generate_chat_screenshot(excuse_id, excuse, scenario)
        elif proof_type == "location_log":
            proof_path = generate_location_log(excuse_id, scenario)
        else:
            print(f"Error: Invalid proof type '{proof_type}' requested.")
            return jsonify({"error": "Invalid proof type."}), 400

        if not proof_path:
            print(f"CRITICAL: Proof generation function returned None for {proof_type}. This indicates a failure within the generation process itself. Check logs above for details.")
            return jsonify({"error": "Failed to generate proof file (internal generation error). Check server logs for exact reason."}), 500

        print(f"Proof file path returned by generator: {proof_path}")
        
        time.sleep(0.1)

        file_exists = os.path.exists(proof_path)
        print(f"Result of os.path.exists('{proof_path}'): {file_exists}")

        if not file_exists:
            print(f"CRITICAL: Proof file NOT FOUND on disk at {proof_path} even after generation reported success. This is likely a path mismatch or a rare race condition.")
            return jsonify({"error": f"Proof file was not found on the server at {proof_path} after creation attempt. Path mismatch or race condition."}), 500

        file_basename = os.path.basename(proof_path)
        print(f"Successfully located generated proof file. Sending proof_url: /proofs/{file_basename}")
        return jsonify({"proof_url": f"/proofs/{file_basename}"})
    except Exception as e:
        print(f"UNHANDLED ERROR in /generate_proof/<excuse_id> route: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate proof due to an unexpected server error: ({e}). Please check server logs for details."}), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    excuse_id = data.get('excuse_id')
    is_effective = data.get('is_effective')

    if excuse_id not in excuses_db:
        return jsonify({"error": "Excuse not found."}), 404

    excuse_data = excuses_db[excuse_id]
    
    if excuse_data["excuse_text"] not in insights_db["excuse_feedback"]:
        insights_db["excuse_feedback"][excuse_data["excuse_text"]] = {"effective_count": 0, "total_feedback": 0}

    excuse_data["feedback"]["total_feedback"] += 1
    if is_effective:
        excuse_data["feedback"]["effective_count"] += 1

    insights_db["excuse_feedback"][excuse_data["excuse_text"]]["total_feedback"] += 1
    if is_effective:
        insights_db["excuse_feedback"][excuse_data["excuse_text"]]["effective_count"] += 1

    return jsonify({"message": "Feedback received!", "current_feedback": excuse_data["feedback"]})

@app.route('/insights')
def get_insights():
    ranked_excuses = sorted(
        [
            {"excuse_text": text, **data}
            for text, data in insights_db["excuse_feedback"].items()
            if data["total_feedback"] > 0
        ],
        key=lambda x: x["effective_count"] / x["total_feedback"],
        reverse=True
    )[:5]

    frequent_scenarios_list = sorted(
        [{"scenario": s, "count": c} for s, c in insights_db["frequent_scenarios"].items()],
        key=lambda x: x["count"],
        reverse=True
    )[:5]

    total_excuses_generated = sum(insights_db["daily_counts"].values())
    
    predicted_excuse_time = "No clear pattern yet (generate more excuses!)"
    if total_excuses_generated > 5:
        hour_counts = {}
        for excuse_id, excuse_data in excuses_db.items():
            timestamp_str = excuse_data['timestamp']
            dt_object = datetime.fromisoformat(timestamp_str)
            hour = dt_object.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if hour_counts:
            busiest_hour = max(hour_counts, key=hour_counts.get)
            predicted_excuse_time = f"{busiest_hour}:00 - {busiest_hour+1}:00 (based on past activity)"
            if busiest_hour == 0: predicted_excuse_time = "12 AM - 1 AM (based on past activity)"
            elif busiest_hour == 12: predicted_excuse_time = "12 PM - 1 PM (based on past activity)"
            elif busiest_hour > 12: predicted_excuse_time = f"{busiest_hour - 12} PM - {busiest_hour - 11} PM (based on past activity)"
            else: predicted_excuse_time = f"{busiest_hour} AM - {busiest_hour + 1} AM (based on past activity)"

    insights = {
        "top_excuses": ranked_excuses,
        "frequent_scenarios_all_time": frequent_scenarios_list,
        "predicted_excuse_time": predicted_excuse_time
    }
    return jsonify(insights)

@app.route('/save_excuse', methods=['POST'])
def save_excuse():
    data = request.get_json()
    excuse_text = data.get('excuse_text')
    scenario = data.get('scenario')
    user_role = data.get('user_role')
    recipient = data.get('recipient')
    language = data.get('language')

    if not excuse_text:
        return jsonify({"error": "Excuse text is required to save."}), 400

    saved_excuses = _load_saved_excuses()
    new_id = str(uuid.uuid4())
    saved_excuses[new_id] = {
        "id": new_id,
        "excuse_text": excuse_text,
        "scenario": scenario,
        "user_role": user_role,
        "recipient": recipient,
        "language": language,
        "saved_at": datetime.now().isoformat()
    }
    _save_saved_excuses(saved_excuses)
    return jsonify({"message": "Excuse saved successfully!", "id": new_id}), 201

@app.route('/get_saved_excuses', methods=['GET'])
def get_saved_excuses():
    saved_excuses = _load_saved_excuses()
    return jsonify(list(saved_excuses.values()))

@app.route('/delete_saved_excuse/<excuse_id>', methods=['DELETE'])
def delete_saved_excuse(excuse_id):
    saved_excuses = _load_saved_excuses()
    if excuse_id in saved_excuses:
        del saved_excuses[excuse_id]
        _save_saved_excuses(saved_excuses)
        return jsonify({"message": "Excuse deleted successfully!"}), 200
    return jsonify({"error": "Excuse not found."}), 404

if __name__ == '__main__':
    app.run(debug=True)