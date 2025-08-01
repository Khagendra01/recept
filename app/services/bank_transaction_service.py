import csv
import io
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime
from math import ceil
import pandas as pd
import json
from openai import OpenAI
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from collections import defaultdict

from app.core.config import settings
from app.models.bank_transaction import BankTransaction
from app.models.transaction import Transaction
from app.schemas.bank_transaction import (
    BankTransactionCreate, 
    BankTransactionUpdate, 
    BankTransactionList,
    CSVUploadResponse,
    ComparisonResult,
    TransactionMatch
)

class BankTransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)    
    def create_bank_transaction(self, transaction_create: BankTransactionCreate) -> BankTransaction:
        """Create new bank transaction"""
        db_transaction = BankTransaction(**transaction_create.model_dump())
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction
    
    def get_bank_transaction(self, transaction_id: int) -> Optional[BankTransaction]:
        """Get bank transaction by ID"""
        return self.db.query(BankTransaction).filter(BankTransaction.id == transaction_id).first()
    
    def update_bank_transaction(
        self, 
        transaction_id: int, 
        transaction_update: BankTransactionUpdate
    ) -> Optional[BankTransaction]:
        """Update bank transaction"""
        db_transaction = self.get_bank_transaction(transaction_id)
        if not db_transaction:
            return None
        
        update_data = transaction_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_transaction, field, value)
        
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction
    
    def get_user_bank_transactions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        batch_id: str = None
    ) -> BankTransactionList:
        """Get bank transactions for a user"""
        
        query = self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id)
        
        if batch_id:
            query = query.filter(BankTransaction.upload_batch_id == batch_id)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        transactions = (
            query
            .order_by(desc(BankTransaction.date), desc(BankTransaction.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        pages = ceil(total / limit) if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return BankTransactionList(
            transactions=transactions,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
    
    async def process_csv_upload(self, user_id: int, csv_content: bytes) -> CSVUploadResponse:
        """Process uploaded CSV file with bank transactions using improved parsing"""
        batch_id = str(uuid.uuid4())
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        try:
            # Decode CSV content
            csv_text = csv_content.decode('utf-8')
            
            # Try OpenAI parsing first, with fallback to traditional parsing
            transactions_data = await self._parse_csv_with_openai(csv_text)
            
            # If OpenAI parsing fails or returns no data, use traditional parsing
            if not transactions_data:
                transactions_data = self._parse_csv_traditional(csv_text)
            
            total_transactions = len(transactions_data)
            
            # Process each transaction
            for i, transaction_data in enumerate(transactions_data):
                try:
                    # Clean and validate data
                    cleaned_data = self._clean_transaction_data_improved(transaction_data)
                    
                    if cleaned_data:
                        # Create bank transaction
                        bank_transaction_create = BankTransactionCreate(
                            user_id=user_id,
                            upload_batch_id=batch_id,
                            **cleaned_data
                        )
                        
                        self.create_bank_transaction(bank_transaction_create)
                        successful_imports += 1
                    else:
                        failed_imports += 1
                        errors.append(f"Row {i+1}: Invalid transaction data")
                        
                except Exception as e:
                    failed_imports += 1
                    errors.append(f"Row {i+1}: {str(e)}")
            
            return CSVUploadResponse(
                batch_id=batch_id,
                total_transactions=total_transactions,
                successful_imports=successful_imports,
                failed_imports=failed_imports,
                errors=errors[:10]  # Limit to first 10 errors
            )
            
        except Exception as e:
            return CSVUploadResponse(
                batch_id=batch_id,
                total_transactions=0,
                successful_imports=0,
                failed_imports=1,
                errors=[f"CSV parsing error: {str(e)}"]
            )
    
    def _parse_csv_traditional(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV using traditional methods with improved logic"""
        transactions = []
        
        try:
            # Create StringIO object
            csv_file = io.StringIO(csv_text)
            
            # Try to detect delimiter
            sample = csv_file.read(1024)
            csv_file.seek(0)
            
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            # Read CSV with error handling
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Normalize column names
                    normalized_row = self._normalize_csv_row(row)
                    
                    # Skip empty rows
                    if not any(normalized_row.values()):
                        continue
                    
                    # Skip header-like rows (rows that look like headers)
                    if self._is_header_row(normalized_row):
                        continue
                    
                    transactions.append(normalized_row)
                    
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            print(f"Error in traditional CSV parsing: {e}")
            return []
    
    def _normalize_csv_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CSV row with improved field mapping"""
        normalized_row = {}
        
        # Enhanced field mappings with more variations
        field_mappings = {
            'date': [
                'date', 'transaction_date', 'posted_date', 'trans_date', 'posting_date',
                'transaction date', 'posting date', 'date posted', 'effective date'
            ],
            'description': [
                'description', 'memo', 'merchant', 'payee', 'details', 'transaction description',
                'merchant name', 'payee name', 'transaction details', 'memo/description',
                'merchant/description', 'merchant_description'
            ],
            'amount': [
                'amount', 'transaction_amount', 'debit', 'credit', 'transaction amount',
                'debit amount', 'credit amount', 'withdrawal', 'deposit'
            ],
            'balance': [
                'balance', 'running_balance', 'account_balance', 'running balance',
                'account balance', 'ending balance', 'new balance'
            ],
            'transaction_type': [
                'type', 'transaction_type', 'debit_credit', 'transaction type',
                'debit/credit', 'dc', 'dr_cr'
            ],
            'reference_number': [
                'reference', 'ref_number', 'check_number', 'transaction_id', 'reference number',
                'check number', 'transaction id', 'ref', 'check', 'id'
            ],
            'category': [
                'category', 'categories', 'transaction_category', 'transaction categories'
            ]
        }
        
        # Normalize column names and map to standard fields
        for key, value in row.items():
            if not key or not value:
                continue
                
            # Normalize key
            normalized_key = key.lower().strip()
            normalized_key = re.sub(r'[^\w\s]', ' ', normalized_key)
            normalized_key = re.sub(r'\s+', '_', normalized_key).strip('_')
            
            # Find matching field
            mapped_field = None
            for field, variations in field_mappings.items():
                if any(var in normalized_key for var in variations):
                    mapped_field = field
                    break
            
            if mapped_field:
                normalized_row[mapped_field] = value.strip() if value else None
            else:
                # Keep original field if no mapping found
                normalized_row[normalized_key] = value.strip() if value else None
        
        return normalized_row
    
    def _is_header_row(self, row: Dict[str, Any]) -> bool:
        """Check if row looks like a header row"""
        header_indicators = [
            'date', 'description', 'amount', 'balance', 'type', 'reference',
            'transaction', 'debit', 'credit', 'memo', 'merchant'
        ]
        
        row_values = ' '.join(str(v).lower() for v in row.values() if v)
        
        # Check if row contains header-like text
        header_count = sum(1 for indicator in header_indicators if indicator in row_values)
        return header_count >= 2  # If 2 or more header indicators, likely a header row
    
    def _parse_csv_file(self, csv_file: io.StringIO) -> List[Dict[str, Any]]:
        """Parse CSV file and return list of transaction dictionaries"""
        transactions = []
        
        # Reset file pointer
        csv_file.seek(0)
        
        # Try to detect delimiter
        sample = csv_file.read(1024)
        csv_file.seek(0)
        
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        
        # Read CSV
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        for row in reader:
            # Normalize column names (lowercase, replace spaces with underscores)
            normalized_row = {}
            for key, value in row.items():
                if key:
                    normalized_key = key.lower().replace(' ', '_').replace('-', '_')
                    normalized_row[normalized_key] = value.strip() if value else None
            
            transactions.append(normalized_row)
        
        return transactions
    
    async def _parse_csv_with_openai(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV file using OpenAI API to extract structured transaction data"""
        try:
            # Create prompt for OpenAI to parse the entire CSV
            prompt = self._create_csv_parsing_prompt(csv_text)
            
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at parsing CSV files containing bank transaction data. Extract all transactions and return them as a JSON array. Each transaction should have: date (ISO format), description, amount (as float), balance (as float), transaction_type, reference_number (optional). Handle various CSV formats and column names intelligently. Return only valid JSON without any markdown formatting or code blocks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Try to extract JSON from markdown code blocks if present
            json_content = content
            if content.startswith('```json'):
                # Extract JSON from markdown code block
                json_content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                # Extract JSON from generic code block
                json_content = content.replace('```', '').strip()
            
            # Try to parse JSON response
            try:
                transactions_data = json.loads(json_content)
                
                # Validate that it's a list
                if not isinstance(transactions_data, list):
                    print("OpenAI response is not a list")
                    return []
                
                # Validate each transaction
                validated_transactions = []
                for i, transaction in enumerate(transactions_data):
                    if isinstance(transaction, dict):
                        # Ensure required fields exist
                        if 'date' in transaction and 'amount' in transaction:
                            validated_transactions.append(transaction)
                        else:
                            print(f"Transaction {i} missing required fields")
                    else:
                        print(f"Transaction {i} is not a dictionary")
                
                return validated_transactions
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Failed to parse OpenAI response as JSON: {e}")
                print(f"Response content: {content}")
                return []
                
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return []
    
    def _create_csv_parsing_prompt(self, csv_text: str) -> str:
        """Create prompt for OpenAI to parse CSV data"""
        return f"""
Please parse the following CSV file and extract all bank transactions. 

CSV Content:
{csv_text}

Instructions:
1. Identify all transaction rows in the CSV
2. Extract the following fields for each transaction:
   - date: Convert to ISO format (YYYY-MM-DD)
   - description: Transaction description/memo
   - amount: Convert to float (positive for credits, negative for debits)
   - balance: Running balance (if available)
   - transaction_type: "credit" or "debit" (if not clear, infer from amount sign)
   - reference_number: Any reference/check number (optional)

3. Handle various CSV formats and column names intelligently
4. Skip header rows and non-transaction rows
5. Return as a JSON array of transaction objects

Example output format:
[
  {{
    "date": "2024-01-15",
    "description": "GROCERY STORE PURCHASE",
    "amount": -45.67,
    "balance": 1234.56,
    "transaction_type": "debit",
    "reference_number": "123456"
  }},
  {{
    "date": "2024-01-16",
    "description": "SALARY DEPOSIT",
    "amount": 2500.00,
    "balance": 3734.56,
    "transaction_type": "credit",
    "reference_number": null
  }}
]

Return only valid JSON.
"""
    
    def _clean_transaction_data_improved(self, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean and validate transaction data with improved logic"""
        try:
            cleaned = {}
            
            # Extract and validate date
            date_value = self._extract_field_value(transaction_data, ['date', 'transaction_date', 'posted_date'])
            if date_value:
                parsed_date = self._parse_date_improved(date_value)
                if parsed_date:
                    cleaned['date'] = parsed_date
                else:
                    return None  # Invalid date is a deal breaker
            else:
                return None  # No date is a deal breaker
            
            # Extract and validate amount
            amount_value = self._extract_field_value(transaction_data, ['amount', 'transaction_amount', 'debit', 'credit'])
            if amount_value:
                parsed_amount = self._parse_amount_improved(amount_value)
                if parsed_amount is not None:
                    cleaned['amount'] = parsed_amount
                else:
                    return None  # Invalid amount is a deal breaker
            else:
                return None  # No amount is a deal breaker
            
            # Extract description
            description_value = self._extract_field_value(transaction_data, ['description', 'memo', 'merchant', 'payee'])
            if description_value:
                cleaned['description'] = self._clean_description(description_value)
            
            # Extract balance
            balance_value = self._extract_field_value(transaction_data, ['balance', 'running_balance', 'account_balance'])
            if balance_value:
                parsed_balance = self._parse_amount_improved(balance_value)
                if parsed_balance is not None:
                    cleaned['balance'] = parsed_balance
            
            # Extract transaction type
            type_value = self._extract_field_value(transaction_data, ['transaction_type', 'type', 'debit_credit'])
            if type_value:
                cleaned['transaction_type'] = self._normalize_transaction_type_improved(type_value, cleaned.get('amount', 0))
            else:
                # Infer from amount if not provided
                cleaned['transaction_type'] = 'credit' if cleaned.get('amount', 0) >= 0 else 'debit'
            
            # Extract reference number
            ref_value = self._extract_field_value(transaction_data, ['reference_number', 'reference', 'ref_number', 'check_number'])
            if ref_value:
                cleaned['reference_number'] = self._clean_reference_number(ref_value)
            
            # Extract category from CSV if available, otherwise auto-categorize
            category_value = self._extract_field_value(transaction_data, ['category', 'categories', 'transaction_category'])
            if category_value and category_value.lower() not in ['n/a', 'unknown', '']:
                cleaned['category'] = category_value.lower()
            elif cleaned.get('description'):
                cleaned['category'] = self._auto_categorize_improved(cleaned['description'])
            
            # Extract merchant name from description
            if cleaned.get('description'):
                cleaned['merchant_name'] = self._extract_merchant_name_improved(cleaned['description'])
            
            return cleaned
            
        except Exception as e:
            print(f"Error cleaning transaction data: {e}")
            return None
    
    def _extract_field_value(self, data: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """Extract field value from data using multiple possible field names"""
        for field_name in field_names:
            if field_name in data and data[field_name]:
                return str(data[field_name]).strip()
        return None
    
    def _clean_description(self, description: str) -> str:
        """Clean and normalize description"""
        if not description:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common prefixes
        prefixes_to_remove = ['POS ', 'VISA ', 'MC ', 'DEBIT ', 'CREDIT ', 'ATM ', 'CHECK ']
        for prefix in prefixes_to_remove:
            if cleaned.upper().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned[:500]  # Limit length
    
    def _clean_reference_number(self, ref: str) -> str:
        """Clean reference number"""
        if not ref:
            return ""
        
        # Remove non-alphanumeric characters except dashes
        cleaned = re.sub(r'[^\w\-]', '', str(ref))
        return cleaned[:100]  # Limit length
    
    def _parse_date_improved(self, date_str: str) -> Optional[datetime]:
        """Parse date string with improved logic"""
        if not date_str:
            return None
        
        # Common date formats with more variations
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%m/%d/%y',
            '%d/%m/%y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%Y %H:%M',
            '%d/%m/%Y %H:%M',
        ]
        
        # Clean the date string
        cleaned_date = date_str.strip()
        
        # Try each format
        for fmt in date_formats:
            try:
                return datetime.strptime(cleaned_date, fmt)
            except ValueError:
                continue
        
        # Try to extract date from complex strings
        try:
            # Look for date patterns in the string
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2}/\d{2}/\d{2})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, cleaned_date)
                if match:
                    date_part = match.group(1)
                    # Try to parse the extracted date
                    for fmt in date_formats[:8]:  # Use simpler formats for extracted dates
                        try:
                            return datetime.strptime(date_part, fmt)
                        except ValueError:
                            continue
        except Exception:
            pass
        
        return None
    
    def _parse_amount_improved(self, amount_str: str) -> Optional[float]:
        """Parse amount string with improved logic"""
        if not amount_str:
            return None
        
        try:
            # Clean the amount string
            cleaned = str(amount_str).strip()
            
            # Remove currency symbols and common formatting
            cleaned = re.sub(r'[\$€£¥₹]', '', cleaned)
            cleaned = re.sub(r'[,]', '', cleaned)
            
            # Handle parentheses notation for negative amounts
            if '(' in cleaned and ')' in cleaned:
                cleaned = cleaned.replace('(', '-').replace(')', '')
            
            # Remove any remaining non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d.\-]', '', cleaned)
            
            # Handle multiple decimal points (take the last one)
            if cleaned.count('.') > 1:
                parts = cleaned.split('.')
                cleaned = '.'.join(parts[:-1]) + '.' + parts[-1]
            
            # Parse as decimal first for better precision
            decimal_amount = Decimal(cleaned)
            return float(decimal_amount)
            
        except (ValueError, InvalidOperation, TypeError):
            return None
    
    def _normalize_transaction_type_improved(self, type_str: str, amount: float = 0) -> str:
        """Normalize transaction type with improved logic"""
        if not type_str:
            # Infer from amount
            return 'credit' if amount >= 0 else 'debit'
        
        type_lower = str(type_str).lower().strip()
        
        # More comprehensive type mapping
        debit_indicators = [
            'debit', 'deduction', 'withdrawal', 'out', '-', 'dr', 'debit card',
            'purchase', 'payment', 'charge', 'withdraw', 'debit transaction'
        ]
        
        credit_indicators = [
            'credit', 'deposit', 'addition', 'in', '+', 'cr', 'credit card',
            'refund', 'deposit', 'credit transaction', 'credit adjustment'
        ]
        
        if any(indicator in type_lower for indicator in debit_indicators):
            return 'debit'
        elif any(indicator in type_lower for indicator in credit_indicators):
            return 'credit'
        else:
            # Default to amount-based inference
            return 'credit' if amount >= 0 else 'debit'
    
    def _auto_categorize_improved(self, description: str) -> str:
        """Auto-categorize transaction with improved logic"""
        if not description:
            return 'other'
        
        desc_lower = description.lower()
        
        # Enhanced category keywords
        categories = {
            'food': [
                'restaurant', 'cafe', 'food', 'grocery', 'market', 'dining', 'starbucks', 
                'mcdonald', 'pizza', 'burger', 'subway', 'kfc', 'wendy', 'taco', 'chipotle',
                'domino', 'papa john', 'pizza hut', 'dunkin', 'coffee', 'bakery', 'deli'
            ],
            'gas': [
                'gas', 'fuel', 'shell', 'exxon', 'chevron', 'bp', 'mobil', 'sunoco',
                'marathon', 'speedway', 'circle k', '7-eleven', 'gas station', 'fuel station'
            ],
            'shopping': [
                'amazon', 'walmart', 'target', 'store', 'shop', 'retail', 'purchase',
                'best buy', 'home depot', 'lowes', 'costco', 'sam club', 'ikea', 'macy',
                'nordstrom', 'kohl', 'ross', 'marshalls', 'tj maxx', 'online', 'ecommerce'
            ],
            'travel': [
                'hotel', 'airline', 'flight', 'uber', 'lyft', 'taxi', 'parking', 'toll',
                'marriott', 'hilton', 'hyatt', 'airbnb', 'expedia', 'booking', 'orbitz',
                'southwest', 'delta', 'american airline', 'united', 'airport', 'car rental'
            ],
            'entertainment': [
                'movie', 'theater', 'netflix', 'spotify', 'game', 'entertainment',
                'hulu', 'disney', 'hbo', 'youtube', 'apple tv', 'amazon prime', 'xbox',
                'playstation', 'nintendo', 'concert', 'show', 'ticket', 'event'
            ],
            'healthcare': [
                'pharmacy', 'doctor', 'medical', 'hospital', 'health', 'cvs', 'walgreens',
                'rite aid', 'kroger pharmacy', 'walmart pharmacy', 'clinic', 'dental',
                'vision', 'optical', 'prescription', 'medicine', 'healthcare'
            ],
            'utilities': [
                'electric', 'water', 'gas bill', 'internet', 'phone', 'utility',
                'power', 'electricity', 'water bill', 'gas company', 'internet service',
                'cable', 'satellite', 'at&t', 'verizon', 'comcast', 'spectrum'
            ],
            'transportation': [
                'uber', 'lyft', 'taxi', 'parking', 'toll', 'bus', 'train', 'subway',
                'metro', 'transit', 'transportation', 'car', 'auto', 'vehicle'
            ],
            'insurance': [
                'insurance', 'geico', 'state farm', 'allstate', 'progressive', 'farmers',
                'liberty mutual', 'nationwide', 'auto insurance', 'home insurance',
                'health insurance', 'life insurance'
            ],
            'banking': [
                'bank', 'atm', 'check', 'deposit', 'withdrawal', 'transfer',
                'chase', 'bank of america', 'wells fargo', 'citibank', 'us bank'
            ]
        }
        
        for category, keywords in categories.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _extract_merchant_name_improved(self, description: str) -> str:
        """Extract and clean merchant name with improved logic"""
        if not description:
            return ""
        
        # If description contains multiple lines or is very long, extract the first part
        lines = description.split('\n')
        first_line = lines[0].strip()
        
        # If the first line looks like a merchant name (not too long, no special chars)
        if len(first_line) <= 100 and not re.search(r'[^\w\s\-\.&]', first_line):
            merchant_name = first_line
        else:
            # Use the original logic for complex descriptions
            merchant_name = description
        
        # Remove common prefixes and suffixes
        cleaned = merchant_name.upper()
        
        # Remove common transaction codes and prefixes
        prefixes_to_remove = [
            'POS ', 'VISA ', 'MC ', 'DEBIT ', 'CREDIT ', 'ATM ', 'CHECK ',
            'PURCHASE ', 'PAYMENT ', 'TRANSACTION ', 'CARD ', 'ONLINE '
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove trailing location codes and numbers
        cleaned = re.sub(r'\s+[A-Z]{2}\s*\d*$', '', cleaned)  # Remove state codes
        cleaned = re.sub(r'\s+\d{4,}$', '', cleaned)  # Remove trailing numbers
        cleaned = re.sub(r'\s+#\d+$', '', cleaned)  # Remove reference numbers
        
        # Remove common suffixes
        suffixes_to_remove = [
            ' INC', ' LLC', ' CORP', ' CORPORATION', ' COMPANY', ' CO',
            ' STORE', ' SHOP', ' MARKET', ' SUPERMARKET', ' GROCERY'
        ]
        
        for suffix in suffixes_to_remove:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        
        return cleaned.strip()[:255]  # Limit length
    
    def _clean_transaction_data_from_openai(self, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean and validate transaction data from OpenAI parsed JSON"""
        try:
            cleaned = {}
            
            # Extract fields directly from OpenAI parsed data
            if 'date' in transaction_data:
                cleaned['date'] = self._parse_date_improved(transaction_data['date'])
            
            if 'description' in transaction_data:
                cleaned['description'] = self._clean_description(str(transaction_data['description']))
            
            if 'amount' in transaction_data:
                # OpenAI should return amount as float, but validate
                amount = transaction_data['amount']
                if isinstance(amount, (int, float)):
                    cleaned['amount'] = float(amount)
                else:
                    cleaned['amount'] = self._parse_amount_improved(str(amount))
            
            if 'balance' in transaction_data:
                balance = transaction_data['balance']
                if isinstance(balance, (int, float)):
                    cleaned['balance'] = float(balance)
                else:
                    cleaned['balance'] = self._parse_amount_improved(str(balance))
            
            if 'transaction_type' in transaction_data:
                cleaned['transaction_type'] = self._normalize_transaction_type_improved(
                    transaction_data['transaction_type'], 
                    cleaned.get('amount', 0)
                )
            
            if 'reference_number' in transaction_data and transaction_data['reference_number']:
                cleaned['reference_number'] = self._clean_reference_number(str(transaction_data['reference_number']))
            
            # Validate required fields
            if not cleaned.get('date') or not cleaned.get('amount'):
                return None
            
            # Auto-categorize based on description
            if cleaned.get('description'):
                cleaned['category'] = self._auto_categorize_improved(cleaned['description'])
                cleaned['merchant_name'] = self._extract_merchant_name_improved(cleaned['description'])
            
            return cleaned
            
        except Exception as e:
            print(f"Error cleaning OpenAI parsed transaction data: {e}")
            return None
    
    def _clean_transaction_data(self, row_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean and validate transaction data from CSV row"""
        try:
            cleaned = {}
            
            # Map common CSV column names to our fields
            field_mappings = {
                'date': ['date', 'transaction_date', 'posted_date', 'trans_date'],
                'description': ['description', 'memo', 'merchant', 'payee', 'details'],
                'amount': ['amount', 'transaction_amount', 'debit', 'credit'],
                'balance': ['balance', 'running_balance', 'account_balance'],
                'transaction_type': ['type', 'transaction_type', 'debit_credit'],
                'reference_number': ['reference', 'ref_number', 'check_number', 'transaction_id']
            }
            
            # Extract and clean each field
            for field, possible_columns in field_mappings.items():
                value = None
                for col in possible_columns:
                    if col in row_data and row_data[col]:
                        value = row_data[col]
                        break
                
                if field == 'date' and value:
                    cleaned[field] = self._parse_date_improved(value)
                elif field in ['amount', 'balance'] and value:
                    cleaned[field] = self._parse_amount_improved(value)
                elif field == 'transaction_type' and value:
                    cleaned[field] = self._normalize_transaction_type_improved(value)
                elif value:
                    cleaned[field] = str(value)[:500]  # Limit string length
            
            # Validate required fields
            if not cleaned.get('date') or not cleaned.get('amount'):
                return None
            
            # Auto-categorize based on description
            if cleaned.get('description'):
                cleaned['category'] = self._auto_categorize_improved(cleaned['description'])
                cleaned['merchant_name'] = self._extract_merchant_name_improved(cleaned['description'])
            
            return cleaned
            
        except Exception as e:
            print(f"Error cleaning transaction data: {e}")
            return None
    

    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%m/%d/%y',
            '%d/%m/%y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float"""
        if not amount_str:
            return None
        
        try:
            # Remove currency symbols and commas
            cleaned = amount_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
            return float(cleaned)
        except ValueError:
            return None
    
    def _normalize_transaction_type(self, type_str: str) -> str:
        """Normalize transaction type"""
        type_lower = type_str.lower().strip()
        
        if type_lower in ['debit', 'deduction', 'withdrawal', 'out', '-']:
            return 'debit'
        elif type_lower in ['credit', 'deposit', 'addition', 'in', '+']:
            return 'credit'
        else:
            return 'debit'  # Default to debit
    
    def _auto_categorize(self, description: str) -> str:
        """Auto-categorize transaction based on description"""
        desc_lower = description.lower()
        
        # Define category keywords
        categories = {
            'food': ['restaurant', 'cafe', 'food', 'grocery', 'market', 'dining', 'starbucks', 'mcdonald', 'pizza'],
            'gas': ['gas', 'fuel', 'shell', 'exxon', 'chevron', 'bp', 'mobil'],
            'shopping': ['amazon', 'walmart', 'target', 'store', 'shop', 'retail', 'purchase'],
            'travel': ['hotel', 'airline', 'flight', 'uber', 'lyft', 'taxi', 'parking', 'toll'],
            'entertainment': ['movie', 'theater', 'netflix', 'spotify', 'game', 'entertainment'],
            'healthcare': ['pharmacy', 'doctor', 'medical', 'hospital', 'health', 'cvs', 'walgreens'],
            'utilities': ['electric', 'water', 'gas bill', 'internet', 'phone', 'utility'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _extract_merchant_name(self, description: str) -> str:
        """Extract and clean merchant name from description"""
        # Remove common prefixes and suffixes
        cleaned = description.upper()
        
        # Remove common transaction codes
        prefixes_to_remove = ['POS', 'VISA', 'MC', 'DEBIT', 'CREDIT', 'ATM', 'CHECK']
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove trailing location codes and numbers
        import re
        cleaned = re.sub(r'\s+[A-Z]{2}\s*\d*$', '', cleaned)  # Remove state codes
        cleaned = re.sub(r'\s+\d{4,}$', '', cleaned)  # Remove trailing numbers
        
        return cleaned.strip()[:255]  # Limit length
    
    def compare_transactions(self, user_id: int) -> ComparisonResult:
        """Compare ledger transactions with bank transactions"""
        # Get all transactions for user
        ledger_transactions = self.db.query(Transaction).filter(Transaction.user_id == user_id).all()
        bank_transactions = self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id).all()
        
        # Match transactions
        matched, ledger_only, bank_only = self._match_transactions(
            ledger_transactions, bank_transactions
        )
        
        # Calculate summary
        total_ledger = len(ledger_transactions)
        total_bank = len(bank_transactions)
        matched_count = len(matched)
        ledger_only_count = len(ledger_only)
        bank_only_count = len(bank_only)
        
        # Calculate match percentage
        total_comparisons = total_ledger + total_bank
        match_percentage = (matched_count * 2 / total_comparisons * 100) if total_comparisons > 0 else 0
        
        summary = {
            "total_ledger": total_ledger,
            "total_bank": total_bank,
            "matched_count": matched_count,
            "ledger_only_count": ledger_only_count,
            "bank_only_count": bank_only_count,
            "match_percentage": match_percentage
        }
        
        return ComparisonResult(
            matched=matched,
            ledger_only=ledger_only,
            bank_only=bank_only,
            summary=summary
        )
    
    def _match_transactions(
        self, 
        ledger_transactions: List[Transaction], 
        bank_transactions: List[BankTransaction]
    ) -> Tuple[List[TransactionMatch], List[TransactionMatch], List[TransactionMatch]]:
        """Match ledger transactions with bank transactions"""
        matched = []
        ledger_only = []
        bank_only = []
        
        # Create sets for efficient lookup
        matched_ledger_ids = set()
        matched_bank_ids = set()
        
        # Try to match transactions
        for ledger_tx in ledger_transactions:
            best_match = None
            best_confidence = 0
            
            for bank_tx in bank_transactions:
                if bank_tx.id in matched_bank_ids:
                    continue
                
                confidence = self._calculate_match_confidence(ledger_tx, bank_tx)
                
                if confidence > best_confidence and confidence > 0.7:  # Minimum confidence threshold
                    best_confidence = confidence
                    best_match = bank_tx
            
            if best_match:
                # Create match
                match = TransactionMatch(
                    ledger_transaction=ledger_tx,
                    bank_transaction=best_match,
                    match_type="matched",
                    confidence=best_confidence
                )
                matched.append(match)
                matched_ledger_ids.add(ledger_tx.id)
                matched_bank_ids.add(best_match.id)
            else:
                ledger_only.append(TransactionMatch(
                    ledger_transaction=ledger_tx,
                    bank_transaction=None,
                    match_type="ledger_only",
                    confidence=0
                ))
        
        # Add unmatched bank transactions
        for bank_tx in bank_transactions:
            if bank_tx.id not in matched_bank_ids:
                bank_only.append(TransactionMatch(
                    ledger_transaction=None,
                    bank_transaction=bank_tx,
                    match_type="bank_only",
                    confidence=0
                ))
        
        return matched, ledger_only, bank_only
    
    def _calculate_match_confidence(self, ledger_tx: Transaction, bank_tx: BankTransaction) -> float:
        """Calculate confidence score for transaction match"""
        confidence = 0.0
        
        # Amount matching (highest weight)
        if ledger_tx.amount is not None and bank_tx.amount is not None:
            if abs(ledger_tx.amount - bank_tx.amount) < 0.01:  # Exact amount match
                confidence += 0.4
            elif abs(ledger_tx.amount - bank_tx.amount) < 0.1:  # Close amount match
                confidence += 0.2
        
        # Date matching
        if ledger_tx.transaction_date and bank_tx.date:
            date_diff = abs((ledger_tx.transaction_date - bank_tx.date).days)
            if date_diff == 0:  # Same date
                confidence += 0.3
            elif date_diff <= 1:  # Within 1 day
                confidence += 0.2
            elif date_diff <= 3:  # Within 3 days
                confidence += 0.1
        
        # Description matching
        if ledger_tx.description and bank_tx.description:
            desc_similarity = self._calculate_string_similarity(
                ledger_tx.description.lower(), 
                bank_tx.description.lower()
            )
            confidence += desc_similarity * 0.2
        
        # Category matching
        if ledger_tx.category and bank_tx.category:
            if ledger_tx.category.lower() == bank_tx.category.lower():
                confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def detect_and_merge_duplicates(self, user_id: int, batch_id: str = None) -> Dict[str, Any]:
        """Detect and merge duplicate transactions using AI-powered matching"""
        # Get transactions for the user
        query = self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id)
        if batch_id:
            query = query.filter(BankTransaction.upload_batch_id == batch_id)
        
        transactions = query.all()
        
        # Group transactions by potential duplicates
        duplicate_groups = self._group_potential_duplicates(transactions)
        
        # Process each group with AI analysis
        merged_transactions = []
        duplicate_summary = {
            "total_transactions": len(transactions),
            "duplicate_groups_found": len(duplicate_groups),
            "transactions_merged": 0,
            "transactions_deleted": 0,
            "groups_processed": []
        }
        
        for group_id, group_transactions in duplicate_groups.items():
            if len(group_transactions) > 1:
                # Use AI to analyze if these are truly duplicates
                ai_analysis = self._analyze_duplicates_with_ai(group_transactions)
                
                if ai_analysis["are_duplicates"]:
                    # Merge the duplicates
                    merged_tx = self._merge_duplicate_transactions(group_transactions)
                    merged_transactions.append(merged_tx)
                    
                    # Delete the original duplicates
                    for tx in group_transactions:
                        self.db.delete(tx)
                    
                    duplicate_summary["transactions_merged"] += len(group_transactions)
                    duplicate_summary["transactions_deleted"] += len(group_transactions) - 1
                    
                    duplicate_summary["groups_processed"].append({
                        "group_id": group_id,
                        "transactions_count": len(group_transactions),
                        "ai_confidence": ai_analysis["confidence"],
                        "ai_reasoning": ai_analysis["reasoning"],
                        "merged_transaction_id": merged_tx.id
                    })
        
        self.db.commit()
        
        return {
            "summary": duplicate_summary,
            "merged_transactions": [self._transaction_to_dict(tx) for tx in merged_transactions]
        }
    
    def _group_potential_duplicates(self, transactions: List[BankTransaction]) -> Dict[str, List[BankTransaction]]:
        """Group transactions that might be duplicates based on basic criteria"""
        groups = defaultdict(list)
        
        for tx in transactions:
            # Create a key based on amount, date, and description similarity
            amount_key = f"{tx.amount:.2f}" if tx.amount else "0.00"
            date_key = tx.date.strftime("%Y-%m-%d") if tx.date else "unknown"
            
            # Clean description for grouping
            clean_desc = self._clean_description_for_grouping(tx.description or "")
            
            # Create group key
            group_key = f"{amount_key}_{date_key}_{clean_desc[:50]}"
            groups[group_key].append(tx)
        
        # Filter out groups with only one transaction
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def _clean_description_for_grouping(self, description: str) -> str:
        """Clean description for grouping purposes"""
        if not description:
            return ""
        
        # Remove common prefixes and normalize
        cleaned = description.upper().strip()
        
        # Remove common transaction codes
        prefixes_to_remove = ['POS', 'VISA', 'MC', 'DEBIT', 'CREDIT', 'ATM', 'CHECK']
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove trailing location codes and numbers
        cleaned = re.sub(r'\s+[A-Z]{2}\s*\d*$', '', cleaned)
        cleaned = re.sub(r'\s+\d{4,}$', '', cleaned)
        
        return cleaned.strip()
    
    def _analyze_duplicates_with_ai(self, transactions: List[BankTransaction]) -> Dict[str, Any]:
        """Use AI to analyze if transactions are truly duplicates"""
        if len(transactions) < 2:
            return {"are_duplicates": False, "confidence": 0.0, "reasoning": "Not enough transactions"}
        
        # Prepare transaction data for AI analysis
        tx_data = []
        for tx in transactions:
            tx_data.append({
                "id": tx.id,
                "date": tx.date.isoformat() if tx.date else None,
                "description": tx.description,
                "amount": tx.amount,
                "category": tx.category,
                "merchant_name": tx.merchant_name
            })
        
        # Create AI prompt
        prompt = self._create_duplicate_analysis_prompt(tx_data)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst. Analyze the given transactions and determine if they are duplicates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Parse AI response
            analysis = self._parse_ai_duplicate_analysis(ai_response)
            return analysis
            
        except Exception as e:
            # Fallback to basic analysis if AI fails
            return self._fallback_duplicate_analysis(transactions)
    
    def _create_duplicate_analysis_prompt(self, transactions: List[Dict[str, Any]]) -> str:
        """Create prompt for AI duplicate analysis"""
        prompt = f"""
Analyze the following {len(transactions)} transactions and determine if they are duplicates:

"""
        
        for i, tx in enumerate(transactions, 1):
            prompt += f"""
Transaction {i}:
- ID: {tx['id']}
- Date: {tx['date']}
- Description: {tx['description']}
- Amount: {tx['amount']}
- Category: {tx['category']}
- Merchant: {tx['merchant_name']}
"""
        
        prompt += """
Please analyze these transactions and respond in the following JSON format:
{
    "are_duplicates": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why these are or are not duplicates",
    "recommended_action": "merge" or "keep_separate"
}

Consider:
1. Exact matches in amount, date, and description
2. Similar descriptions that might be the same merchant
3. Timing differences (same day vs different days)
4. Amount variations that might be fees or adjustments
5. Different categories that might be auto-categorized differently
"""
        
        return prompt
    
    def _parse_ai_duplicate_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response for duplicate analysis"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    "are_duplicates": analysis.get("are_duplicates", False),
                    "confidence": analysis.get("confidence", 0.0),
                    "reasoning": analysis.get("reasoning", "No reasoning provided"),
                    "recommended_action": analysis.get("recommended_action", "keep_separate")
                }
        except Exception:
            pass
        
        # Fallback parsing
        return {
            "are_duplicates": "duplicate" in ai_response.lower() or "merge" in ai_response.lower(),
            "confidence": 0.5,
            "reasoning": ai_response,
            "recommended_action": "merge" if "duplicate" in ai_response.lower() else "keep_separate"
        }
    
    def _fallback_duplicate_analysis(self, transactions: List[BankTransaction]) -> Dict[str, Any]:
        """Fallback analysis when AI fails"""
        if len(transactions) != 2:
            return {"are_duplicates": False, "confidence": 0.0, "reasoning": "Can only analyze pairs"}
        
        tx1, tx2 = transactions
        
        # Check for exact matches
        exact_match = (
            tx1.amount == tx2.amount and
            tx1.date == tx2.date and
            tx1.description == tx2.description
        )
        
        if exact_match:
            return {
                "are_duplicates": True,
                "confidence": 1.0,
                "reasoning": "Exact match on amount, date, and description",
                "recommended_action": "merge"
            }
        
        # Check for close matches
        amount_match = abs(tx1.amount - tx2.amount) < 0.01 if tx1.amount and tx2.amount else False
        date_match = tx1.date == tx2.date
        desc_similarity = self._calculate_string_similarity(
            tx1.description or "", tx2.description or ""
        )
        
        if amount_match and date_match and desc_similarity > 0.8:
            return {
                "are_duplicates": True,
                "confidence": 0.9,
                "reasoning": f"Close match: amount={amount_match}, date={date_match}, desc_similarity={desc_similarity:.2f}",
                "recommended_action": "merge"
            }
        
        return {
            "are_duplicates": False,
            "confidence": 0.0,
            "reasoning": "No significant similarity found",
            "recommended_action": "keep_separate"
        }
    
    def _merge_duplicate_transactions(self, transactions: List[BankTransaction]) -> BankTransaction:
        """Merge duplicate transactions into a single transaction"""
        if not transactions:
            raise ValueError("No transactions to merge")
        
        # Use the first transaction as the base
        base_tx = transactions[0]
        
        # Merge data from all transactions
        merged_data = {
            "user_id": base_tx.user_id,
            "upload_batch_id": base_tx.upload_batch_id,
            "date": base_tx.date,
            "amount": base_tx.amount,
            "balance": base_tx.balance,
            "transaction_type": base_tx.transaction_type,
            "reference_number": base_tx.reference_number,
            "category": base_tx.category,
            "merchant_name": base_tx.merchant_name,
            "is_matched": base_tx.is_matched,
            "matched_transaction_id": base_tx.matched_transaction_id,
            "match_confidence": base_tx.match_confidence,
            "match_type": base_tx.match_type
        }
        
        # Combine descriptions if they differ
        descriptions = [tx.description for tx in transactions if tx.description]
        if len(set(descriptions)) > 1:
            merged_data["description"] = " | ".join(set(descriptions))
        
        # Use the best category (non-null, non-N/A)
        categories = [tx.category for tx in transactions if tx.category and tx.category != "N/A"]
        if categories:
            merged_data["category"] = categories[0]
        
        # Use the best merchant name
        merchant_names = [tx.merchant_name for tx in transactions if tx.merchant_name and tx.merchant_name != "Unknown"]
        if merchant_names:
            merged_data["merchant_name"] = merchant_names[0]
        
        # Create new merged transaction
        merged_tx = BankTransaction(**merged_data)
        self.db.add(merged_tx)
        self.db.flush()  # Get the ID
        
        return merged_tx
    
    def _transaction_to_dict(self, tx: BankTransaction) -> Dict[str, Any]:
        """Convert transaction to dictionary for response"""
        return {
            "id": tx.id,
            "user_id": tx.user_id,
            "date": tx.date.isoformat() if tx.date else None,
            "description": tx.description,
            "amount": tx.amount,
            "category": tx.category,
            "merchant_name": tx.merchant_name,
            "created_at": tx.created_at.isoformat() if tx.created_at else None
        }
    
    def improved_match_transactions(self, user_id: int) -> ComparisonResult:
        """Improved transaction matching with AI-powered analysis"""
        # Get all transactions for user
        ledger_transactions = self.db.query(Transaction).filter(Transaction.user_id == user_id).all()
        bank_transactions = self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id).all()
        
        # First, detect and merge duplicates
        duplicate_result = self.detect_and_merge_duplicates(user_id)
        
        # Refresh bank transactions after merging
        bank_transactions = self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id).all()
        
        # Use AI-enhanced matching
        matched, ledger_only, bank_only = self._ai_enhanced_match_transactions(
            ledger_transactions, bank_transactions
        )
        
        # Calculate summary
        total_ledger = len(ledger_transactions)
        total_bank = len(bank_transactions)
        matched_count = len(matched)
        ledger_only_count = len(ledger_only)
        bank_only_count = len(bank_only)
        
        # Calculate match percentage
        total_comparisons = total_ledger + total_bank
        match_percentage = (matched_count * 2 / total_comparisons * 100) if total_comparisons > 0 else 0
        
        summary = {
            "total_ledger": total_ledger,
            "total_bank": total_bank,
            "matched_count": matched_count,
            "ledger_only_count": ledger_only_count,
            "bank_only_count": bank_only_count,
            "match_percentage": match_percentage,
            "duplicates_merged": duplicate_result["summary"]["transactions_merged"]
        }
        
        return ComparisonResult(
            matched=matched,
            ledger_only=ledger_only,
            bank_only=bank_only,
            summary=summary
        )
    
    def _ai_enhanced_match_transactions(
        self, 
        ledger_transactions: List[Transaction], 
        bank_transactions: List[BankTransaction]
    ) -> Tuple[List[TransactionMatch], List[TransactionMatch], List[TransactionMatch]]:
        """AI-enhanced transaction matching"""
        matched = []
        ledger_only = []
        bank_only = []
        
        # Create sets for efficient lookup
        matched_ledger_ids = set()
        matched_bank_ids = set()
        
        # Try to match transactions with AI assistance
        for ledger_tx in ledger_transactions:
            best_match = None
            best_confidence = 0
            
            for bank_tx in bank_transactions:
                if bank_tx.id in matched_bank_ids:
                    continue
                
                # Use AI to calculate match confidence
                confidence = self._ai_calculate_match_confidence(ledger_tx, bank_tx)
                
                if confidence > best_confidence and confidence > 0.6:  # Lowered threshold for AI
                    best_confidence = confidence
                    best_match = bank_tx
            
            if best_match:
                # Create match
                match = TransactionMatch(
                    ledger_transaction=ledger_tx,
                    bank_transaction=best_match,
                    match_type="matched",
                    confidence=best_confidence
                )
                matched.append(match)
                matched_ledger_ids.add(ledger_tx.id)
                matched_bank_ids.add(best_match.id)
            else:
                ledger_only.append(TransactionMatch(
                    ledger_transaction=ledger_tx,
                    bank_transaction=None,
                    match_type="ledger_only",
                    confidence=0
                ))
        
        # Add unmatched bank transactions
        for bank_tx in bank_transactions:
            if bank_tx.id not in matched_bank_ids:
                bank_only.append(TransactionMatch(
                    ledger_transaction=None,
                    bank_transaction=bank_tx,
                    match_type="bank_only",
                    confidence=0
                ))
        
        return matched, ledger_only, bank_only
    
    def _ai_calculate_match_confidence(self, ledger_tx: Transaction, bank_tx: BankTransaction) -> float:
        """AI-enhanced confidence calculation for transaction matching"""
        # First, calculate basic confidence
        basic_confidence = self._calculate_match_confidence(ledger_tx, bank_tx)
        
        # If basic confidence is high enough, use AI for final verification
        if basic_confidence > 0.5:
            ai_confidence = self._ai_verify_match(ledger_tx, bank_tx)
            # Combine basic and AI confidence
            return (basic_confidence * 0.6) + (ai_confidence * 0.4)
        
        return basic_confidence
    
    def _ai_verify_match(self, ledger_tx: Transaction, bank_tx: BankTransaction) -> float:
        """Use AI to verify if two transactions are a match"""
        try:
            prompt = f"""
Analyze if these two transactions are the same transaction:

Transaction 1 (Ledger):
- Date: {ledger_tx.transaction_date}
- Amount: {ledger_tx.amount}
- Description: {ledger_tx.description}
- Category: {ledger_tx.category}
- Merchant: {ledger_tx.merchant_name}

Transaction 2 (Bank):
- Date: {bank_tx.date}
- Amount: {bank_tx.amount}
- Description: {bank_tx.description}
- Category: {bank_tx.category}
- Merchant: {bank_tx.merchant_name}

Respond with a confidence score between 0.0 and 1.0, where:
0.0 = Definitely not the same transaction
1.0 = Definitely the same transaction

Consider:
- Amount differences (fees, adjustments)
- Date differences (processing delays)
- Description variations (different formats)
- Category differences (auto-categorization)
- Merchant name variations

Response format: Just the number (e.g., 0.85)
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial transaction matching expert. Provide confidence scores for transaction matches."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Parse confidence score
            try:
                confidence = float(ai_response)
                return max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            except ValueError:
                return 0.5  # Default if parsing fails
                
        except Exception:
            return 0.5  # Default if AI fails

    def generate_sample_bank_transactions(self, user_id: int) -> CSVUploadResponse:
        """Generate sample bank transactions for demonstration"""
        batch_id = str(uuid.uuid4())
        
        # Clear existing bank transactions for this user to avoid duplication
        self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id).delete()
        self.db.commit()
        
        # Sample bank transactions data (BankTransaction model)
        sample_bank_transactions = [
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 15),
                "description": "SAFEWAY GROCERY PURCHASE",
                "amount": 45.67,
                "balance": 1234.56,
                "transaction_type": "debit",
                "reference_number": "123456",
                "category": "food",
                "merchant_name": "SAFEWAY"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 16),
                "description": "SALARY DEPOSIT",
                "amount": 2500.00,
                "balance": 3734.56,
                "transaction_type": "credit",
                "reference_number": None,
                "category": "income",
                "merchant_name": "EMPLOYER CORP"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 17),
                "description": "SHELL GAS STATION",
                "amount": 35.89,
                "balance": 3698.67,
                "transaction_type": "debit",
                "reference_number": "789012",
                "category": "gas",
                "merchant_name": "SHELL"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 18),
                "description": "AMAZON.COM ONLINE PURCHASE",
                "amount": 89.99,
                "balance": 3608.68,
                "transaction_type": "debit",
                "reference_number": "345678",
                "category": "shopping",
                "merchant_name": "AMAZON"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 19),
                "description": "CHIPOTLE RESTAURANT",
                "amount": 67.45,
                "balance": 3541.23,
                "transaction_type": "debit",
                "reference_number": "901234",
                "category": "food",
                "merchant_name": "CHIPOTLE"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 20),
                "description": "NETFLIX SUBSCRIPTION",
                "amount": 15.99,
                "balance": 3525.24,
                "transaction_type": "debit",
                "reference_number": "567890",
                "category": "entertainment",
                "merchant_name": "NETFLIX"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 21),
                "description": "CVS PHARMACY PURCHASE",
                "amount": 23.50,
                "balance": 3501.74,
                "transaction_type": "debit",
                "reference_number": "234567",
                "category": "healthcare",
                "merchant_name": "CVS"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 22),
                "description": "ELECTRIC COMPANY BILL PAYMENT",
                "amount": 125.00,
                "balance": 3376.74,
                "transaction_type": "debit",
                "reference_number": "890123",
                "category": "utilities",
                "merchant_name": "ELECTRIC COMPANY"
            }
        ]
        
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        # Create bank transactions from sample data
        for transaction_data in sample_bank_transactions:
            try:
                # Create bank transaction (BankTransaction model)
                bank_tx = BankTransaction(**transaction_data)
                self.db.add(bank_tx)
                successful_imports += 1
                
            except Exception as e:
                failed_imports += 1
                errors.append(f"Sample bank transaction error: {str(e)}")
        
        self.db.commit()
        
        return CSVUploadResponse(
            batch_id=batch_id,
            total_transactions=len(sample_bank_transactions),
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            errors=errors[:10]  # Limit to first 10 errors
        )

    def generate_sample_comparison_data(self, user_id: int) -> ComparisonResult:
        """Generate sample comparison data with distinct ledger and bank transactions where some match"""
        
        # Clear existing sample data for this user to avoid duplication
        self.db.query(Transaction).filter(Transaction.user_id == user_id).delete()
        self.db.query(BankTransaction).filter(BankTransaction.user_id == user_id).delete()
        self.db.commit()
        
        # Create sample ledger transactions (5 transactions)
        sample_ledger_transactions = [
            {
                "user_id": user_id,
                "merchant_name": "SAFEWAY",
                "amount": 45.67,
                "currency": "USD",
                "transaction_date": datetime(2024, 1, 15),
                "category": "food",
                "description": "Grocery purchase at Safeway",
                "is_processed": True
            },
            {
                "user_id": user_id,
                "merchant_name": "SHELL",
                "amount": 35.89,
                "currency": "USD",
                "transaction_date": datetime(2024, 1, 17),
                "category": "gas",
                "description": "Gas station purchase",
                "is_processed": True
            },
            {
                "user_id": user_id,
                "merchant_name": "AMAZON",
                "amount": 89.99,
                "currency": "USD",
                "transaction_date": datetime(2024, 1, 18),
                "category": "shopping",
                "description": "Online purchase from Amazon",
                "is_processed": True
            },
            {
                "user_id": user_id,
                "merchant_name": "CHIPOTLE",
                "amount": 67.45,
                "currency": "USD",
                "transaction_date": datetime(2024, 1, 19),
                "category": "food",
                "description": "Restaurant dining at Chipotle",
                "is_processed": True
            },
            {
                "user_id": user_id,
                "merchant_name": "NETFLIX",
                "amount": 15.99,
                "currency": "USD",
                "transaction_date": datetime(2024, 1, 20),
                "category": "entertainment",
                "description": "Netflix subscription payment",
                "is_processed": True
            }
        ]
        
        # Create ledger transactions
        for ledger_data in sample_ledger_transactions:
            ledger_tx = Transaction(**ledger_data)
            self.db.add(ledger_tx)
        
        # Create sample bank transactions (8 transactions) - different from ledger
        batch_id = str(uuid.uuid4())
        sample_bank_transactions = [
            # These 3 should match with ledger transactions (same amount, date, similar description)
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 15),
                "description": "SAFEWAY GROCERY PURCHASE",
                "amount": 45.67,
                "balance": 1234.56,
                "transaction_type": "debit",
                "reference_number": "123456",
                "category": "food",
                "merchant_name": "SAFEWAY"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 17),
                "description": "SHELL GAS STATION",
                "amount": 35.89,
                "balance": 3698.67,
                "transaction_type": "debit",
                "reference_number": "789012",
                "category": "gas",
                "merchant_name": "SHELL"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 18),
                "description": "AMAZON.COM ONLINE PURCHASE",
                "amount": 89.99,
                "balance": 3608.68,
                "transaction_type": "debit",
                "reference_number": "345678",
                "category": "shopping",
                "merchant_name": "AMAZON"
            },
            # These 5 are bank-only transactions (not in ledger)
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 16),
                "description": "SALARY DEPOSIT",
                "amount": 2500.00,
                "balance": 3734.56,
                "transaction_type": "credit",
                "reference_number": None,
                "category": "income",
                "merchant_name": "EMPLOYER CORP"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 19),
                "description": "CHIPOTLE RESTAURANT",
                "amount": 67.45,
                "balance": 3541.23,
                "transaction_type": "debit",
                "reference_number": "901234",
                "category": "food",
                "merchant_name": "CHIPOTLE"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 20),
                "description": "NETFLIX SUBSCRIPTION",
                "amount": 15.99,
                "balance": 3525.24,
                "transaction_type": "debit",
                "reference_number": "567890",
                "category": "entertainment",
                "merchant_name": "NETFLIX"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 21),
                "description": "CVS PHARMACY PURCHASE",
                "amount": 23.50,
                "balance": 3501.74,
                "transaction_type": "debit",
                "reference_number": "234567",
                "category": "healthcare",
                "merchant_name": "CVS"
            },
            {
                "user_id": user_id,
                "upload_batch_id": batch_id,
                "date": datetime(2024, 1, 22),
                "description": "ELECTRIC COMPANY BILL PAYMENT",
                "amount": 125.00,
                "balance": 3376.74,
                "transaction_type": "debit",
                "reference_number": "890123",
                "category": "utilities",
                "merchant_name": "ELECTRIC COMPANY"
            }
        ]
        
        # Create bank transactions
        for bank_data in sample_bank_transactions:
            bank_tx = BankTransaction(**bank_data)
            self.db.add(bank_tx)
        
        self.db.commit()
        
        # Now perform comparison
        return self.compare_transactions(user_id)
