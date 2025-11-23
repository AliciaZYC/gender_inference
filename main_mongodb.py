"""
Main application with MongoDB and GridFS integration - FIXED VERSION
"""

import os
import tempfile
from database import MongoDBConnection, MongoDBOverrideStore, AthleteRepository
from main import GenderInferenceAgent

class MongoGenderInferenceAgent(GenderInferenceAgent):
    """Extended agent with GridFS support"""
    
    def __init__(self, override_store, db_connection):
        super().__init__(override_store)
        self.db_connection = db_connection
        self.temp_files = []  # Track temp files for cleanup
    
    def process_athlete(self, athlete_data):
        """Process single athlete with GridFS image handling"""
        
        athlete_id = athlete_data['athlete_id']
        
        # Check if image is in GridFS
        image_path = None
        if athlete_data.get('profile_image_gridfs'):
            # Download from GridFS to temp file
            temp_path = self.db_connection.get_image_from_gridfs(
                athlete_data['profile_image_gridfs']
            )
            if temp_path:
                image_path = temp_path
                self.temp_files.append(temp_path)
                print(f"  Downloaded image from GridFS")
        elif athlete_data.get('profile_image_path'):
            # Use local path if available
            if os.path.exists(athlete_data['profile_image_path']):
                image_path = athlete_data['profile_image_path']
        
        # Run inference
        result = self.infer_gender(
            athlete_id=athlete_id,
            athlete_name=athlete_data.get('name', ''),
            sport_team=athlete_data.get('sport_team', ''),
            profile_pic_path=image_path,
            explicit_gender=athlete_data.get('explicit_gender')
        )
        
        return result
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        self.temp_files = []


def process_all_athletes():
    """Process all athletes needing gender inference"""
    
    print("\n" + "="*60)
    print("Gender Inference Batch Processing (MongoDB + GridFS)")
    print("="*60)
    
    # Connect to MongoDB
    print("\nConnecting to MongoDB Atlas...")
    db = MongoDBConnection()
    athlete_repo = AthleteRepository(db)
    override_store = MongoDBOverrideStore(db)
    
    # Initialize inference agent with MongoDB support
    agent = MongoGenderInferenceAgent(override_store, db)
    
    # Get athletes needing inference
    athletes = athlete_repo.get_athletes_needing_inference()
    print(f"Found {len(athletes)} athletes needing gender inference\n")
    
    # Process each athlete
    successful = 0
    failed = 0
    skipped = 0
    
    for athlete in athletes:
        print(f"{'='*40}")
        print(f"Processing: {athlete.get('name', 'Unknown')} ({athlete['athlete_id']})")
        print(f"Team: {athlete.get('sport_team', 'Unknown')}")
        
        try:
            result = agent.process_athlete(athlete)
            
            if result:
                # Check if this is an actual inference result (not an override)
                if 'override' in result.signal_attribution or 'explicit_input' in result.signal_attribution:
                    print(f"  Has explicit gender or override: {result.inferred_gender}")
                    skipped += 1
                else:
                    # This is a real inference result - save to database
                    athlete_repo.update_inferred_gender(
                        athlete_id=athlete['athlete_id'],
                        gender=result.inferred_gender,
                        confidence=result.confidence_score,
                        signal_attribution=result.signal_attribution
                    )
                    
                    print(f"✓ Inferred: {result.inferred_gender}")
                    print(f"  Confidence: {result.confidence_score:.1%}")
                    
                    # Show signal attribution
                    print(f"  Signals used:")
                    for signal, weight in result.signal_attribution.items():
                        print(f"    - {signal}: {weight:.1%}")
                    
                    if result.needs_manual_review:
                        print("  ⚠️ Flagged for manual review")
                    
                    successful += 1
            else:
                print("  No result returned")
                failed += 1
                
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1
    
    # Cleanup temp files
    agent.cleanup_temp_files()
    
    print("\n" + "="*60)
    print("Batch Processing Complete!")
    print(f"Successful: {successful}")
    print(f"Skipped (has override): {skipped}")
    print(f"Failed: {failed}")
    print("="*60)
    
    db.close()


def view_results():
    """View inference results from database"""
    
    print("\n" + "="*60)
    print("Gender Inference Results")
    print("="*60)
    
    db = MongoDBConnection()
    
    # Get all athletes
    athletes = list(db.athletes.find())
    
    # Print summary
    total = len(athletes)
    has_explicit = sum(1 for a in athletes if a.get('explicit_gender'))
    has_inferred = sum(1 for a in athletes if a.get('inferred_gender'))
    needs_review = sum(1 for a in athletes 
                      if a.get('inference_confidence', 1) < 0.5)
    
    print(f"\nTotal athletes: {total}")
    print(f"Has explicit gender: {has_explicit}")
    print(f"Has inferred gender: {has_inferred}")
    print(f"Needs manual review: {needs_review}")
    
    # Print details
    print("\n" + "-"*60)
    print(f"{'ID':<12} {'Name':<20} {'Explicit':<10} {'Inferred':<10} {'Confidence':<12}")
    print("-"*60)
    
    for a in athletes:
        athlete_id = a.get('athlete_id', 'N/A')[:10]
        name = a.get('name', 'Unknown')[:18]
        explicit = str(a.get('explicit_gender', '-'))  # Convert to string
        inferred = str(a.get('inferred_gender', '-'))  # Convert to string
        conf = f"{a.get('inference_confidence', 0)*100:.0f}%" if a.get('inference_confidence') else '-'
        
        print(f"{athlete_id:<12} {name:<20} {explicit:<10} {inferred:<10} {conf:<12}")
    
    db.close()


def clear_all_inferences():
    """Clear all inferred genders (for testing)"""
    
    print("Clearing all inferred genders...")
    db = MongoDBConnection()
    
    # Clear inferred gender fields
    result = db.athletes.update_many(
        {},
        {'$unset': {
            'inferred_gender': '',
            'inference_confidence': '',
            'signal_attribution': '',
            'inference_timestamp': ''
        }}
    )
    
    # Clear override collection
    db.gender_overrides.delete_many({})
    
    print(f"Cleared {result.modified_count} athletes")
    print("Cleared all overrides")
    
    db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'view':
            view_results()
        elif sys.argv[1] == 'clear':
            clear_all_inferences()
        else:
            print("Usage: python main_mongodb.py [view|clear]")
    else:
        process_all_athletes()