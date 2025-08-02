#!/usr/bin/env python3
"""
Clinic Website Finder
Simple Google search-based website finder for RMT clinics using Name, Clinic/Facility Name, and Street Address
"""

import pandas as pd
import requests
from googlesearch import search
import time
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import os
from datetime import datetime

class ClinicWebsiteFinder:
    def __init__(self, excel_path):
        """Initialize with Excel file path"""
        self.excel_path = excel_path
        self.df = pd.read_excel(excel_path)
        print(f"✅ Loaded {len(self.df)} records from {excel_path}")
        
        # Healthcare-related keywords for validation
        self.healthcare_keywords = [
            'massage', 'therapy', 'rmt', 'wellness', 'health', 'clinic', 
            'physiotherapy', 'rehabilitation', 'treatment', 'therapeutic',
            'registered massage therapist', 'bodywork', 'healing'
        ]
        
        # Domains to exclude (directories, social media, etc.)
        self.excluded_domains = [
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'yelp.com', 'yellowpages.ca', 'google.com', 'maps.google.com',
            'foursquare.com', 'tripadvisor.com', 'booking.com'
        ]
    
    def clean_search_term(self, text):
        """Clean and prepare text for Google search"""
        if pd.isna(text) or text == 'Unknown':
            return ""
        
        # Remove special characters and extra spaces
        cleaned = re.sub(r'[^\w\s-]', ' ', str(text))
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def generate_search_queries(self, name, clinic_name, address):
        """Generate multiple search queries for finding the clinic website"""
        queries = []
        
        # Clean the inputs
        clean_name = self.clean_search_term(name)
        clean_clinic = self.clean_search_term(clinic_name)
        clean_address = self.clean_search_term(address)
        
        # Strategy 1: Clinic name + address + massage therapy
        if clean_clinic and clean_address:
            queries.append(f'"{clean_clinic}" "{clean_address}" massage therapy')
        
        # Strategy 2: Clinic name + massage therapy + RMT
        if clean_clinic:
            queries.append(f'"{clean_clinic}" massage therapy RMT')
        
        # Strategy 3: Name + clinic + massage therapy
        if clean_name and clean_clinic:
            queries.append(f'"{clean_name}" "{clean_clinic}" massage therapy')
        
        # Strategy 4: Clinic name + address (simple)
        if clean_clinic and clean_address:
            queries.append(f'"{clean_clinic}" "{clean_address}"')
        
        # Strategy 5: Just clinic name + massage
        if clean_clinic:
            queries.append(f'"{clean_clinic}" massage')
        
        return [q for q in queries if q.strip()]
    
    def validate_website(self, url):
        """Validate if the website is relevant to healthcare/massage therapy"""
        try:
            # Check domain exclusions
            domain = urlparse(url).netloc.lower()
            if any(excluded in domain for excluded in self.excluded_domains):
                return False, 0.0
            
            # Try to fetch and analyze the page content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return False, 0.0
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Count healthcare keywords
            keyword_count = sum(1 for keyword in self.healthcare_keywords if keyword in text_content)
            
            # Calculate relevance score
            score = keyword_count / len(self.healthcare_keywords)
            
            # Consider it valid if score > 0.1 (at least 10% of keywords found)
            is_valid = score > 0.1
            
            return is_valid, score
            
        except Exception as e:
            print(f"   ⚠️ Error validating {url}: {e}")
            return False, 0.0
    
    def search_for_website(self, name, clinic_name, address):
        """Search for clinic website using Google search"""
        print(f"\n🔍 Searching for: {name} at {clinic_name}")
        
        queries = self.generate_search_queries(name, clinic_name, address)
        print(f"   Generated {len(queries)} search queries")
        
        best_website = None
        best_score = 0.0
        
        for i, query in enumerate(queries, 1):
            print(f"   Query {i}: {query}")
            
            try:
                # Perform Google search
                search_results = list(search(query, num_results=5, sleep_interval=2))
                
                for url in search_results:
                    print(f"      Checking: {url}")
                    
                    is_valid, score = self.validate_website(url)
                    
                    if is_valid and score > best_score:
                        best_website = url
                        best_score = score
                        print(f"      ✅ Valid website found! Score: {score:.2f}")
                        
                        # If we found a high-quality match, stop searching
                        if score > 0.3:
                            print(f"   🎯 High-quality match found, stopping search")
                            return best_website, best_score, query
                    else:
                        print(f"      ❌ Not relevant (score: {score:.2f})")
                
                # Rate limiting between queries
                time.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️ Error with query '{query}': {e}")
                time.sleep(5)  # Longer delay on error
                continue
        
        if best_website:
            print(f"   ✅ Best website found: {best_website} (score: {best_score:.2f})")
        else:
            print(f"   ❌ No suitable website found")
        
        return best_website, best_score, queries[0] if queries else ""
    
    def process_sample_records(self, sample_size=5):
        """Process a sample of records with unknown websites"""
        # Filter records with unknown websites
        unknown_records = self.df[self.df['Website'] == 'Unknown'].head(sample_size)
        
        if len(unknown_records) == 0:
            print("❌ No records with 'Unknown' websites found")
            return []
        
        print(f"📊 Processing {len(unknown_records)} records with unknown websites")
        
        results = []
        
        for idx, (_, row) in enumerate(unknown_records.iterrows(), 1):
            print(f"\n{'='*60}")
            print(f"Processing Record {idx}/{len(unknown_records)}")
            print(f"{'='*60}")
            
            name = row.get('Name', '')
            clinic_name = row.get('Clinic/Facility Name', '')
            address = row.get('Street Address', '')
            
            print(f"Name: {name}")
            print(f"Clinic: {clinic_name}")
            print(f"Address: {address}")
            
            # Search for website
            start_time = time.time()
            website, score, query_used = self.search_for_website(name, clinic_name, address)
            processing_time = time.time() - start_time
            
            result = {
                'index': row.name,
                'name': name,
                'clinic_name': clinic_name,
                'address': address,
                'original_website': row.get('Website', ''),
                'found_website': website if website else 'Not Found',
                'confidence_score': score,
                'query_used': query_used,
                'processing_time': f"{processing_time:.1f}s",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            results.append(result)
            
            # Show result
            if website:
                print(f"🎉 SUCCESS: Found website {website}")
            else:
                print(f"😞 No website found for this record")
            
            print(f"⏱️ Processing time: {processing_time:.1f} seconds")
            
            # Rate limiting between records
            if idx < len(unknown_records):
                print(f"⏳ Waiting 5 seconds before next record...")
                time.sleep(5)
        
        return results
    
    def save_results(self, results):
        """Save results to Excel file"""
        if not results:
            print("❌ No results to save")
            return
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Save to Excel with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"clinic_website_results_{timestamp}.xlsx"
        
        results_df.to_excel(output_filename, index=False)
        print(f"💾 Results saved to: {output_filename}")
        
        # Print summary
        found_count = sum(1 for r in results if r['found_website'] != 'Not Found')
        success_rate = (found_count / len(results)) * 100
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total processed: {len(results)}")
        print(f"   Websites found: {found_count}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        return output_filename

def main():
    """Main function to run the clinic website finder"""
    print("🏥 Clinic Website Finder")
    print("=" * 50)
    
    # Path to Excel file
    excel_path = os.path.expanduser("~/Downloads/rmt.xlsx")
    
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return
    
    try:
        # Initialize finder
        finder = ClinicWebsiteFinder(excel_path)
        
        # Process sample records
        print(f"\n🎯 Processing sample of 5 records with unknown websites...")
        results = finder.process_sample_records(sample_size=5)
        
        # Save results
        if results:
            output_file = finder.save_results(results)
            print(f"\n✅ Processing complete! Check {output_file} for results.")
        else:
            print("❌ No results generated")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
