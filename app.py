import os
import logging
from datetime import datetime

import google.generativeai as genai
from flask import (Flask, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from werkzeug.utils import secure_filename

from configAI import GOOGLE_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = "super secret key"  # Change this in a real application!
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
RULES_FILE = "regras.txt"  # Define the rules file
ALLOWED_EXTENSIONS = {"txt", "json"}  # Add more if needed


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# Ensure upload and output folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Configure the Google API
genai.configure(api_key=GOOGLE_API_KEY)
MODELO_ESCOLHIDO = "gemini-2.0-flash"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_rules(rules_file):
    """Loads the rules from the specified file."""
    try:
        with open(rules_file, "r") as f:
            rules_content = f.read()
            logging.info(f"Successfully loaded rules from {rules_file}")
            return rules_content
    except FileNotFoundError:
        logging.warning(f"Rules file not found: {rules_file}")
        return "No rules file found."
    except Exception as e:
        logging.error(f"Error reading rules file: {e}")
        return f"Error reading rules file: {e}"


def build_system_prompt(rules_content):
    """Builds the system prompt for the AI."""
    prompt = """
    VOCÊ É UM ESPECIALISTA EM INTEGRAÇÃO ENTRE SISTEMAS COM HABILIDADES PARA ANALISAR APIS.
    """
    if rules_content:
        prompt += f"\nRegras:\n{rules_content}"
    return prompt


def process_with_ai(file_content, rules_content):
    """Processes the file content with the Gemini AI model."""
    model = genai.GenerativeModel(MODELO_ESCOLHIDO)
    try:
        # Combine rules and file content into a single prompt
        prompt = f"Regras:\n{rules_content}\n\nConteúdo do Arquivo:\n{file_content}"
        logging.info("Prompt sent to AI: " + prompt)
        response = model.generate_content(prompt)
        logging.info("AI processing complete.")
        return response.text
    except Exception as e:
        logging.error(f"Error processing with AI: {e}")
        return f"Error processing with AI: {e}"


@app.route("/", methods=["GET", "POST"])
def upload_file():
    logging.info("upload_file function called")
    if request.method == "POST":
        # Check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            logging.warning("No file part in the request")
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            flash("No selected file")
            logging.warning("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            try:
                file.save(file_path)
                logging.info(f"File saved successfully to {file_path}")
            except Exception as e:
                flash(f"Error saving file: {e}")
                logging.error(f"Error saving file: {e}")
                return redirect(request.url)

            try:
                with open(file_path, "r") as f:
                    file_content = f.read()
                logging.info(f"File content read successfully from {file_path}")
            except Exception as e:
                flash(f"Error reading file: {e}")
                logging.error(f"Error reading file: {e}")
                return redirect(request.url)

            # Load the rules
            rules_content = load_rules(RULES_FILE)

            ai_output = process_with_ai(file_content, rules_content)

            # Save the AI output to a file named resultado.txt
            output_filename = "resultado.txt"
            output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)
            try:
                with open(output_path, "w") as f:
                    f.write(ai_output)
                logging.info(f"AI output saved to {output_path}")
            except Exception as e:
                flash(f"Error writing output file: {e}")
                logging.error(f"Error writing output file: {e}")
                return redirect(request.url)

            return redirect(url_for("download_file", name=output_filename))
        else:
            flash("Invalid file type")
            logging.warning("Invalid file type uploaded")
            return redirect(request.url)
    return render_template("index.html")


@app.route("/uploads/<name>")
def download_file(name):
    logging.info(f"Download requested for file: {name}")
    return send_from_directory(app.config["OUTPUT_FOLDER"], name)


if __name__ == "__main__":
    app.run(debug=True)
