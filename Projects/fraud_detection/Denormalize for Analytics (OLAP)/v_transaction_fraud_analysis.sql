CREATE VIEW v_transaction_fraud_analysis AS
SELECT 
    row_id,
    trans_date_trans_time,
    cc_num,
    merchant,
    category,
    amt,
    first,
    last,
    city,
    state,
    is_fraud,
    
    -- 1. Rounded geographic clusters (2 decimal places ~ 1.1 km)
    ROUND(lat, 2) AS lat_rounded,
    ROUND(long, 2) AS long_rounded,
    
    -- 2. Group statistics (Category + Rounded Location)
    AVG(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2)) AS group_mean_amt,
    STDDEV(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2)) AS group_std_amt,
    
    -- 3. Z-score calculation (with safety check for 0 standard deviation)
    CASE 
        -- If stddev is 0 or null (e.g., only 1 transaction in the group), set Z-score to 0
        WHEN STDDEV(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2)) = 0 
             OR STDDEV(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2)) IS NULL 
        THEN 0
        ELSE (amt - AVG(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2))) / 
             STDDEV(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2))
    END AS amt_zscore,
    
    -- 4. Outlier flag based on threshold (e.g., Z-score > 3 or < -3)
    CASE 
        WHEN ABS(
            (amt - AVG(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2))) / 
            NULLIF(STDDEV(amt) OVER(PARTITION BY category, ROUND(lat, 2), ROUND(long, 2)), 0)
        ) > 3.0 THEN 1
        ELSE 0
    END AS is_outlier

FROM transactions;