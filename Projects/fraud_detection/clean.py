from dataclasses import dataclass, asdict
import pandas as pd
import re
from datetime import datetime

@dataclass
class Transaction:
    row_id: int
    trans_date_trans_time: str
    cc_num: str
    merchant: str
    category: str
    amt: float
    first: str
    last: str
    gender: str
    street: str
    city: str
    state: str
    zip_code: int
    lat: float
    long: float
    city_pop: int
    job: str
    dob: str
    trans_num: str
    unix_time: int
    merch_lat: float
    merch_long: float
    is_fraud: int

    def clean(self) -> 'Transaction':
        """Cleans and normalizes the fields of the transaction object in-place."""
        
        # 1. Clean strings (strip whitespace, normalize case)
        self.merchant = self.merchant.strip()
        self.category = self.category.strip().lower() # standardize categories to lowercase
        self.first = self.first.strip().capitalize()
        self.last = self.last.strip().capitalize()
        self.city = self.city.strip().title()
        self.state = self.state.strip().upper()        # ensure state is 2-letter uppercase
        self.gender = self.gender.strip().upper()      # ensure gender is 'M' or 'F'
        self.job = self.job.strip()

        # 2. Fix scientific notation or float strings in credit card numbers if any leaked through
        # (e.g., converting something like '2.29116E+15' safely if it was read as float)
        if 'E' in str(self.cc_num) or '.' in str(self.cc_num):
            try:
                self.cc_num = str(int(float(self.cc_num)))
            except ValueError:
                pass
        self.cc_num = str(self.cc_num).strip()

        # 3. Financial validations (ensure amount is positive; flag or adjust if invalid)
        if self.amt < 0:
            # Option: take absolute value, or log it as an anomaly
            self.amt = abs(self.amt)

        # 4. Optional: Date format normalization (ensure standard string format)
        # You can add regex checks or datetime parsing here if needed
        # Normalize transaction timestamp to 'YYYY-MM-DD HH:MM:SS'
        if self.trans_date_trans_time:
            self.trans_date_trans_time = self._normalize_timestamp(self.trans_date_trans_time)

        # Normalize Date of Birth (DOB) to 'YYYY-MM-DD'
        if self.dob:
            self.dob = self._normalize_date(self.dob)

        return self

    @classmethod
    def from_series(cls, series: pd.Series) -> 'Transaction':
        """Instantiate and automatically clean a Transaction object from a DataFrame row."""
        instance = cls(
            row_id=int(series.get('row_id', 0)),
            trans_date_trans_time=str(series['trans_date_trans_time']),
            cc_num=str(series['cc_num']),
            merchant=str(series['merchant']),
            category=str(series['category']),
            amt=float(series['amt']),
            first=str(series['first']),
            last=str(series['last']),
            gender=str(series['gender']),
            street=str(series['street']),
            city=str(series['city']),
            state=str(series['state']),
            zip_code=int(str(series['zip']).split('.')[0]), # handles zip read as float with .0
            lat=float(series['lat']),
            long=float(series['long']),
            city_pop=int(series['city_pop']),
            job=str(series['job']),
            dob=str(series['dob']),
            trans_num=str(series['trans_num']),
            unix_time=int(series['unix_time']),
            merch_lat=float(series['merch_lat']),
            merch_long=float(series['merch_long']),
            is_fraud=int(series['is_fraud'])
        )
         # Automatically trigger cleaning upon instantiation
        return instance.clean()

    @staticmethod
    def _normalize_timestamp(val: str) -> str:
        """Tries common timestamp formats and standardizes to YYYY-MM-DD HH:MM:SS."""
        val = str(val).strip()
        # List of common input formats your CSV might contain
        formats = [
            "%m/%d/%Y %H:%M",     # e.g., "06/21/2020 12:14"
            "%Y-%m-%d %H:%M:%S",  # e.g., "2020-06-21 12:14:00"
            "%m/%d/%Y %H:%M:%S",  # e.g., "06/21/2020 12:14:00"
            "%Y-%m-%d %H:%M"      # e.g., "2020-06-21 12:14"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(val, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
                
        # Fallback if no format matches (returns original string so you don't lose data)
        return val

    @staticmethod
    def _normalize_date(val: str) -> str:
        """Tries common date formats and standardizes to YYYY-MM-DD."""
        val = str(val).strip()
        formats = [
            "%Y-%m-%d",  # e.g., "1968-03-19"
            "%m/%d/%Y",  # e.g., "03/19/1968"
            "%d-%m-%Y"   # e.g., "19-03-1968"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(val, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
                
        return val    
    
   