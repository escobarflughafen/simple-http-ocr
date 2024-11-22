from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import pytesseract
from openai import OpenAI
import os
import dotenv
import logging
import json


dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["DEBUG"] = True
CORS(app)

# Config logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Set OpenAI API Key
PORT = os.getenv("PORT")
API_KEY = os.getenv("OPENAI_API_KEY")  # Set your OpenAI key in the environment
MODEL = os.getenv("OPENAI_MODEL")

openai_client = OpenAI()
logging.info(f"OpenAI initialized, using model {MODEL}.")


@app.route('/extract-and-format-ocr', methods=['POST'])
def extractAndFormatOCR():
    """
    Processes input data: image, text, or both, and formats into structured JSON using GPT.
    """
    # Extract image and text from the request
    file = request.files.get('image', None)
    raw_text = request.form.get('text', "").strip()

    if not file and not raw_text:
        return jsonify({"error": "You must provide at least an image or text"}), 400

    ocr_text = ""
    if file:
        logging.info("Image file received. Processing OCR...")
        try:
            image = Image.open(file)
            ocr_text = pytesseract.image_to_string(image)
            logging.info("OCR processing completed.")
        except Exception as e:
            logging.error(f"OCR processing failed: {e}")
            return jsonify({"error": "OCR processing failed", "details": str(e)}), 500

    # Combine data sources
    if file and raw_text:
        combined_text = f"{ocr_text}\n\nAdditional context from user:\n{raw_text}"
    elif raw_text:
        combined_text = raw_text
    else:
        combined_text = ocr_text

    # Call GPT to format the text
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that formats OCR text into valid JSON for Python."},
            {
                "role": "user",
                "content": f"""
                The following text is extracted from a receipt using OCR:
                ---
                {combined_text}
                ---
                Format this text into a valid JSON object that can be parsed by Python's `json.loads()` without any issues.
                Ensure the JSON:
                1. Does not include code block markers (e.g., ```json).
                2. Uses double quotes for all keys and string values.
                3. Is properly escaped and formatted for JSON standards.
                4. Includes a "transactions" array with each transaction containing these keys:
                    - "Transaction Name"
                    - "Category"
                    - "Amount" (as a number)
                    - "Place"
                    - "Date"
                    - "Additional Info" (as null if missing).
                5. Adds any summary fields if necessary, such as "Total Amount", "Card Type", etc.
                """
            }
        ]
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.5
        )

        completion = response.choices[0].message.content.strip()

        formatted_json = json.loads(completion)

        logging.info(
            f"Text processed by {MODEL} with response {formatted_json}.")

    except Exception as e:
        return jsonify({"error": "OpenAI API call failed", "details": str(e)}), 500

    # Return the formatted JSON object
    try:
        return jsonify({
            "status": "success",
            "ocr_text": ocr_text,
            "formatted_data": formatted_json
        })
    except Exception as e:
        return jsonify({"error": "Failed to return JSON", "details": str(e)}), 500


# Health Check Endpoint
@app.route('/health', methods=['GET'])
def healthCheck():
    """
    A simple health check endpoint to verify the service is running.
    """
    return jsonify({"status": "running"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
