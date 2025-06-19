CREATE DATABASE attendance_db;
USE attendance_db;

CREATE TABLE attendance (
    student_id VARCHAR(255),
    date DATE,
    status VARCHAR(10),
    PRIMARY KEY (student_id, date)
);
