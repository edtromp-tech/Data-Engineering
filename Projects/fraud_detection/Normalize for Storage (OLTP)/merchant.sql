CREATE TABLE merchants (
    merchant_id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_name VARCHAR(255) UNIQUE,
    merch_lat DECIMAL(9, 6),
    merch_long DECIMAL(9, 6)
);