"""
MongoDB connection and GridFS management for Gender Inference System
"""

from pymongo import MongoClient
from typing import Optional, Dict, List
from datetime import datetime
import gridfs
from bson import ObjectId
import os
import tempfile

class MongoDBConnection:
    """MongoDB connection manager with GridFS support"""
    
    def __init__(self, uri: str = None):
        """
        Initialize MongoDB connection
        
        Args:
            uri: MongoDB connection string
        """
        if uri is None:
            # Use your MongoDB Atlas connection string
            uri = "mongodb+srv://zhangyichi10_db_user:jmIjiqELy26PUVlh@gender.wg4opvd.mongodb.net/"
        
        self.client = MongoClient(uri)
        self.db = self.client['gender']  # Your database name
        
        # Collections
        self.athletes = self.db['gender']  # Your collection name
        self.gender_overrides = self.db['gender_overrides']
        self.inference_logs = self.db['inference_logs']
        
        # Initialize GridFS
        self.fs = gridfs.GridFS(self.db)
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Unique index on athlete_id
            self.athletes.create_index('athlete_id', unique=True)
            self.gender_overrides.create_index('athlete_id', unique=True)
            
            # Index for queries
            self.athletes.create_index('explicit_gender')
            self.athletes.create_index('inferred_gender')
            self.inference_logs.create_index('athlete_id')
            self.inference_logs.create_index('timestamp')
        except:
            pass  # Indexes might already exist
    
    def upload_image_to_gridfs(self, image_path: str, athlete_id: str) -> str:
        """
        Upload image to GridFS and return file_id
        
        Args:
            image_path: Local path to image file
            athlete_id: Athlete ID for metadata
            
        Returns:
            GridFS file_id as string
        """
        try:
            with open(image_path, 'rb') as f:
                file_id = self.fs.put(
                    f.read(),
                    filename=os.path.basename(image_path),
                    athlete_id=athlete_id,
                    content_type='image/jpeg'
                )
                return str(file_id)
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None
    
    def get_image_from_gridfs(self, file_id: str) -> Optional[str]:
        """
        Download image from GridFS to temporary file
        
        Args:
            file_id: GridFS file_id
            
        Returns:
            Path to temporary file or None
        """
        try:
            grid_file = self.fs.get(ObjectId(file_id))
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(grid_file.read())
                return tmp.name
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


class MongoDBOverrideStore:
    """MongoDB-backed implementation of OverrideStore"""
    
    def __init__(self, db_connection: MongoDBConnection):
        self.db = db_connection
        self.collection = db_connection.gender_overrides
    
    def get_override(self, athlete_id: str) -> Optional[str]:
        """Get stored gender override from MongoDB"""
        doc = self.collection.find_one({'athlete_id': athlete_id})
        if doc:
            return doc.get('gender')
        return None
    
    def set_override(self, athlete_id: str, gender: str):
        """Store gender override in MongoDB"""
        normalized_gender = gender.lower().strip()
        if normalized_gender not in ['male', 'female']:
            raise ValueError(f"Invalid gender: {gender}")
        
        self.collection.update_one(
            {'athlete_id': athlete_id},
            {
                '$set': {
                    'gender': normalized_gender,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
    
    def clear_override(self, athlete_id: str):
        """Remove gender override from MongoDB"""
        self.collection.delete_one({'athlete_id': athlete_id})


class AthleteRepository:
    """Repository pattern for athlete data access"""
    
    def __init__(self, db_connection: MongoDBConnection):
        self.db = db_connection
        self.collection = db_connection.athletes
    
    def get_athlete(self, athlete_id: str) -> Optional[Dict]:
        """Get athlete by ID"""
        return self.collection.find_one({'athlete_id': athlete_id})
    
    def get_athletes_needing_inference(self) -> List[Dict]:
        """Get all athletes without gender"""
        return list(self.collection.find({
            '$and': [
                {'$or': [
                    {'explicit_gender': None},
                    {'explicit_gender': {'$exists': False}}
                ]},
                {'$or': [
                    {'inferred_gender': {'$exists': False}},
                    {'inferred_gender': None}
                ]}
            ]
        }))
    
    def update_inferred_gender(self, athlete_id: str, 
                             gender: str, 
                             confidence: float,
                             signal_attribution: Dict):
        """Update athlete with inferred gender"""
        self.collection.update_one(
            {'athlete_id': athlete_id},
            {
                '$set': {
                    'inferred_gender': gender,
                    'inference_confidence': confidence,
                    'signal_attribution': signal_attribution,
                    'inference_timestamp': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    def get_all_athletes(self) -> List[Dict]:
        """Get all athletes"""
        return list(self.collection.find())