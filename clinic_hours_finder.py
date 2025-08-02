#!/usr/bin/env python3
"""
Clinic Hours Finder
Fetches clinic opening hours for each day of the week using Google search
Based on Name, Clinic/Facility Name, Street Address, and Clinic Website
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
import json

class ClinicHoursFinder:
    def __init__(self, excel_path):
        """Initialize with Excel file path"""
        self.excel_path = excel_path
        self.df = pd.read_excel(excel_path)
        print(f"✅ Loaded {len(self.df)} records from {excel_path}")
        
        # Days of the week
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Common hour patterns to look for
        self.hour_patterns = [
            r'(\d{1,2}):?(\d{2})?\s*(am|pm)\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)\s*-\s*(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})',
            r'(\d{1,2})\s*-\s*(\d{1,2})',
        ]
        
        # Closed indicators
        self.closed_indicators = [
            'closed', 'close', 'not open', 'unavailable', 'by appointment only',
            'appointment only', 'call for hours', 'varies', 'holiday hours'
        ]
    
    def clean_search_term(self, text):
        """Clean and prepare text for Google search"""
        if pd.isna(text) or text == 'Unknown' or text == '':
            return ""
        
        # Remove special characters and extra spaces (fix regex pattern)
        cleaned = re.sub(r'[^\w\s\-\.]', ' ', str(text))
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def generate_hours_search_queries(self, name, clinic_name, address, website):
        """Generate search queries for finding clinic hours"""
        queries = []
        
        # Clean the inputs
        clean_name = self.clean_search_term(name)
        clean_clinic = self.clean_search_term(clinic_name)
        clean_address = self.clean_search_term(address)
        clean_website = self.clean_search_term(website)
        
        # Strategy 1: Clinic name + "hours" + "opening times"
        if clean_clinic:
            queries.append(f'"{clean_clinic}" hours opening times')
        
        # Strategy 2: Clinic name + address + "hours"
        if clean_clinic and clean_address:
            queries.append(f'"{clean_clinic}" "{clean_address}" hours')
        
        # Strategy 3: Website + "hours" (if website available)
        if clean_website and clean_website != 'Unknown':
            domain = urlparse(clean_website).netloc if clean_website.startswith('http') else clean_website
            queries.append(f'site:{domain} hours opening times')
        
        # Strategy 4: Clinic name + "open" + days
        if clean_clinic:
            queries.append(f'"{clean_clinic}" open monday tuesday wednesday thursday friday')
        
        # Strategy 5: Name + clinic + "schedule"
        if clean_name and clean_clinic:
            queries.append(f'"{clean_name}" "{clean_clinic}" schedule hours')
        
        return [q for q in queries if q.strip()]
    
    def extract_hours_from_text(self, text):
        """Extract opening hours from text content"""
        if not text:
            return {}
        
        text = text.lower()
        hours_data = {}
        
        # Initialize all days as unknown
        for day in self.days:
            hours_data[day] = "unknown"
        
        # Check for closed indicators first
        for day in self.days:
            day_lower = day.lower()
            
            # Look for "Monday: Closed" or "Closed Monday" patterns
            closed_patterns = [
                rf'{day_lower}:?\s*({"|".join(self.closed_indicators)})',
                rf'({"|".join(self.closed_indicators)})\s*{day_lower}',
                rf'{day_lower}:?\s*-\s*({"|".join(self.closed_indicators)})'
            ]
            
            for pattern in closed_patterns:
                if re.search(pattern, text):
                    hours_data[day] = "closed"
                    break
        
        # Look for hour patterns for each day
        for day in self.days:
            if hours_data[day] != "closed":  # Don't override closed status
                day_lower = day.lower()
                
                # Look for patterns like "Monday: 9am-5pm" or "Mon 9:00-17:00"
                day_patterns = [
                    rf'{day_lower}:?\s*(\d{{1,2}}:?\d{{0,2}}\s*(?:am|pm)?\s*-\s*\d{{1,2}}:?\d{{0,2}}\s*(?:am|pm)?)',
                    rf'{day_lower[:3]}:?\s*(\d{{1,2}}:?\d{{0,2}}\s*(?:am|pm)?\s*-\s*\d{{1,2}}:?\d{{0,2}}\s*(?:am|pm)?)',
                    rf'{day_lower}:?\s*(\d{{1,2}}\s*(?:am|pm)\s*-\s*\d{{1,2}}\s*(?:am|pm))',
                ]
                
                for pattern in day_patterns:
                    match = re.search(pattern, text)
                    if match:
                        hours_data[day] = self.format_hours(match.group(1))
                        break
        
        # Look for general patterns like "Mon-Fri: 9am-5pm"
        general_patterns = [
            r'(mon|monday)\s*-\s*(fri|friday):?\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?\s*-\s*\d{1,2}:?\d{0,2}\s*(?:am|pm)?)',
            r'weekdays?:?\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?\s*-\s*\d{1,2}:?\d{0,2}\s*(?:am|pm)?)',
            r'(mon|tue|wed|thu|fri|sat|sun)\s*-\s*(mon|tue|wed|thu|fri|sat|sun):?\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?\s*-\s*\d{1,2}:?\d{0,2}\s*(?:am|pm)?)'
        ]
        
        for pattern in general_patterns:
            match = re.search(pattern, text)
            if match:
                if 'mon' in match.group(0) and 'fri' in match.group(0):
                    # Monday to Friday pattern
                    formatted_hours = self.format_hours(match.group(-1))
                    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                        if hours_data[day] == "unknown":
                            hours_data[day] = formatted_hours
        
        return hours_data
    
    def format_hours(self, hours_text):
        """Format hours text to standard AM/PM format"""
        if not hours_text:
            return "unknown"
        
        hours_text = hours_text.strip().lower()
        
        # Handle 24-hour format conversion
        time_pattern = r'(\d{1,2}):?(\d{2})?\s*-\s*(\d{1,2}):?(\d{2})?'
        match = re.search(time_pattern, hours_text)
        
        if match:
            start_hour = int(match.group(1))
            start_min = match.group(2) or "00"
            end_hour = int(match.group(3))
            end_min = match.group(4) or "00"
            
            # Convert to AM/PM if not already
            if 'am' not in hours_text and 'pm' not in hours_text:
                start_ampm = "AM" if start_hour < 12 else "PM"
                end_ampm = "AM" if end_hour < 12 else "PM"
                
                if start_hour > 12:
                    start_hour -= 12
                elif start_hour == 0:
                    start_hour = 12
                
                if end_hour > 12:
                    end_hour -= 12
                elif end_hour == 0:
                    end_hour = 12
                
                return f"{start_hour}:{start_min} {start_ampm} - {end_hour}:{end_min} {end_ampm}"
        
        # If already in AM/PM format, clean it up
        am_pm_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)'
        match = re.search(am_pm_pattern, hours_text)
        
        if match:
            start_hour = match.group(1)
            start_min = match.group(2) or "00"
            start_ampm = match.group(3).upper()
            end_hour = match.group(4)
            end_min = match.group(5) or "00"
            end_ampm = match.group(6).upper()
            
            return f"{start_hour}:{start_min} {start_ampm} - {end_hour}:{end_min} {end_ampm}"
        
        return hours_text
    
    def search_clinic_hours(self, name, clinic_name, address, website):
        """Search for clinic hours using Google search"""
        print(f"\n🕐 Searching hours for: {clinic_name}")
        
        queries = self.generate_hours_search_queries(name, clinic_name, address, website)
        print(f"   Generated {len(queries)} search queries")
        
        all_text_content = ""
        
        for i, query in enumerate(queries, 1):
            print(f"   Query {i}: {query}")
            
            try:
                # Perform Google search
                search_results = list(search(query, num_results=3, sleep_interval=2))
                
                for url in search_results:
                    print(f"      Checking: {url}")
                    
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Look for hours in specific elements
                            hours_elements = soup.find_all(['div', 'span', 'p', 'td'], 
                                                         string=re.compile(r'(hours?|open|monday|tuesday|wednesday|thursday|friday|saturday|sunday)', re.I))
                            
                            for element in hours_elements:
                                parent = element.parent
                                if parent:
                                    all_text_content += " " + parent.get_text()
                            
                            # Also get general text content
                            page_text = soup.get_text()
                            all_text_content += " " + page_text
                            
                            print(f"      ✅ Content extracted from {url}")
                        
                    except Exception as e:
                        print(f"      ⚠️ Error accessing {url}: {e}")
                        continue
                
                # Rate limiting between queries
                time.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️ Error with query '{query}': {e}")
                time.sleep(5)
                continue
        
        # Extract hours from all collected text
        hours_data = self.extract_hours_from_text(all_text_content)
        
        # Print found hours
        print(f"   📅 Hours found:")
        for day, hours in hours_data.items():
            print(f"      {day}: {hours}")
        
        return hours_data
    
    def process_sample_records(self, sample_size=5):
        """Process a sample of records with available websites"""
        # Filter records with available websites (not Unknown or empty)
        available_websites = self.df[
            (self.df['Clinic Website'].notna()) & 
            (self.df['Clinic Website'] != 'Unknown') & 
            (self.df['Clinic Website'] != '')
        ].head(sample_size)
        
        if len(available_websites) == 0:
            print("❌ No records with available websites found")
            return []
        
        print(f"📊 Processing {len(available_websites)} records with available websites")
        
        results = []
        
        for idx, (_, row) in enumerate(available_websites.iterrows(), 1):
            print(f"\n{'='*70}")
            print(f"Processing Record {idx}/{len(available_websites)}")
            print(f"{'='*70}")
            
            name = row.get('Name', '')
            clinic_name = row.get('Clinic/Facility Name', '')
            address = row.get('Street Address', '')
            website = row.get('Clinic Website', '')
            
            print(f"Name: {name}")
            print(f"Clinic: {clinic_name}")
            print(f"Address: {address}")
            print(f"Website: {website}")
            
            # Search for hours
            start_time = time.time()
            hours_data = self.search_clinic_hours(name, clinic_name, address, website)
            processing_time = time.time() - start_time
            
            # Create result record
            result = {
                'index': row.name,
                'Name': name,
                'Clinic/Facility Name': clinic_name,
                'Street Address': address,
                'Clinic Website': website,
                'Monday Hours': hours_data.get('Monday', 'unknown'),
                'Tuesday Hours': hours_data.get('Tuesday', 'unknown'),
                'Wednesday Hours': hours_data.get('Wednesday', 'unknown'),
                'Thursday Hours': hours_data.get('Thursday', 'unknown'),
                'Friday Hours': hours_data.get('Friday', 'unknown'),
                'Saturday Hours': hours_data.get('Saturday', 'unknown'),
                'Sunday Hours': hours_data.get('Sunday', 'unknown'),
                'Processing Time': f"{processing_time:.1f}s",
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add all original columns
            for col in self.df.columns:
                if col not in result:
                    result[col] = row.get(col, '')
            
            results.append(result)
            
            # Show summary
            found_hours = sum(1 for day in self.days if hours_data.get(day, 'unknown') not in ['unknown', 'closed'])
            print(f"📊 Found hours for {found_hours}/7 days")
            print(f"⏱️ Processing time: {processing_time:.1f} seconds")
            
            # Rate limiting between records
            if idx < len(available_websites):
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
        
        # Reorder columns to show hours together
        hour_columns = [f"{day} Hours" for day in self.days]
        other_columns = [col for col in results_df.columns if col not in hour_columns and col not in ['Processing Time', 'Timestamp']]
        
        column_order = other_columns + hour_columns + ['Processing Time', 'Timestamp']
        results_df = results_df[column_order]
        
        # Save to Excel with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"clinic_hours_results_{timestamp}.xlsx"
        
        results_df.to_excel(output_filename, index=False)
        print(f"💾 Results saved to: {output_filename}")
        
        # Print summary
        total_days = len(results) * 7
        found_hours = 0
        closed_days = 0
        
        for result in results:
            for day in self.days:
                day_hours = result.get(f"{day} Hours", 'unknown')
                if day_hours not in ['unknown']:
                    if day_hours == 'closed':
                        closed_days += 1
                    else:
                        found_hours += 1
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total records processed: {len(results)}")
        print(f"   Total day-hour combinations: {total_days}")
        print(f"   Hours found: {found_hours}")
        print(f"   Days marked as closed: {closed_days}")
        print(f"   Unknown hours: {total_days - found_hours - closed_days}")
        print(f"   Success rate: {((found_hours + closed_days) / total_days * 100):.1f}%")
        
        return output_filename

def main():
    """Main function to run the clinic hours finder"""
    print("🕐 Clinic Hours Finder")
    print("=" * 50)
    
    # Path to Excel file
    excel_path = os.path.expanduser("~/Downloads/physio_updates_Jul27.xlsx")
    
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return
    
    try:
        # Initialize finder
        finder = ClinicHoursFinder(excel_path)
        
        # Process sample records
        print(f"\n🎯 Processing sample of 5 records with available websites...")
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
