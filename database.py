"""
MongoDB database operations for Change of Control Analyzer
"""

import os
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_CONN_STR = os.getenv("MONGO_CONN_STR")

# Singleton client
_client = None
_db = None


def get_db():
    """Get MongoDB database connection"""
    global _client, _db
    
    if _db is None:
        if not MONGO_CONN_STR:
            raise ValueError("MONGO_CONN_STR environment variable not set")
        
        try:
            _client = MongoClient(MONGO_CONN_STR, serverSelectionTimeoutMS=5000)
            # Test connection
            _client.admin.command('ping')
            _db = _client['change_of_control']
            print("✅ MongoDB connected successfully")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise
    
    return _db


def save_analysis_result(result: Dict) -> bool:
    """
    Save or update analysis result in MongoDB
    
    Args:
        result: Dictionary containing company analysis data
        
    Returns:
        True if saved/updated, False if duplicate (same percent)
    """
    try:
        db = get_db()
        collection = db['analyses']
        
        # Extract required fields
        ticker = result.get('ticker')
        company_name = result.get('company_name')
        percentage = result.get('percentage')
        
        if not ticker or percentage is None or percentage == 0:
            return False
        
        # Check if company exists
        existing = collection.find_one({'ticker': ticker})
        
        if existing:
            # Check if percentage is the same (within small tolerance)
            if abs(existing.get('percentage', 0) - percentage) < 0.0001:
                print(f"⏭️  Skipping {ticker} - same percentage")
                return False
            
            # Update with new data
            collection.update_one(
                {'ticker': ticker},
                {
                    '$set': {
                        'company_name': company_name,
                        'percentage': percentage,
                        'total_payments': result.get('total_payments'),
                        'market_cap': result.get('market_cap'),
                        'def14a_url': result.get('def14a_url'),
                        'filing_date': result.get('filing_date'),
                        'payouts': result.get('payouts', []),
                        'updated_at': result.get('filing_date')
                    }
                }
            )
            print(f"🔄 Updated {ticker} with new percentage: {percentage:.4f}%")
            return True
        else:
            # Insert new record
            document = {
                'ticker': ticker,
                'company_name': company_name,
                'percentage': percentage,
                'total_payments': result.get('total_payments'),
                'market_cap': result.get('market_cap'),
                'def14a_url': result.get('def14a_url'),
                'filing_date': result.get('filing_date'),
                'payouts': result.get('payouts', []),
                'created_at': result.get('filing_date')
            }
            collection.insert_one(document)
            print(f"💾 Saved new record for {ticker}: {percentage:.4f}%")
            return True
            
    except Exception as e:
        print(f"❌ Error saving to MongoDB: {e}")
        return False


def get_top_companies(limit: int = 10) -> List[Dict]:
    """
    Get top companies by percentage
    
    Args:
        limit: Number of top companies to return
        
    Returns:
        List of company records sorted by percentage (highest first)
    """
    try:
        db = get_db()
        collection = db['analyses']
        
        # Get top companies sorted by percentage
        results = collection.find(
            {},
            {
                '_id': 0,
                'company_name': 1,
                'ticker': 1,
                'percentage': 1,
                'def14a_url': 1,
                'total_payments': 1,
                'market_cap': 1,
                'filing_date': 1
            }
        ).sort('percentage', DESCENDING).limit(limit)
        
        return list(results)
        
    except Exception as e:
        print(f"❌ Error fetching top companies: {e}")
        return []


def test_connection() -> bool:
    """Test MongoDB connection"""
    try:
        db = get_db()
        db.command('ping')
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    if test_connection():
        print("✅ Database connection test successful")
        
        # Test getting top companies
        top = get_top_companies(5)
        print(f"\nTop 5 companies:")
        for i, company in enumerate(top, 1):
            print(f"{i}. {company.get('company_name')} ({company.get('ticker')}): {company.get('percentage'):.4f}%")
    else:
        print("❌ Database connection test failed")

