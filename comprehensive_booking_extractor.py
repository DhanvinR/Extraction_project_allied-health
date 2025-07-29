#!/usr/bin/env python3
"""
Comprehensive Booking URL and Hours Extractor
Extracts booking URLs and operating hours from practitioner names and clinic websites
Uses Google APIs as fallback when clinic website is not available
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import re
from urllib.parse import urljoin, unquote
import json
import os
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ComprehensiveBookingExtractor:
    def __init__(self, google_api_key: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.google_api_key = google_api_key
        
        # Enhanced booking link patterns
        self.booking_patterns = [
            r'book\s*(?:now|online|appointment|visit|treatment|session)',
            r'schedule\s*(?:now|online|appointment|visit|treatment)',
            r'appointment\s*(?:booking|online|schedule)',
            r'online\s*(?:booking|scheduling|appointment)',
            r'reserve\s*(?:now|online|appointment)',
            r'request\s*(?:appointment|consultation)',
            r'contact\s*(?:us|form)',
            r'get\s*started',
            r'book\s*a\s*(?:visit|session|treatment|consultation)',
            r'make\s*an?\s*appointment',
            r'patient\s*portal',
            r'client\s*portal'
        ]
        
        # Common booking paths to try
        self.booking_paths = [
            '/book', '/booking', '/book-online', '/book-now',
            '/appointment', '/appointments', '/schedule', '/scheduling',
            '/contact', '/contact-us', '/get-started', '/portal',
            '/patient-portal', '/client-portal', '/online-booking',
            '/book-appointment', '/request-appointment'
        ]
        
        # Hours patterns for extraction
        self.hours_patterns = [
            r'(\w+)\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'(\w+)\s*:?\s*(\d{1,2})\s*(am|pm)\s*-\s*(\d{1,2})\s*(am|pm)',
            r'hours?\s*:?\s*(\w+)\s*-?\s*(\w+)\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'open\s*:?\s*(\w+)\s*-?\s*(\w+)\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)'
        ]

    def extract_practitioner_data(self, practitioner_name: str, clinic_website: str = None) -> Dict:
        """
        Main function to extract booking URL and operating hours
        """
        logging.info(f"🔍 Processing: {practitioner_name}")
        
        result = {
            'practitioner_name': practitioner_name,
            'clinic_website': clinic_website,
            'booking_url': '',
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': '',
            'data_source': ''
        }
        
        if clinic_website:
            # Extract from clinic website
            logging.info(f"   📱 Extracting from clinic website: {clinic_website}")
            website_data = self.extract_from_website(clinic_website)
            result.update(website_data)
            result['data_source'] = 'clinic_website'
        else:
            # Use Google APIs as fallback
            logging.info(f"   🌐 No clinic website - using Google APIs")
            google_data = self.extract_from_google_apis(practitioner_name)
            result.update(google_data)
            result['data_source'] = 'google_apis'
        
        return result

    def extract_from_website(self, website_url: str) -> Dict:
        """
        Extract booking URL and hours from clinic website
        """
        data = {
            'booking_url': '',
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': ''
        }
        
        try:
            # Get website content
            response = self.session.get(website_url, timeout=15, allow_redirects=True)
            if response.status_code != 200:
                return data
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = response.text.lower()
            
            # Extract booking URL
            booking_url = self.extract_booking_url(website_url, soup, page_text)
            if booking_url:
                data['booking_url'] = booking_url
                logging.info(f"   ✅ Found booking URL: {booking_url}")
            
            # Extract operating hours
            hours_data = self.extract_operating_hours(soup, page_text)
            data.update(hours_data)
            
            if any(hours_data.values()):
                logging.info(f"   ⏰ Found operating hours")
            
        except Exception as e:
            logging.error(f"   ❌ Error extracting from website: {e}")
        
        return data

    def extract_booking_url(self, website_url: str, soup: BeautifulSoup, page_text: str) -> str:
        """
        Extract booking URL using multiple strategies
        """
        booking_urls = set()
        
        # Strategy 1: Direct Jane.app URLs in HTML
        jane_patterns = [
            r'https?://[^/]*\.janeapp\.com[^\s"\']*',
            r'https?://[^/]*janeapp[^/]*\.com[^\s"\']*'
        ]
        
        for pattern in jane_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                clean_url = match.rstrip('",\')}]')
                if 'janeapp.com' in clean_url:
                    booking_urls.add(clean_url)
        
        if booking_urls:
            return list(booking_urls)[0]
        
        # Strategy 2: Follow booking links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True).lower()
            
            for pattern in self.booking_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    full_url = urljoin(website_url, href)
                    
                    if 'janeapp.com' in full_url:
                        return full_url
                    
                    # Follow the link to check for Jane.app
                    jane_url = self.follow_booking_link(full_url)
                    if jane_url:
                        return jane_url
                    break
        
        # Strategy 3: Try common booking paths
        for path in self.booking_paths[:5]:  # Limit to first 5 to avoid too many requests
            try:
                test_url = website_url.rstrip('/') + path
                response = self.session.get(test_url, timeout=8, allow_redirects=True)
                
                if response.status_code == 200:
                    if 'janeapp.com' in response.url:
                        return response.url
                    
                    if 'janeapp.com' in response.text.lower():
                        jane_matches = re.findall(jane_patterns[0], response.text, re.IGNORECASE)
                        if jane_matches:
                            return jane_matches[0].rstrip('",\')}]')
                
                time.sleep(0.5)  # Rate limiting
                
            except:
                continue
        
        return ''

    def follow_booking_link(self, url: str) -> str:
        """
        Follow a booking link to see if it redirects to Jane.app
        """
        try:
            response = self.session.get(url, timeout=8, allow_redirects=True)
            if response.status_code == 200:
                if 'janeapp.com' in response.url:
                    return response.url
                
                if 'janeapp.com' in response.text.lower():
                    jane_pattern = r'https?://[^/]*\.janeapp\.com[^\s"\']*'
                    matches = re.findall(jane_pattern, response.text, re.IGNORECASE)
                    if matches:
                        return matches[0].rstrip('",\')}]')
        except:
            pass
        
        return ''

    def extract_operating_hours(self, soup: BeautifulSoup, page_text: str) -> Dict:
        """
        Extract operating hours from website content
        """
        hours_data = {
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': ''
        }
        
        # Look for hours sections
        hours_sections = soup.find_all(['div', 'section', 'p'], 
                                     class_=re.compile(r'hours|time|schedule', re.I))
        
        # Also search for text containing hours keywords
        hours_text = ''
        for section in hours_sections:
            hours_text += section.get_text() + ' '
        
        # If no specific sections found, search entire page text
        if not hours_text.strip():
            hours_text = page_text
        
        # Extract hours using patterns
        hours_info = self.parse_hours_text(hours_text)
        hours_data.update(hours_info)
        
        return hours_data

    def parse_hours_text(self, text: str) -> Dict:
        """
        Parse hours information from text
        """
        hours_data = {
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': ''
        }
        
        # Common hour patterns
        patterns = [
            r'monday\s*-?\s*friday\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'weekdays?\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'mon\s*-?\s*fri\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'saturday\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'sunday\s*:?\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
        ]
        
        text_lower = text.lower()
        
        # Extract weekday hours
        for pattern in patterns[:3]:  # Weekday patterns
            match = re.search(pattern, text_lower)
            if match:
                start_hour = self.normalize_time(match.groups())
                end_hour = self.normalize_time(match.groups()[len(match.groups())//2:])
                
                if start_hour:
                    hours_data['weekday_earliest_am'] = start_hour
                if end_hour:
                    hours_data['weekday_latest_pm'] = end_hour
                break
        
        # Extract weekend hours (Saturday)
        sat_match = re.search(patterns[3], text_lower)
        if sat_match:
            start_hour = self.normalize_time(sat_match.groups()[:3])
            end_hour = self.normalize_time(sat_match.groups()[3:])
            
            if start_hour:
                hours_data['weekend_earliest_am'] = start_hour
            if end_hour:
                hours_data['weekend_latest_pm'] = end_hour
        
        # Look for closed days
        closed_patterns = [
            r'closed\s+on\s+(\w+)',
            r'(\w+)\s*:?\s*closed',
            r'closed\s+(\w+)',
        ]
        
        closed_days = []
        for pattern in closed_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    closed_days.extend(match)
                else:
                    closed_days.append(match)
        
        if closed_days:
            hours_data['days_closed'] = ', '.join(set(closed_days))
        
        return hours_data

    def normalize_time(self, time_parts: tuple) -> str:
        """
        Normalize time format to HH:MM AM/PM
        """
        try:
            if not time_parts or not time_parts[0]:
                return ''
            
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 and time_parts[1] else 0
            am_pm = time_parts[2] if len(time_parts) > 2 and time_parts[2] else ''
            
            # Handle 24-hour format conversion
            if not am_pm:
                if hour >= 12:
                    am_pm = 'PM'
                    if hour > 12:
                        hour -= 12
                else:
                    am_pm = 'AM'
                    if hour == 0:
                        hour = 12
            
            return f"{hour:02d}:{minute:02d} {am_pm.upper()}"
        
        except (ValueError, IndexError):
            return ''

    def extract_from_google_apis(self, practitioner_name: str) -> Dict:
        """
        Extract information using Google APIs when clinic website is not available
        """
        data = {
            'booking_url': '',
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': '',
            'clinic_website': ''
        }
        
        if not self.google_api_key:
            logging.warning(f"   ⚠️  No Google API key provided")
            return data
        
        try:
            # Search for the practitioner using Google Places API
            places_data = self.search_google_places(practitioner_name)
            
            if places_data:
                # Extract website if found
                if 'website' in places_data:
                    data['clinic_website'] = places_data['website']
                    # Now extract from the found website
                    website_data = self.extract_from_website(places_data['website'])
                    data.update(website_data)
                
                # Extract hours from Google Places data
                if 'opening_hours' in places_data:
                    hours_data = self.parse_google_hours(places_data['opening_hours'])
                    data.update(hours_data)
                
                logging.info(f"   ✅ Found data via Google APIs")
            else:
                logging.info(f"   ❌ No data found via Google APIs")
        
        except Exception as e:
            logging.error(f"   ❌ Error with Google APIs: {e}")
        
        return data

    def search_google_places(self, practitioner_name: str) -> Dict:
        """
        Search for practitioner using Google Places API
        """
        try:
            # Google Places Text Search API
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            
            params = {
                'query': f"{practitioner_name} physiotherapy BC Canada",
                'key': self.google_api_key,
                'fields': 'name,website,opening_hours,formatted_address'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('results'):
                    # Return the first result
                    place = data['results'][0]
                    
                    # Get detailed information
                    if 'place_id' in place:
                        details = self.get_place_details(place['place_id'])
                        if details:
                            return details
                    
                    return place
            
        except Exception as e:
            logging.error(f"Google Places search error: {e}")
        
        return {}

    def get_place_details(self, place_id: str) -> Dict:
        """
        Get detailed place information using Google Places Details API
        """
        try:
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            
            params = {
                'place_id': place_id,
                'key': self.google_api_key,
                'fields': 'name,website,opening_hours,formatted_address'
            }
            
            response = requests.get(details_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', {})
        
        except Exception as e:
            logging.error(f"Google Places details error: {e}")
        
        return {}

    def parse_google_hours(self, opening_hours: Dict) -> Dict:
        """
        Parse Google Places opening hours format
        """
        hours_data = {
            'weekday_earliest_am': '',
            'weekday_latest_pm': '',
            'weekend_earliest_am': '',
            'weekend_latest_pm': '',
            'days_closed': ''
        }
        
        try:
            if 'weekday_text' in opening_hours:
                weekday_hours = []
                weekend_hours = []
                closed_days = []
                
                for day_hours in opening_hours['weekday_text']:
                    day_lower = day_hours.lower()
                    
                    if 'closed' in day_lower:
                        # Extract day name
                        day_match = re.match(r'(\w+):', day_hours)
                        if day_match:
                            closed_days.append(day_match.group(1))
                    else:
                        # Extract hours
                        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)\s*–\s*(\d{1,2}):(\d{2})\s*(am|pm)', day_lower)
                        
                        if time_match:
                            start_time = f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3).upper()}"
                            end_time = f"{time_match.group(4)}:{time_match.group(5)} {time_match.group(6).upper()}"
                            
                            # Determine if weekday or weekend
                            if any(day in day_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
                                weekday_hours.append((start_time, end_time))
                            elif any(day in day_lower for day in ['saturday', 'sunday']):
                                weekend_hours.append((start_time, end_time))
                
                # Set the most common weekday hours
                if weekday_hours:
                    hours_data['weekday_earliest_am'] = weekday_hours[0][0]
                    hours_data['weekday_latest_pm'] = weekday_hours[0][1]
                
                # Set weekend hours
                if weekend_hours:
                    hours_data['weekend_earliest_am'] = weekend_hours[0][0]
                    hours_data['weekend_latest_pm'] = weekend_hours[0][1]
                
                # Set closed days
                if closed_days:
                    hours_data['days_closed'] = ', '.join(closed_days)
        
        except Exception as e:
            logging.error(f"Error parsing Google hours: {e}")
        
        return hours_data

def process_practitioners_batch(practitioners_data: List[Dict], google_api_key: str = None) -> List[Dict]:
    """
    Process a batch of practitioners
    practitioners_data: List of dicts with 'name' and optionally 'clinic_website'
    """
    extractor = ComprehensiveBookingExtractor(google_api_key)
    results = []
    
    logging.info(f"🚀 Processing {len(practitioners_data)} practitioners")
    
    for i, practitioner in enumerate(practitioners_data, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"PROCESSING {i}/{len(practitioners_data)}")
        logging.info(f"{'='*60}")
        
        name = practitioner.get('name', '')
        website = practitioner.get('clinic_website', '')
        
        if not name:
            logging.warning("⚠️  No practitioner name provided")
            continue
        
        result = extractor.extract_practitioner_data(name, website)
        results.append(result)
        
        # Rate limiting
        time.sleep(2)
    
    return results

def main():
    """
    Example usage of the comprehensive booking extractor
    """
    # Example practitioners data
    practitioners_data = [
        {
            'name': 'Dr. John Smith',
            'clinic_website': 'https://example-physio.com'
        },
        {
            'name': 'Dr. Jane Doe',
            'clinic_website': ''  # Will use Google APIs
        },
        {
            'name': 'Dr. Mike Johnson'
            # No website provided - will use Google APIs
        }
    ]
    
    # Set your Google API key here (optional)
    google_api_key = os.getenv('GOOGLE_API_KEY')  # Set as environment variable
    
    # Process practitioners
    results = process_practitioners_batch(practitioners_data, google_api_key)
    
    # Convert to DataFrame and save
    df = pd.DataFrame(results)
    df.to_csv('comprehensive_booking_results.csv', index=False)
    
    # Display results
    logging.info(f"\n{'='*60}")
    logging.info(f"PROCESSING COMPLETE")
    logging.info(f"{'='*60}")
    logging.info(f"✅ Processed: {len(results)} practitioners")
    
    booking_count = len([r for r in results if r.get('booking_url')])
    hours_count = len([r for r in results if r.get('weekday_earliest_am')])
    
    logging.info(f"🔗 Booking URLs found: {booking_count}/{len(results)}")
    logging.info(f"⏰ Operating hours found: {hours_count}/{len(results)}")
    logging.info(f"📁 Results saved to: comprehensive_booking_results.csv")

if __name__ == "__main__":
    main()
