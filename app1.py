import base64
import boto3
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pymysql
from PIL import Image
import io
import concurrent.futures

app = Flask(__name__)

# ── AWS Configuration ─────────────────────────────────────────────────────────
REGION_S3 = 'us-east-1'
REGION_REKOGNITION = 'us-east-1'
BUCKET_NAME = 'face-attendance-bucket-us-east-1'
COLLECTION_ID = 'face-attendance-collection'

# Initialize AWS clients
s3 = boto3.client('s3', region_name=REGION_S3)
rekognition = boto3.client('rekognition', region_name=REGION_REKOGNITION)

# Verify S3 bucket connectivity
try:
    resp = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=1)
    print(f"S3 bucket '{BUCKET_NAME}' is reachable. {resp.get('KeyCount', 0)} objects found.")
except Exception as e:
    print("Error reaching S3 bucket:", e)

# RDS connection function (create new connection each call to avoid timeout)
def get_rds_connection():
    return pymysql.connect(
        host='attendence-db.c0jyi6y2s34k.us-east-1.rds.amazonaws.com',
        user='rachana',
        password='Rachanahn116',
        db='attendance_db',
        connect_timeout=60
    )

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering index: {str(e)}")
        return f"An error occurred: {str(e)}"

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        student_id = data['student_id']
        image_data_url = data['image']  # format: "data:image/jpeg;base64,..."

        # Check if student_id already exists in Rekognition collection
        faces = rekognition.list_faces(CollectionId=COLLECTION_ID)
        for face in faces['Faces']:
            if face.get('ExternalImageId') == student_id:
                return jsonify({"message": f"Student ID '{student_id}' is already registered."}), 400

        # Decode and prepare image
        header, encoded = image_data_url.split(',', 1)
        image_bytes = base64.b64decode(encoded)
        filename = f"{student_id}.jpg"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"registration/{filename}",
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        print(f"Registration image for {student_id} uploaded to S3.")

        # Index face in Rekognition collection from S3 image
        rekognition.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': f"registration/{filename}"}},
            ExternalImageId=student_id,
            DetectionAttributes=['DEFAULT']
        )
        print(f"Face for {student_id} indexed in Rekognition.")

        return jsonify({"message": f"Registered {student_id} successfully"})

    except Exception as e:
        print(f"Error in register: {str(e)}")
        return jsonify({"message": f"Registration failed: {str(e)}"}), 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.json['image']
        image_data = base64.b64decode(data.split(',')[1])

        # Detect all faces in the uploaded image bytes directly
        detect_response = rekognition.detect_faces(
            Image={'Bytes': image_data},
            Attributes=['DEFAULT']
        )
        face_details = detect_response.get('FaceDetails', [])
        if not face_details:
            return jsonify({"message": "No faces detected"}), 404

        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        matched_ids = set()

        def match_face(face):
            box = face['BoundingBox']
            left = int(box['Left'] * width)
            top = int(box['Top'] * height)
            box_width = int(box['Width'] * width)
            box_height = int(box['Height'] * height)

            cropped_face = image.crop((left, top, left + box_width, top + box_height))
            cropped_face = cropped_face.resize((300, 300))  # resize to speed up

            cropped_io = io.BytesIO()
            cropped_face.save(cropped_io, format='JPEG')
            cropped_bytes = cropped_io.getvalue()

            try:
                search_response = rekognition.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': cropped_bytes},
                    FaceMatchThreshold=90,
                    MaxFaces=1
                )
                matches = search_response.get('FaceMatches', [])
                if matches:
                    return matches[0]['Face']['ExternalImageId']
            except Exception as e:
                print(f"Face matching error: {e}")
            return None

        # Use threads to speed up matching multiple faces
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(match_face, face_details))

        for student_id in results:
            if student_id:
                matched_ids.add(student_id)

        if not matched_ids:
            return jsonify({"message": "No registered students recognized"}), 404

        # Mark attendance in RDS
        conn = get_rds_connection()
        with conn.cursor() as cursor:
            date = datetime.now().strftime('%Y-%m-%d')
            for student_id in matched_ids:
                cursor.execute(
                    "REPLACE INTO attendance (student_id, date, status) VALUES (%s, %s, %s)",
                    (student_id, date, 'present')
                )
            conn.commit()
        conn.close()

        return jsonify({"message": f"Attendance marked for: {', '.join(matched_ids)}"}), 200

    except Exception as e:
        print(f"Error in upload: {str(e)}")
        return jsonify({"message": f"An error occurred during the upload: {str(e)}"}), 500

@app.route('/attendence')
def attendence_history():
    try:
        conn = get_rds_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT student_id, date, status FROM attendance ORDER BY date DESC")
            records = cursor.fetchall()
        conn.close()
        return render_template('attendence.html', records=records)
    except Exception as e:
        print(f"Error fetching attendance history: {str(e)}")
        return f"An error occurred: {str(e)}"

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
