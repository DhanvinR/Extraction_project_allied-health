#!/usr/bin/env python3
"""
Example usage of the Comprehensive Booking Extractor
"""

from comprehensive_booking_extractor import ComprehensiveBookingExtractor, process_practitioners_batch
import pandas as pd
import os

def example_single_practitioner():
    """
    Example: Extract data for a single practitioner
    """
    print("🔍 Single Practitioner Example")
    print("=" * 50)
    
    # Initialize extractor (Google API key is optional)
    google_api_key = os.getenv('GOOGLE_API_KEY')  # Set as environment variable
    extractor = ComprehensiveBookingExtractor(google_api_key)
    
    # Extract data for a practitioner with clinic website
    result1 = extractor.extract_practitioner_data(
        practitioner_name="Igor Kharif",
        clinic_website="http://www.coasttherapy.ca"
    )
    
    print("Result 1 (with website):")
    for key, value in result1.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-" * 50)
    
    # Extract data for a practitioner without clinic website (uses Google APIs)
    result2 = extractor.extract_practitioner_data(
        practitioner_name="Stephen Blaxland Physiotherapy Vernon BC"
        # No clinic_website provided - will use Google APIs
    )
    
    print("Result 2 (no website - Google APIs):")
    for key, value in result2.items():
        print(f"  {key}: {value}")

def example_batch_processing():
    """
    Example: Process multiple practitioners in batch
    """
    print("\n🚀 Batch Processing Example")
    print("=" * 50)
    
    # Sample practitioners data
    practitioners_data = [
        {
            'name': 'Igor Kharif',
            'clinic_website': 'http://www.coasttherapy.ca'
        },
        {
            'name': 'Stephen Blaxland',
            'clinic_website': 'https://prospecttherapy.ca'
        },
        {
            'name': 'Carmen Emslie',
            'clinic_website': 'https://physiocareathome.com/'
        },
        {
            'name': 'Jennifer Gabrys Physiotherapy Penticton'
            # No website - will use Google APIs
        },
        {
            'name': 'Giancarlo Brancati',
            'clinic_website': 'http://www.coasttherapy.ca'
        },
        {
            'name': 'Arvin Cheng',
            'clinic_website': 'http://coasttherapy.ca'
        },
        {
            'name': 'Carmen Emslie',
            'clinic_website': 'https://physiocareathome.com/'
        },
        {
            'name': 'Jennifer Gabrys Physiotherapy Penticton'
            # No website - will use Google APIs
        },
        {
            'name': 'Igor Kharif',
            'clinic_website': 'http://www.coasttherapy.ca'
        },
        {
            'name': 'Stephen Blaxland',
            'clinic_website': 'https://prospecttherapy.ca'
        },
        {
            'name': 'Carmen Emslie',
            'clinic_website': 'https://physiocareathome.com/'
        },
        {
            'name': 'Jennifer Gabrys Physiotherapy Penticton'
            # No website - will use Google APIs
        }
    ]
    
    # Set Google API key (optional)
    google_api_key = os.getenv('GOOGLE_API_KEY')
    
    # Process batch
    results = process_practitioners_batch(practitioners_data, google_api_key)
    
    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv('example_results.csv', index=False)
    
    print(f"\n✅ Processed {len(results)} practitioners")
    print("📁 Results saved to: example_results.csv")
    
    # Display summary
    booking_count = len([r for r in results if r.get('booking_url')])
    hours_count = len([r for r in results if any([
        r.get('weekday_earliest_am'),
        r.get('weekday_latest_pm'),
        r.get('weekend_earliest_am'),
        r.get('weekend_latest_pm')
    ])])
    
    print(f"🔗 Booking URLs found: {booking_count}/{len(results)}")
    print(f"⏰ Operating hours found: {hours_count}/{len(results)}")

def example_from_existing_csv():
    """
    Example: Process practitioners from existing CSV file
    """
    print("\n📊 Processing from CSV Example")
    print("=" * 50)
    
    # Load existing practitioners data
    try:
        df = pd.read_csv('all_practitioners_results_enhanced_final.csv')
        
        # Select first 3 practitioners for example
        sample_practitioners = []
        for _, row in df.head(3).iterrows():
            sample_practitioners.append({
                'name': row['practitioner_name'],
                'clinic_website': row.get('clinic_website', '')
            })
        
        # Process with comprehensive extractor
        google_api_key = os.getenv('GOOGLE_API_KEY')
        results = process_practitioners_batch(sample_practitioners, google_api_key)
        
        # Create enhanced DataFrame
        enhanced_df = pd.DataFrame(results)
        enhanced_df.to_csv('enhanced_sample_results.csv', index=False)
        
        print(f"✅ Enhanced {len(results)} practitioners from existing CSV")
        print("📁 Enhanced results saved to: enhanced_sample_results.csv")
        
    except FileNotFoundError:
        print("❌ CSV file not found. Please ensure 'all_practitioners_results_enhanced_final.csv' exists.")

if __name__ == "__main__":
    print("🎯 Comprehensive Booking Extractor Examples")
    print("=" * 60)
    
    # Note about Google API key
    if not os.getenv('GOOGLE_API_KEY'):
        print("⚠️  Note: Set GOOGLE_API_KEY environment variable to enable Google APIs fallback")
        print("   export GOOGLE_API_KEY='your_api_key_here'")
        print()
    
    # Run examples
    example_single_practitioner()
    example_batch_processing()
    example_from_existing_csv()
    
    print("\n🎉 All examples completed!")
    print("📖 Check the generated CSV files for results")
