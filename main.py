import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import requests
import base64
import json
import os
from override_store import OverrideStore

@dataclass
class InferenceResult:
    inferred_gender: str  # 'male' or 'female'
    confidence_score: float  # 0.0 to 1.0
    signal_attribution: Dict[str, float]  # Weight contribution from each signal
    needs_manual_review: bool  # Flag for low confidence cases
    
    @property
    def gender_label(self) -> str:
        """Backwards compatibility - returns inferred_gender"""
        return self.inferred_gender

class GenderInferenceAgent:
    def __init__(self, override_store: OverrideStore, low_conf_threshold=0.3, high_conf_threshold=0.7):
        """
        Initialize Gender Inference AI Agent
        Combines default sport gender, first name, and profile photo signals
        
        Args:
            override_store: Persistence layer for gender overrides (dependency injection)
            low_conf_threshold: Lower confidence threshold
            high_conf_threshold: Higher confidence threshold
        """
        self.low_threshold = low_conf_threshold
        self.high_threshold = high_conf_threshold
        self.store = override_store  # Dependency injection
        
        # Load name gender model
        self.name_gender_model = self._load_name_model()
        
        # Load sport statistics
        self.sport_stats = self._load_sport_statistics()
    
    def _load_name_model(self):
        """
        Load name gender model using Gender-guesser
        """
        try:
            import gender_guesser.detector as gender
            print("Loading gender-guesser (400k+ international names dataset)")
            return gender.Detector()
        except ImportError:
            raise ImportError(
                "gender-guesser not installed. Run: pip install gender-guesser"
            )
    
    def _load_sport_statistics(self):
        """
        Load sport gender statistics from JSON file
        """
        json_path = "sport_gender_data/sport_gender_ratios.json"
        if not os.path.exists(json_path):
            print(f"Warning: Data file not found: {json_path}")
            print("Please run data_processing.py to generate data file")
            return {}
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                downloaded_data = json.load(f)
            
            sport_stats = {}
            for sport, male_ratio in downloaded_data.items():
                sport_stats[sport] = {
                    'male_ratio': float(male_ratio),
                    'sample_size': 0
                }
            
            print(f"Loaded {len(sport_stats)} sports data entries")
            return sport_stats
        except Exception as e:
            print(f"Failed to load data file: {e}")
            return {}
    
    def get_name_signal(self, first_name: str) -> Tuple[float, float, str]:
        """
        Analyze first name for gender probability
        Returns: (male_probability, confidence, signal_quality)
        Handles neutral/ambiguous names
        """
        if not first_name:
            return 0.5, 0.0, "missing"
        
        result = self.name_gender_model.get_gender(first_name.capitalize())
        
        # Map gender-guesser results to probabilities and quality
        prob_map = {
            'male': (0.95, 0.90, "high"),           # Clear male name
            'female': (0.05, 0.90, "high"),          # Clear female name
            'mostly_male': (0.80, 0.60, "medium"),   # Mostly male but has exceptions
            'mostly_female': (0.20, 0.60, "medium"), # Mostly female but has exceptions
            'andy': (0.50, 0.10, "ambiguous"),       # Neutral/ambiguous name (e.g., Alex)
            'unknown': (0.50, 0.05, "unknown")       # Unknown name
        }
        
        return prob_map.get(result, (0.50, 0.05, "unknown"))
    
    def get_sport_signal(self, sport_team: str) -> Tuple[float, bool, str]:
        """
        Get default sport gender probability
        Returns: (male_probability, is_explicit_gender, signal_quality)
        Handles mis-assigned teams (e.g., female on men's team)
        """
        sport_lower = sport_team.lower()
        
        # Check for explicit gender markers (handles mis-assigned teams)
        female_keywords = ["women", "woman", "ladies", "girls", "female", "w."]
        male_keywords = ["men", "man", "boys", "male", "m."]
        
        # Explicit gender teams (like "UCLA Men's Football" or "US Women's Soccer")
        for keyword in female_keywords:
            if keyword in sport_lower:
                return 0.02, True, "explicit_female"
        
        for keyword in male_keywords:
            if keyword in sport_lower:
                return 0.98, True, "explicit_male"
        
        # Clean sport name for matching
        sport_clean = sport_lower
        for keyword in female_keywords + male_keywords + ["team", "club", "university", "college", "school"]:
            sport_clean = sport_clean.replace(keyword, "").strip()
        
        sport_normalized = sport_clean.replace(' ', '_').replace('-', '_')
        
        # Match against sport statistics
        if sport_normalized in self.sport_stats:
            ratio = self.sport_stats[sport_normalized]['male_ratio']
            # Determine quality based on how skewed the ratio is
            if ratio > 0.9 or ratio < 0.1:
                quality = "high"  # Sports like football (men only) or softball (women only)
            elif ratio > 0.7 or ratio < 0.3:
                quality = "medium"
            else:
                quality = "mixed"  # Mixed sports like Track & Field
            return ratio, False, quality
        
        # Partial matching
        for sport_name, stats in self.sport_stats.items():
            if sport_name in sport_lower or sport_name in sport_normalized:
                ratio = stats['male_ratio']
                if ratio > 0.9 or ratio < 0.1:
                    quality = "high"
                elif ratio > 0.7 or ratio < 0.3:
                    quality = "medium"
                else:
                    quality = "mixed"
                return ratio, False, quality
        
        # Unknown sport
        return 0.50, False, "unknown"
    
    def get_image_signal(self, image_path: str) -> Tuple[float, str]:
        """
        Analyze profile picture using Face++ API
        Returns: (male_probability, signal_quality)
        Handles group photos and low-quality images
        """
        # Face++ API configuration
        API_KEY = "EfUBVzQeIjJMYMWyEdJu3_AqgYw_7Jd3"
        API_SECRET = "2LsPdmGz7RvoSAE7bKQv4ojOHG3d6rjq"
        
        if API_KEY == "YOUR_API_KEY" or API_SECRET == "YOUR_API_SECRET":
            print("Warning: Face++ API credentials not configured")
            return 0.50, "api_error"
        
        try:
            url = "https://api-us.faceplusplus.com/facepp/v3/detect"
            
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            data = {
                'api_key': API_KEY,
                'api_secret': API_SECRET,
                'image_base64': image_data,
                'return_attributes': 'gender,age'
            }
            
            print(f"  Calling Face++ API...")
            response = requests.post(url, data=data, timeout=15)
            result = response.json()
            
            if 'error_message' in result:
                print(f"  Face++ API error: {result['error_message']}")
                return 0.50, "api_error"
            
            if 'faces' in result:
                num_faces = len(result['faces'])
                
                if num_faces == 0:
                    print("  No faces detected in image")
                    return 0.50, "no_face"
                
                elif num_faces == 1:
                    # Single face - high quality signal
                    face = result['faces'][0]
                    gender = face['attributes']['gender']['value']
                    age = face['attributes'].get('age', {}).get('value', 'unknown')
                    print(f"  Face++ detected: {gender}, age ~{age}")
                    
                    if gender.lower() == 'male':
                        return 0.95, "high"
                    else:
                        return 0.05, "high"
                
                else:
                    # Group photo - analyze all faces
                    print(f"  Group photo detected ({num_faces} faces)")
                    male_count = sum(1 for face in result['faces'] 
                                   if face['attributes']['gender']['value'].lower() == 'male')
                    female_count = num_faces - male_count
                    
                    # If all same gender, confidence is medium
                    # If mixed, confidence is low
                    if male_count == num_faces:
                        print(f"  All {num_faces} faces appear male")
                        return 0.85, "group_same"  # Slightly lower confidence for group
                    elif female_count == num_faces:
                        print(f"  All {num_faces} faces appear female")
                        return 0.15, "group_same"
                    else:
                        print(f"  Mixed group: {male_count} male, {female_count} female")
                        # Use ratio but with low confidence
                        return male_count / num_faces, "group_mixed"
            
            return 0.50, "unknown"
                
        except requests.exceptions.Timeout:
            print("  Face++ API timeout")
            return 0.50, "timeout"
        except Exception as e:
            print(f"  Face++ API error: {e}")
            return 0.50, "error"
    
    def set_manual_override(self, athlete_id: str, gender: str):
        """
        Manually set a gender override for an athlete
        This will be persisted and used in future inferences
        
        Args:
            athlete_id: Unique identifier for the athlete
            gender: 'male' or 'female'
        """
        self.store.set_override(athlete_id, gender)
        print(f"Override set for athlete {athlete_id}: {gender}")
    
    def clear_manual_override(self, athlete_id: str):
        """
        Clear a gender override for an athlete
        
        Args:
            athlete_id: Unique identifier for the athlete
        """
        self.store.clear_override(athlete_id)
        print(f"Override cleared for athlete {athlete_id}")
    
    def infer_gender(self, 
                     athlete_id: str,
                     athlete_name: str, 
                     sport_team: str,
                     profile_pic_path: Optional[str] = None,
                     explicit_gender: Optional[str] = None) -> Optional[InferenceResult]:
        """
        Main inference pipeline with persistent override support
        
        Args:
            athlete_id: Unique identifier for the athlete (required for override persistence)
            athlete_name: Full name of the athlete
            sport_team: Sport team name
            profile_pic_path: Path to profile picture (optional)
            explicit_gender: Explicitly provided gender (optional, will be persisted)
        
        Returns:
            InferenceResult or None if override exists
        """
        # Step 1: Check for persistent override
        override = self.store.get_override(athlete_id)
        if override:
            print(f"Found override for ID {athlete_id}: {override}. Skipping inference.")
            return InferenceResult(
                inferred_gender=override,
                confidence_score=1.0,
                signal_attribution={'override': 1.0},
                needs_manual_review=False
            )
        
        # Step 2: Check explicit input and persist if exists
        if explicit_gender:
            normalized_gender = explicit_gender.lower().strip()
            print(f"Explicit gender provided: {normalized_gender}. Storing override and skipping inference.")
            self.store.set_override(athlete_id, normalized_gender)  # Persist immediately
            return InferenceResult(
                inferred_gender=normalized_gender,
                confidence_score=1.0,
                signal_attribution={'explicit_input': 1.0},
                needs_manual_review=False
            )
        
        # Initialize signal tracking
        signal_attribution = {}
        signal_weights = {}
        
        # Get sport signal (default sport gender)
        sport_prob, sport_is_explicit, sport_quality = self.get_sport_signal(sport_team)
        signal_attribution["sport"] = sport_prob
        
        # Get name signal
        name_parts = athlete_name.split()
        first_name = name_parts[0] if name_parts else ""
        name_prob, name_confidence, name_quality = self.get_name_signal(first_name)
        signal_attribution["name"] = name_prob
        
        # Determine initial weights based on signal quality
        # Handle ambiguous/neutral names and mixed sports
        if sport_is_explicit:
            # Explicit team gender is very strong signal
            signal_weights["sport"] = 0.8
            signal_weights["name"] = 0.2 if name_quality != "ambiguous" else 0.1
        else:
            # Adjust weights based on signal quality
            if sport_quality == "mixed":
                signal_weights["sport"] = 0.2  # Low weight for mixed sports like Track & Field
            elif sport_quality == "high":
                signal_weights["sport"] = 0.5
            else:
                signal_weights["sport"] = 0.3
            
            if name_quality == "ambiguous":
                signal_weights["name"] = 0.1  # Very low weight for names like Alex
            elif name_quality == "high":
                signal_weights["name"] = 0.4
            else:
                signal_weights["name"] = 0.2
        
        # Calculate initial probability and confidence
        total_weight = sum(signal_weights.values())
        if total_weight > 0:
            initial_prob = sum(prob * signal_weights.get(key, 0) 
                             for key, prob in [("sport", sport_prob), ("name", name_prob)]) / total_weight
        else:
            initial_prob = 0.5
        
        # Calculate initial confidence from name+sport only
        initial_confidence = abs(initial_prob - 0.5) * 2
        
        # Determine if image analysis needed based on:
        # 1. Low initial confidence
        # 2. Ambiguous signals (neutral name or mixed sport)
        needs_image = (
            initial_confidence < 0.7 or  # Confidence less than 70%
            name_quality == "ambiguous" or  # Ambiguous name like Alex
            sport_quality == "mixed"  # Mixed sport like Track & Field
        )
        
        # Process image if available
        final_prob = initial_prob
        if profile_pic_path and os.path.exists(profile_pic_path):
            if needs_image:
                print(f"  Initial confidence {initial_confidence:.1%} (name: {name_quality}, sport: {sport_quality})")
                print(f"  Analyzing image for better accuracy...")
                image_prob, image_quality = self.get_image_signal(profile_pic_path)
                signal_attribution["image"] = image_prob
                
                # Adjust image weight based on quality
                if image_quality == "high":
                    signal_weights["image"] = 0.6  # Single clear face
                elif image_quality == "group_same":
                    signal_weights["image"] = 0.4  # Group photo, same gender
                elif image_quality in ["group_mixed", "no_face"]:
                    signal_weights["image"] = 0.1  # Very low weight for mixed/no face
                else:
                    signal_weights["image"] = 0.2  # Low quality signal
                
                # Recalculate with all signals
                total_weight = sum(signal_weights.values())
                final_prob = sum(prob * signal_weights.get(key, 0) 
                               for key, prob in signal_attribution.items()) / total_weight
            else:
                print(f"  High confidence ({initial_confidence:.1%}) from name+sport, skipping image")
        else:
            if needs_image and profile_pic_path:
                print(f"  Image needed but file not found: {profile_pic_path}")
            elif needs_image:
                print(f"  Low confidence ({initial_confidence:.1%}) but no image provided")
        
        # Determine gender and confidence
        inferred_gender = "male" if final_prob >= 0.5 else "female"
        confidence_score = abs(final_prob - 0.5) * 2  # Convert to 0-1 confidence
        
        # Flag for manual review if confidence is low
        needs_manual_review = confidence_score < 0.5
        
        # Normalize signal weights to show attribution
        if total_weight > 0:
            for key in signal_weights:
                signal_weights[key] /= total_weight
        
        return InferenceResult(
            inferred_gender=inferred_gender,
            confidence_score=confidence_score,
            signal_attribution=signal_weights,
            needs_manual_review=needs_manual_review
        )


# Example usage
if __name__ == "__main__":
    from override_store import InMemoryOverrideStore
    from test_data import MOCK_ATHLETES
    
    print("\n" + "=" * 60)
    print("Gender Inference AI System")
    print("=" * 60)
    print("\nFeatures:")
    print("- Default sport gender analysis")
    print("- First name gender detection")
    print("- Profile picture analysis (handles group photos)")
    print("- Conditional weighting for ambiguous signals")
    print("- Persistent override storage (dependency injection)")
    print("-" * 60)
    
    # Initialize override store (can be swapped with MongoDB/Redis implementation)
    override_store = InMemoryOverrideStore()
    
    # Initialize agent with override store
    agent = GenderInferenceAgent(override_store=override_store)
    
    print("\nInference Results:")
    print("=" * 60)
    
    for athlete_data in MOCK_ATHLETES:
        athlete_id = athlete_data['athlete_id']
        print(f"\nAthlete ID: {athlete_id}")
        print(f"Athlete: {athlete_data['name']}")
        print(f"Team: {athlete_data['sport_team']}")
        print(f"Image: {athlete_data.get('profile_image', 'None')}")
        print(f"Explicit Gender: {athlete_data.get('explicit_gender', 'None')}")
        
        result = agent.infer_gender(
            athlete_id=athlete_id,
            athlete_name=athlete_data['name'],
            sport_team=athlete_data['sport_team'],
            profile_pic_path=athlete_data.get('profile_image'),
            explicit_gender=athlete_data.get('explicit_gender')
        )
        
        if result:
            print(f"Inferred Gender: {result.inferred_gender}")
            print(f"Confidence Score: {result.confidence_score:.2%}")
            print(f"Signal Attribution:")
            for signal, weight in result.signal_attribution.items():
                print(f"  - {signal}: {weight:.2%}")
            if result.needs_manual_review:
                print("⚠️ Low confidence - needs manual review")
        else:
            print("Inference skipped (override or explicit gender)")
        
        print("-" * 40)
    
    # Demonstrate override persistence
    print("\n" + "=" * 60)
    print("Testing Override Persistence")
    print("=" * 60)
    
    # Test: Set a manual override
    print("\n1. Setting manual override for athlete_001...")
    agent.set_manual_override('athlete_001', 'female')
    
    # Test: Re-infer the same athlete (should use override)
    print("\n2. Re-inferring athlete_001 (should use override)...")
    result = agent.infer_gender(
        athlete_id='athlete_001',
        athlete_name='Michael Johnson',
        sport_team='UCLA Football',
        profile_pic_path='./data/image1.jpg'
    )
    if result:
        print(f"   Result: {result.inferred_gender} (from override)")
    
    # Test: Clear override
    print("\n3. Clearing override for athlete_001...")
    agent.clear_manual_override('athlete_001')
    
    # Test: Re-infer again (should do normal inference)
    print("\n4. Re-inferring athlete_001 (should do normal inference)...")
    result = agent.infer_gender(
        athlete_id='athlete_001',
        athlete_name='Michael Johnson',
        sport_team='UCLA Football',
        profile_pic_path='./data/image1.jpg'
    )
    if result:
        print(f"   Result: {result.inferred_gender} (from inference)")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)