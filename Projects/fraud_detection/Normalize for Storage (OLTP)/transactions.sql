CREATE TABLE transactions (
    row_id INT PRIMARY KEY,
    trans_num VARCHAR(100) UNIQUE,
    cc_num VARCHAR(30),
    merchant_id INT,
    trans_date_trans_time TIMESTAMP,
    category VARCHAR(100),
    amt DECIMAL(10, 2),
    unix_time BIGINT,
    is_fraud INT,
    FOREIGN KEY (cc_num) REFERENCES customers(cc_num),
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id)
);