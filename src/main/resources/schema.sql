
CREATE TABLE IF NOT EXISTS consumers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consumer_number VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    address VARCHAR(255),
    connection_type VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consumer_id INT NOT NULL,
    reading_date DATE NOT NULL,
    previous_reading DOUBLE NOT NULL,
    current_reading DOUBLE NOT NULL,
    units DOUBLE NOT NULL,
    FOREIGN KEY (consumer_id) REFERENCES consumers(id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consumer_id INT NOT NULL,
    reading_id INT NOT NULL,
    bill_month VARCHAR(7) NOT NULL,
    units DOUBLE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Pending',
    FOREIGN KEY (consumer_id) REFERENCES consumers(id),
    FOREIGN KEY (reading_id) REFERENCES readings(id)
);
