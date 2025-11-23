"""
Upload local images to MongoDB GridFS
"""

from database import MongoDBConnection

def upload_images_to_gridfs():
    """Upload all athlete images to GridFS"""
    
    print("Connecting to MongoDB...")
    db = MongoDBConnection()
    
    # Image mappings (athlete_id -> local_path)
    image_mappings = [
        ('athlete_001', './data/image1.jpg'),
        ('athlete_002', './data/image2.jpg'),
        ('athlete_003', './data/image3.jpg'),
        ('athlete_004', './data/image4.jpg'),
        ('athlete_005', './data/image5.jpg'),
        ('athlete_008', './data/image6.jpg'),
    ]
    
    print("\nUploading images to GridFS...")
    for athlete_id, local_path in image_mappings:
        try:
            # Check if file exists locally
            import os
            if not os.path.exists(local_path):
                print(f"  ✗ File not found: {local_path}")
                continue
            
            # Upload to GridFS
            file_id = db.upload_image_to_gridfs(local_path, athlete_id)
            
            if file_id:
                # Update athlete record with GridFS file_id
                db.athletes.update_one(
                    {'athlete_id': athlete_id},
                    {'$set': {'profile_image_gridfs': file_id}}
                )
                print(f"  ✓ Uploaded image for {athlete_id}: GridFS ID {file_id}")
            else:
                print(f"  ✗ Failed to upload for {athlete_id}")
                
        except Exception as e:
            print(f"  ✗ Error for {athlete_id}: {e}")
    
    print("\nUpload complete!")
    db.close()

if __name__ == "__main__":
    upload_images_to_gridfs()