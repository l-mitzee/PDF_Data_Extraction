from flask import Flask, request, jsonify, render_template
from flask_cors import CORS, cross_origin
from google.cloud import storage
from doc_extract import DocumentDataExtraction
import csv
import os

app = Flask(__name__)
CORS(app)

# Configure Google Cloud Storage client
Client = storage.Client.from_service_account_json(json_credentials_path='labeling-proj-lisa-6295-e3e63c12c9ba.json')
bucket_name = 'doc_bucket_extract'  # Replace with your GCS bucket name

class ClientApp:
    def __init__(self):
        self.pdf_file_path = ''

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=['POST'])
@cross_origin()
def submitRoute():
    pdf_file = request.files['pdf_file']
    if pdf_file.filename != '':
        # Save the PDF file to GCS bucket
        destination_blob_name = 'uploaded_files/' + pdf_file.filename  # Specify the destination filename in the bucket

        bucket = Client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(pdf_file)

        # Process the uploaded PDF file
        clApp = ClientApp()
        clApp.pdf_file_path = 'gs://' + bucket_name + '/' + destination_blob_name

        return "File uploaded successfully."

@app.route("/extract", methods=['GET'])
@cross_origin()
def extractRoute():
    # Get the list of PDF files from the GCS bucket
    bucket_name = 'doc_bucket_extract'
    bucket = Client.bucket(bucket_name)
    blobs = list(Client.list_blobs(bucket, prefix='uploaded_files/'))

    if blobs:
        extraction = DocumentDataExtraction()
        csv_data = []

        # Process each PDF file
        for blob in blobs:
            if blob.name.endswith('.pdf'):
                # Create the necessary directories
                os.makedirs('/tmp/uploaded_files', exist_ok=True)

                # Download the PDF file to a temporary location
                pdf_temp_file_path = '/tmp/uploaded_files/' + os.path.basename(blob.name)
                
                try:
                    blob.download_to_filename(pdf_temp_file_path)
                except Exception as e:
                    # Print or log the error message
                    print(f"Error downloading file {blob.name}: {str(e)}")
                    continue

                # Extract information from the PDF file
                extracted_info = extraction.extract_invoice_info(pdf_temp_file_path)

                if isinstance(extracted_info, dict):
                    # Append extracted information to the CSV data
                    for key, value in extracted_info.items():
                        csv_data.append([blob.name, key, value])

        if csv_data:
            # Save extracted information to CSV
            csv_filename = 'extracted_info.csv'
            csv_blob_name = 'extracted_files/' + csv_filename
            csv_temp_file_path = '/tmp/' + csv_filename

            with open(csv_temp_file_path, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerows(csv_data)

            # Upload the CSV file to the GCS bucket
            csv_blob = bucket.blob(csv_blob_name)
            csv_blob.upload_from_filename(csv_temp_file_path)

            return f"Key information extracted and saved to {csv_blob_name}"

    return "No PDF files found in the bucket."

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=7000, debug=True)
