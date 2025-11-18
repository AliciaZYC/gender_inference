import os
import json
import pandas as pd


def download_sport_gender_data(force_download=False):
    """
    Download and process sport gender data from TidyTuesday
    
    Args:
        force_download: If True, re-download even if local files exist
    
    Returns:
        dict: Sport gender ratios {sport_name: male_ratio}
    """
    # Create data directory
    os.makedirs("sport_gender_data", exist_ok=True)
    
    csv_path = "sport_gender_data/tidytuesday_sports.csv"
    output_path = "sport_gender_data/sport_gender_ratios.json"
    
    # Download or load TidyTuesday data
    if force_download or not os.path.exists(csv_path):
        print("Downloading TidyTuesday NCAA data...")
        try:
            url = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2022/2022-03-29/sports.csv"
            df = pd.read_csv(url, low_memory=False)
            df.to_csv(csv_path, index=False)
            print("✓ Data downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download data: {e}")
            if os.path.exists(csv_path):
                print("  Using existing local file instead")
                df = pd.read_csv(csv_path, low_memory=False)
            else:
                print("  No data available")
                return {}
    else:
        print("✓ Data file already exists, loading from local file")
        df = pd.read_csv(csv_path, low_memory=False)
    
    # Process data
    print("Processing sport gender ratios...")
    
    sport_gender_map = {}
    
    # Process each sport
    for sport in df['sports'].dropna().unique():
        sport_df = df[df['sports'] == sport].copy()
        
        # Get the latest year's data
        latest_year = sport_df['year'].max()
        latest_data = sport_df[sport_df['year'] == latest_year]
        
        # Calculate gender ratio
        total_men = latest_data['sum_partic_men'].fillna(0).sum()
        total_women = latest_data['sum_partic_women'].fillna(0).sum()
        total = total_men + total_women
        
        if total > 0:
            male_ratio = total_men / total
            # Standardize sport name
            sport_key = sport.lower().replace(' ', '_').replace('-', '_').replace('&', 'and')
            sport_gender_map[sport_key] = round(male_ratio, 4)
    
    # Save as JSON
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(sport_gender_map, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processing complete! Found gender data for {len(sport_gender_map)} sports")
    print(f"   Saved to: {output_path}")
    
    # Print sample data
    print("\nSample of sport gender ratios (male probability):")
    samples = ['football', 'basketball', 'volleyball', 'tennis', 'baseball']
    for sport in samples:
        if sport in sport_gender_map:
            ratio = sport_gender_map[sport]
            gender = "male" if ratio > 0.5 else "female"
            print(f"  {sport:15s}: {ratio:.1%} male, {(1-ratio):.1%} female (likely {gender})")
    
    return sport_gender_map


def load_sport_ratios():
    """
    Load saved sport gender ratios
    """
    json_path = "sport_gender_data/sport_gender_ratios.json"
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Data file not found. Running download first...")
        return download_sport_gender_data()


if __name__ == "__main__":
    # Download and process data
    sport_ratios = download_sport_gender_data()