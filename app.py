from flask import Flask, request, jsonify
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
    Extracts text from an uploaded image using OCR and formats the text into structured JSON using GPT.
    """
    # Validate input
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['image']
    logging.info("Image file received.")

    # Load the image
    try:
        image = Image.open(file)
        logging.info("Image file loaded.")
    except Exception as e:
        return jsonify({"error": "Invalid image file", "details": str(e)}), 400

    # Perform OCR using pytesseract
    try:
        ocr_text = pytesseract.image_to_string(image)
        logging.info(f"Image processed by OCR with text {ocr_text}.")
    except Exception as e:
        return jsonify({"error": "OCR processing failed", "details": str(e)}), 500

    # Call GPT to format the text
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that formats OCR text into valid JSON for Python."},
            {
                "role": "user",
                "content": f"""
                The following text is extracted from a receipt using OCR:
                ---
                {ocr_text}
                ---
                Format this text into a valid JSON object that can be parsed by Python's `json.loads()` without any issues.
                Ensure the JSON:
                1. Does not include code block markers (e.g., ```json).
                2. Uses double quotes for all keys and string values.
                3. Is properly escaped and formatted for JSON standards.
                4. Includes a "transactions" array with each transaction containing:
                    - "Transaction Name"
                    - "Amount" (as a number)
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
