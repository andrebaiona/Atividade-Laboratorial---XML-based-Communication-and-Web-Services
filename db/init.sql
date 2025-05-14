
CREATE DATABASE IF NOT EXISTS tracking_db;
USE tracking_db; 


CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, 
    role VARCHAR(10) NOT NULL DEFAULT 'client', 
    email VARCHAR(100) UNIQUE,
    INDEX(username),
    INDEX(email)
);

CREATE TABLE IF NOT EXISTS packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    sender_city VARCHAR(100) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    is_tracked BOOLEAN NOT NULL DEFAULT FALSE,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE, 
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE 
);

CREATE TABLE IF NOT EXISTS tracking_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    package_id INT NOT NULL,
    city VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE 
);

INSERT IGNORE INTO users (username, password_hash, role, email) VALUES
('admin', '$argon2id$v=19$m=65536,t=3,p=4$kyXkt0snUsNCJsb2nD7DPw$mJ7BD6nRaExB9RtYlkkGbpz8NRxFCf7YbzEW/gdV7Qk', 'admin', 'admin@example.com');