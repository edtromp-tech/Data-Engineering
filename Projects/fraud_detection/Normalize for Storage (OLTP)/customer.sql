-- 1. Customer Table (Static or slowly changing customer details)
CREATE TABLE customers (
    cc_num VARCHAR(30) PRIMARY KEY,
    first VARCHAR(50),
    last VARCHAR(50),
    gender VARCHAR(10),
    street VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(10),
    zip VARCHAR(10),
    lat DECIMAL(9, 6),
    long DECIMAL(9, 6),
    city_pop INT,
    job VARCHAR(100),
    dob DATE
);