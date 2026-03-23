CREATE DATABASE fit;

USE fit;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    password VARCHAR(255)
);

CREATE TABLE health_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    heart_rate INT,
    steps INT,
    sleep FLOAT,
    status VARCHAR(50),
    entry_time DATETIME
);