# 📸 Face Recognition-Based Attendance System

A web-based application that leverages **Amazon Rekognition**, **Amazon S3**, and **Amazon RDS (MySQL)** to enable face-based student registration and attendance marking using live webcam captures.

---

## 🔧 Features

- ✅ Register students with face images
- 📸 Capture webcam images for attendance
- 🧠 Detect and recognize faces using AWS Rekognition
- ☁️ Store images securely in S3
- 🗃️ Log attendance records in Amazon RDS
- 🔍 Prevent duplicate registration by Student ID
- 📅 View attendance history from the web interface

---

## 🛠️ Tech Stack

| Component     | Technology              |
|---------------|--------------------------|
| Backend       | Flask (Python)           |
| Frontend      | HTML, JavaScript         |
| Face Detection| AWS Rekognition          |
| Image Storage | Amazon S3                |
| Database      | Amazon RDS (MySQL)       |

---

##
Flask-based smart attendance system that uses AWS Rekognition for face detection and recognition. It supports multi-face recognition from a single image and logs attendance to an AWS RDS MySQL database. Student images are stored in AWS S3 — be sure to update the bucket name, Rekognition collection ID, and RDS credentials with your own AWS service details before deployment.


