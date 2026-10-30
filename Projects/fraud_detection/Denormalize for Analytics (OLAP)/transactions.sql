CREATE TABLE transactions (
    row_id INT PRIMARY KEY,
    trans_date_trans_time TIMESTAMP,
    cc_num VARCHAR(30),          -- Stored as string to preserve full precision (avoids scientific notation issues)
    merchant VARCHAR(255),
    category VARCHAR(100),
    amt DECIMAL(10, 2),          -- Precise financial representation
    first VARCHAR(50),
    last VARCHAR(50),
    gender VARCHAR(10),
    street VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(10),
    zip VARCHAR(10),             -- Stored as string to safely handle leading zeros in postal codes
    lat DECIMAL(9, 6),           -- Standard geographic precision
    long DECIMAL(9, 6),          -- Standard geographic precision
    city_pop INT,
    job VARCHAR(100),
    dob DATE,
    trans_num VARCHAR(100) UNIQUE, -- Unique transaction hash identifier
    unix_time BIGINT,            -- Unix timestamp epoch
    merch_lat DECIMAL(9, 6),
    merch_long DECIMAL(9, 6),
    is_fraud INT                 -- 0 for legitimate, 1 for fraudulent
);

-- 1. Index for credit card lookups (useful for analyzing individual spending patterns)
CREATE INDEX idx_transactions_cc_num ON transactions(cc_num);

-- 2. Index for category grouping (accelerates the Z-score and aggregation queries)
CREATE INDEX idx_transactions_category ON transactions(category);

-- 3. Index for transaction timestamp (crucial for time-series filters and velocity checks)
CREATE INDEX idx_transactions_trans_time ON transactions(trans_date_trans_time);