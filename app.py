from flask import Flask, request, jsonify
from flask_cors import CORS # type: ignore
from pikepdf import Pdf, PdfImage # type: ignore
import face_recognition # type: ignore
from PIL import Image
import numpy as np
import os


app = Flask(__name__)
CORS(app)

def are_faces_similar(image_path1, image_path2):
    try:
        # Open images and convert them to NumPy arrays
        image1 = np.array(Image.open(image_path1).convert("RGB"))
        image2 = np.array(Image.open(image_path2).convert("RGB"))

        # Detect faces in images
        face_locations1 = face_recognition.face_locations(image1)
        face_locations2 = face_recognition.face_locations(image2)
      
        # Check if no faces are detected
        if len(face_locations1) == 0:
            return "No face detected in the first image."
        if len(face_locations2) == 0:
            return "No face detected in the second image."

        # Extract face encodings
        face_encoding1 = face_recognition.face_encodings(image1, face_locations1)[0]
        face_encoding2 = face_recognition.face_encodings(image2, face_locations2)[0]

        # Compare the faces
        results = face_recognition.compare_faces([face_encoding1], face_encoding2)

        return True if results[0] else False

    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/upload", methods=["POST"])
def upload_files():
    # Check if files are in the request
    if "pdf_file" not in request.files or "image_file" not in request.files:
        return jsonify({"error": "Missing files"}), 400
    
    pdf_file = request.files["pdf_file"]
    image_file = request.files["image_file"]
    
    # =========== Extracting the image from pdf starts here
    pdf_path = "uploaded_pdf.pdf"
    pdf_file.save(pdf_path)
    
    try:
        # Open the PDF
        old_pdf = Pdf.open(pdf_path)
        page_1 = old_pdf.pages[0]
        
        # Check if the page contains images
        images = page_1.images
        if not images:
            return jsonify({"error": "No images found in PDF"}), 400
        
        retResult=False
        stringResult="X"
        
        # Convert the uploaded image to PNG and save
        image_path1 = "uploaded_image.png"
        try:
            img = Image.open(image_file)
            img = img.convert("RGB")  # Ensure it's in RGB mode (if necessary)
            img.save(image_path1, "PNG")  # Save as PNG
        except Exception as e:
            return jsonify({"error": f"Error processing the uploaded image: {str(e)}"}), 400

        for key in page_1.images.keys():
            # Extract the image from the PDF and convert it to PNG
            
            raw_image2 = images[key]
            pdf_image = PdfImage(raw_image2)
            try:
                pdf_image.extract_to(fileprefix="nid-image")
            except Exception as e:
                print(f"Error while converting raw image to PDF image: {str(e)}")
                continue  # Skip this image and continue with the next one
            
            # Convert the extracted image from PDF to PNG
            image_path2 = "nid-image.jpg"
            try:
                image = Image.open(image_path2)
                image = image.convert("RGB")  # Ensure it's in RGB mode
                image_path2 = "nid-image.png"
                image.save(image_path2, "PNG")  # Save as PNG
            except Exception as e:
                print(f"Error converting the extracted PDF image to PNG: {str(e)}")
                continue  # Skip this image and continue with the next one
            
            result = are_faces_similar(image_path1, image_path2)
            if type(result) == str:
                stringResult = result
            else:
                retResult |= result

            # Delete image files after processing
            try:
                
                if os.path.exists(image_path2):
                    os.remove(image_path2)
            except Exception as e:
                print(f"Error while deleting files: {str(e)}")
            
            if retResult:
                break

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # return the result (string for no face or boolean for unmatched faces) as a JSON response
    finalResult = retResult if retResult else stringResult if len(stringResult) > 1 else False
    if os.path.exists(image_path1):
        os.remove(image_path1)
    return jsonify({
        "result": finalResult
    })

@app.route('/')
def home():
    return jsonify({"message": "Flask App Deployed on Render!"})
if __name__ == "__main__":
    app.run(debug=True)