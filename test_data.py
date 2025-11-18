"""
Mock data extracted from MongoDB
This simulates the data structure that would come from MongoDB queries
"""

# Mock athlete data from MongoDB
# In production, this would be fetched from MongoDB using queries like:
# db.athletes.find({...})

MOCK_ATHLETES = [
    {
        'athlete_id': 'athlete_001',
        'name': 'Michael Johnson',
        'sport_team': 'UCLA Football',
        'profile_image': './data/image1.jpg',  # Path to image file
        'explicit_gender': None,  # No explicit gender override
    },
    {
        'athlete_id': 'athlete_002',
        'name': 'Alex Morgan',
        'sport_team': 'US Women\'s Soccer',
        'profile_image': './data/image2.jpg',
        'explicit_gender': None,
    },
    {
        'athlete_id': 'athlete_003',
        'name': 'Alex Wilson',
        'sport_team': 'Track and Field',
        'profile_image': './data/image3.jpg',
        'explicit_gender': None,  # Ambiguous name + mixed sport - will need image
    },
    {
        'athlete_id': 'athlete_004',
        'name': 'Jordan Lee',
        'sport_team': 'Swimming',
        'profile_image': './data/image4.jpg',
        'explicit_gender': None,
    },
    {
        'athlete_id': 'athlete_005',
        'name': 'Sarah Johnson',
        'sport_team': 'Men\'s Basketball Team',
        'profile_image': './data/image5.jpg',
        'explicit_gender': None,  # Mis-assigned team - explicit gender in team name should override
    },
    {
        'athlete_id': 'athlete_006',
        'name': 'Chris Taylor',
        'sport_team': 'Tennis Club',
        'profile_image': None,  # No image available
        'explicit_gender': None,
    },
    {
        'athlete_id': 'athlete_007',
        'name': 'Test User',
        'sport_team': 'Soccer',
        'profile_image': None,
        'explicit_gender': 'female',  # Explicit gender provided - should be stored as override
    },
    {
        'athlete_id': 'athlete_008',
        'name': 'Emma Davis',
        'sport_team': 'Volleyball',
        'profile_image': './data/image6.jpg',
        'explicit_gender': None,
    },
]

# Example MongoDB query structure (commented for reference):
"""
# MongoDB query example:
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['sports_db']
collection = db['athletes']

# Query to fetch athletes needing gender inference
athletes = collection.find({
    'gender': {'$exists': False},  # No gender field yet
    'profile_image': {'$exists': True}  # Has profile image
})

# Convert MongoDB documents to our format
mock_athletes = []
for athlete in athletes:
    mock_athletes.append({
        'athlete_id': str(athlete['_id']),
        'name': athlete.get('name', ''),
        'sport_team': athlete.get('sport_team', ''),
        'profile_image': athlete.get('profile_image_path', None),
        'explicit_gender': athlete.get('explicit_gender', None),
    })
"""

