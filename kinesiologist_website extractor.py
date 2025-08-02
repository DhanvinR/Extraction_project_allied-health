#!/usr/bin/env python3
"""
BC Association of Kinesiologists Scraper - Next 200 (101-300)
Enhanced website finding for the next 200 kinesiologists with checkpoint saving every 25
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KinesiologistNext200:
    def __init__(self):
        self.base_url = "https://bcak.bc.ca"
        self.search_url = "https://bcak.bc.ca/find-a-kinesiologist/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.max_practitioners = 200
        self.checkpoint_interval = 25
        self.practitioners_processed = 0
        self.target_start = 100  # Start from the 101st practitioner
        
        # Statistics
        self.total_attempts = 0
        self.successful_website_finds = 0
        self.google_blocked = False
        
        # Healthcare keywords for website validation
        self.healthcare_keywords = [
            'physiotherapy', 'kinesiology', 'rehabilitation', 'therapy', 'clinic', 'health',
            'wellness', 'fitness', 'exercise', 'treatment', 'medical', 'healthcare',
            'physio', 'kinesiologist', 'therapist', 'recovery', 'injury', 'pain',
            'massage', 'chiropractic', 'osteopathy', 'acupuncture', 'sports medicine'
        ]
    
    def extract_practitioners_from_page(self, page_num: int) -> List[Dict]:
        """Extract basic practitioner info from a search results page"""
        url = f"{self.search_url}?page={page_num}&keywords=&areas_of_specialization=&city=&region=&languages=&gender="
        logger.info(f"Scraping page {page_num}: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            practitioners = []
            practitioner_cards = soup.find_all('div', class_='card')
            
            for card in practitioner_cards:
                try:
                    # Extract name and profile URL from the subtitle link
                    subtitle = card.find('h3', class_='subtitle')
                    if not subtitle:
                        continue
                    
                    name_link = subtitle.find('a', href=True)
                    if not name_link:
                        continue
                    
                    name = name_link.get_text(strip=True)
                    if not name:
                        continue
                        
                    profile_url = urljoin(self.base_url, name_link['href'])
                    
                    # Extract basic info from card content using the info-list structure
                    card_content = card.find('div', class_='card-content')
                    if not card_content:
                        continue
                    
                    # Find the info-list (dl element)
                    info_list = card_content.find('dl', class_='info-list')
                    
                    # Extract gender
                    gender = "Not specified"
                    gender_dt = info_list.find('dt', string='Gender') if info_list else None
                    if gender_dt and gender_dt.find_next_sibling('dd'):
                        gender = gender_dt.find_next_sibling('dd').get_text(strip=True)
                    
                    # Extract practice area
                    practice_area = "Not specified"
                    practice_dt = info_list.find('dt', string='Practice Area') if info_list else None
                    if practice_dt and practice_dt.find_next_sibling('dd'):
                        practice_area = practice_dt.find_next_sibling('dd').get_text(strip=True)
                    
                    # Extract workplace
                    workplace = "Not specified"
                    workplace_dt = info_list.find('dt', string='Workplace') if info_list else None
                    if workplace_dt and workplace_dt.find_next_sibling('dd'):
                        workplace_dd = workplace_dt.find_next_sibling('dd')
                        workplace_text = workplace_dd.get_text(separator=' ', strip=True)
                        workplace = re.sub(r'^[A-Z]\s+', '', workplace_text).strip()
                    
                    practitioner = {
                        'name': name,
                        'gender': gender,
                        'practice_area': practice_area,
                        'workplace': workplace,
                        'profile_url': profile_url
                    }
                    
                    practitioners.append(practitioner)
                    logger.info(f"Extracted basic info for: {name}")
                    
                    # Small delay between extractions
                    time.sleep(random.uniform(0.3, 1.0))
                    
                except Exception as e:
                    logger.warning(f"Error extracting practitioner from card: {e}")
                    continue
            
            logger.info(f"Found {len(practitioners)} unique practitioners on page {page_num}")
            return practitioners
            
        except Exception as e:
            logger.error(f"Error scraping page {page_num}: {e}")
            return []
    
    def extract_clinic_locations_from_profile(self, profile_url: str) -> List[Dict]:
        """Extract clinic locations from a practitioner's profile page"""
        try:
            response = self.session.get(profile_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            clinic_locations = []
            
            # Find the maps section that contains clinic locations
            maps_section = soup.find('div', class_='public-profile__maps')
            if not maps_section:
                logger.info(f"No maps section found in profile")
                return []
            
            # Find all clinic cards within the maps section
            clinic_cards = maps_section.find_all('div', class_='card-content')
            logger.info(f"Found {len(clinic_cards)} clinic cards in profile")
            
            for card in clinic_cards:
                try:
                    # Extract clinic name and address from the card
                    text_content = card.get_text(separator='\n', strip=True)
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    
                    if len(lines) >= 2:
                        clinic_name = lines[0]
                        # Join remaining lines as address (some addresses span multiple lines)
                        address = ' '.join(lines[1:])
                        
                        # Clean up the address
                        address = re.sub(r'\s+', ' ', address).strip()
                        
                        # Validate that this looks like a real clinic location
                        if self.is_valid_clinic_location(clinic_name, address):
                            clinic_locations.append({
                                'clinic_name': clinic_name,
                                'address': address,
                                'website': ''  # Will be populated by website search
                            })
                            logger.info(f"✅ Found clinic: {clinic_name}")
                        else:
                            logger.info(f"⏭️  Skipped invalid location: {clinic_name}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing clinic card: {e}")
                    continue
            
            logger.info(f"📍 Extracted {len(clinic_locations)} valid clinic locations")
            return clinic_locations
            
        except Exception as e:
            logger.error(f"Error extracting clinic locations from {profile_url}: {e}")
            return []
    
    def is_valid_clinic_location(self, clinic_name: str, address: str) -> bool:
        """Validate if a clinic location is legitimate"""
        # Skip navigation elements and generic text
        invalid_patterns = [
            'about bcak', 'contact us', 'get in touch', 'gender', 'practice area',
            'clinical care resources', 'public information', 'telehealth services',
            'all rights reserved', 'british columbia association', 'passionate about',
            'lifelong learner', 'encourager and listener'
        ]
        
        clinic_lower = clinic_name.lower()
        address_lower = address.lower()
        
        # Check if clinic name contains invalid patterns
        for pattern in invalid_patterns:
            if pattern in clinic_lower:
                return False
        
        # Must have a reasonable clinic name (not just description text)
        if len(clinic_name) > 200:
            return False
        
        # Must have an address with some geographic indicators
        if not address or len(address) < 10:
            return False
        
        # Should contain some address-like elements
        address_indicators = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'way', 'drive', 'dr', 
                             'boulevard', 'blvd', 'lane', 'ln', 'place', 'pl', 'court', 'ct',
                             'british columbia', 'bc', 'canada', 'vancouver', 'burnaby', 'richmond',
                             'surrey', 'langley', 'abbotsford', 'chilliwack', 'coquitlam', 'delta']
        
        has_address_indicator = any(indicator in address_lower for indicator in address_indicators)
        
        return has_address_indicator
    
    def search_clinic_website_multiple_methods(self, clinic_name: str, address: str) -> Optional[str]:
        """Search for clinic website using multiple methods with rate limiting protection"""
        self.total_attempts += 1
        
        # Method 1: Try Google search with longer delays
        website = self.search_google_with_backoff(clinic_name, address)
        if website:
            return website
        
        # Method 2: Try domain guessing (most effective method)
        website = self.guess_clinic_domain(clinic_name)
        if website:
            return website
        
        # Method 3: Try DuckDuckGo search (if available)
        website = self.search_duckduckgo(clinic_name, address)
        if website:
            return website
        
        return None
    
    def search_google_with_backoff(self, clinic_name: str, address: str) -> Optional[str]:
        """Search Google with exponential backoff for rate limiting"""
        if self.google_blocked:
            logger.info(f"⏭️  Skipping Google search (blocked) for: {clinic_name}")
            return None
        
        try:
            city = self.extract_city_from_address(address)
            search_query = f'"{clinic_name}" {city} website'
            
            logger.info(f"🔍 Searching Google for: {search_query}")
            
            # Use Google search with longer delays
            from googlesearch import search
            
            # Add random delay before search to avoid rate limiting
            time.sleep(random.uniform(2, 5))
            
            for url in search(search_query, num_results=3, sleep_interval=2):
                if self.is_legitimate_healthcare_website(url, clinic_name):
                    logger.info(f"✅ Found legitimate website: {url}")
                    self.successful_website_finds += 1
                    return url
            
            logger.info(f"❌ No legitimate website found for {clinic_name}")
            return None
            
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                logger.warning(f"🚫 Google rate limiting detected - switching to alternative methods")
                self.google_blocked = True
            else:
                logger.warning(f"Error searching Google: {e}")
            return None
    
    def guess_clinic_domain(self, clinic_name: str) -> Optional[str]:
        """Try to guess clinic domain based on name"""
        try:
            # Clean clinic name for domain guessing
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', clinic_name.lower())
            words = clean_name.split()
            
            # Try common domain patterns
            domain_patterns = [
                ''.join(words) + '.com',
                ''.join(words) + '.ca',
                ''.join(words[:2]) + '.com' if len(words) > 1 else None,
                ''.join(words[:2]) + '.ca' if len(words) > 1 else None,
                words[0] + 'clinic.com' if len(words) > 0 else None,
                words[0] + 'rehab.ca' if len(words) > 0 else None,
                words[0] + 'fitness.com' if len(words) > 0 else None,
                words[0] + 'health.ca' if len(words) > 0 else None,
            ]
            
            for pattern in domain_patterns:
                if pattern and len(pattern) > 6:  # Reasonable domain length
                    url = f"https://www.{pattern}"
                    if self.check_domain_exists(url, clinic_name):
                        logger.info(f"✅ Found website by domain guessing: {url}")
                        self.successful_website_finds += 1
                        return url
            
            return None
            
        except Exception as e:
            logger.warning(f"Error in domain guessing: {e}")
            return None
    
    def check_domain_exists(self, url: str, clinic_name: str) -> bool:
        """Check if a guessed domain exists and is relevant"""
        try:
            response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                content = response.text.lower()
                clinic_words = clinic_name.lower().split()
                
                # Check if clinic name appears in content
                clinic_score = sum(1 for word in clinic_words if len(word) > 3 and word in content)
                
                # Check for healthcare keywords
                healthcare_score = sum(1 for keyword in self.healthcare_keywords[:10] if keyword in content)
                
                return clinic_score >= 1 and healthcare_score >= 2
                
        except:
            pass
        
        return False
    
    def search_duckduckgo(self, clinic_name: str, address: str) -> Optional[str]:
        """Search using DuckDuckGo as alternative to Google"""
        try:
            # Simple DuckDuckGo search implementation
            city = self.extract_city_from_address(address)
            search_query = f"{clinic_name} {city} website"
            
            logger.info(f"🦆 Searching DuckDuckGo for: {search_query}")
            
            # DuckDuckGo instant answer API
            params = {
                'q': search_query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get('https://api.duckduckgo.com/', params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check for relevant URLs in the response
                for result in data.get('Results', []):
                    url = result.get('FirstURL', '')
                    if url and self.is_legitimate_healthcare_website(url, clinic_name):
                        logger.info(f"✅ Found website via DuckDuckGo: {url}")
                        self.successful_website_finds += 1
                        return url
            
            return None
            
        except Exception as e:
            logger.warning(f"Error searching DuckDuckGo: {e}")
            return None
    
    def extract_city_from_address(self, address: str) -> str:
        """Extract city name from address"""
        # Look for common BC city patterns
        bc_cities = ['Vancouver', 'Burnaby', 'Richmond', 'Surrey', 'Langley', 'Abbotsford', 
                     'Chilliwack', 'Coquitlam', 'Delta', 'New Westminster', 'North Vancouver',
                     'West Vancouver', 'Port Coquitlam', 'Port Moody', 'Maple Ridge', 'Pitt Meadows']
        
        for city in bc_cities:
            if city.lower() in address.lower():
                return city
        
        # Fallback: try to extract city from address pattern
        parts = address.split(',')
        if len(parts) >= 2:
            return parts[-3].strip() if len(parts) >= 3 else parts[-2].strip()
        
        return "BC"
    
    def is_legitimate_healthcare_website(self, url: str, clinic_name: str) -> bool:
        """Check if a URL is a legitimate healthcare website"""
        try:
            # Skip obviously irrelevant domains
            domain = urlparse(url).netloc.lower()
            
            # Skip search engines, social media, directories, etc.
            skip_domains = [
                'google.com', 'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
                'yelp.com', 'yellowpages.ca', 'canada411.ca', 'wikipedia.org', 'bcak.bc.ca',
                'translate.google.com', 'maps.google.com', 'youtube.com', 'pinterest.com'
            ]
            
            if any(skip_domain in domain for skip_domain in skip_domains):
                return False
            
            # Check if URL contains clinic-related keywords
            url_lower = url.lower()
            clinic_lower = clinic_name.lower()
            
            # Look for clinic name in URL
            clinic_words = clinic_lower.split()
            if len(clinic_words) >= 2:
                # Check if at least one significant word from clinic name is in URL
                significant_words = [word for word in clinic_words if len(word) > 3]
                if significant_words and any(word in url_lower for word in significant_words):
                    return True
            
            # Check for healthcare-related domains
            healthcare_domains = [
                'clinic', 'health', 'physio', 'therapy', 'rehab', 'wellness', 'medical',
                'kinesiology', 'fitness', 'exercise', 'treatment', 'care'
            ]
            
            if any(keyword in domain for keyword in healthcare_domains):
                return True
            
            # Try to fetch and analyze content
            try:
                response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Check for healthcare keywords in content
                    healthcare_score = sum(1 for keyword in self.healthcare_keywords if keyword in content)
                    
                    # Check for clinic name in content
                    clinic_score = sum(1 for word in clinic_lower.split() if len(word) > 3 and word in content)
                    
                    # Must have reasonable healthcare content and some clinic name match
                    return healthcare_score >= 3 and clinic_score >= 1
                    
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Error validating website {url}: {e}")
            return False
    
    def get_detailed_profile(self, practitioner: Dict) -> Dict:
        """Get detailed profile information including clinic locations"""
        logger.info(f"Getting detailed profile for: {practitioner['name']}")
        
        # Extract clinic locations from profile page
        clinic_locations = self.extract_clinic_locations_from_profile(practitioner['profile_url'])
        
        # Search for websites for each clinic location (limit to first 2 to manage time)
        for i, location in enumerate(clinic_locations[:2]):
            if location['clinic_name'] and location['address']:
                website = self.search_clinic_website_multiple_methods(location['clinic_name'], location['address'])
                location['website'] = website or ''
                
                # Shorter delay between website searches for efficiency
                time.sleep(random.uniform(3, 6))
        
        # Add clinic locations to practitioner data
        practitioner['clinic_locations'] = clinic_locations
        
        logger.info(f"📍 Found {len(clinic_locations)} clinic locations for {practitioner['name']}")
        return practitioner
    
    def save_to_csv(self, practitioners: List[Dict], filename: str):
        """Save practitioner data to CSV file with up to 10 clinic locations"""
        if not practitioners:
            logger.warning("No practitioners to save")
            return
        
        logger.info(f"💾 Saving {len(practitioners)} practitioners to {filename}")
        
        # Create fieldnames for up to 10 clinic locations
        fieldnames = ['name', 'gender', 'practice_area', 'workplace', 'profile_url']
        for i in range(1, 11):  # Support up to 10 clinic locations
            fieldnames.extend([
                f'clinic_name_{i}', 
                f'clinic_address_{i}', 
                f'clinic_website_{i}'
            ])
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for practitioner in practitioners:
                row = {
                    'name': practitioner['name'],
                    'gender': practitioner['gender'],
                    'practice_area': practitioner['practice_area'],
                    'workplace': practitioner['workplace'],
                    'profile_url': practitioner['profile_url']
                }
                
                # Add clinic locations (up to 10)
                for i, location in enumerate(practitioner['clinic_locations'][:10], 1):
                    row[f'clinic_name_{i}'] = location['clinic_name']
                    row[f'clinic_address_{i}'] = location['address']
                    row[f'clinic_website_{i}'] = location['website']
                
                writer.writerow(row)
        
        logger.info(f"✅ Data saved to {filename}")
    
    def print_progress_summary(self, practitioners: List[Dict], checkpoint_num: int, total_processed: int):
        """Print a summary of progress at checkpoint"""
        total_locations = sum(len(p['clinic_locations']) for p in practitioners)
        websites_found = sum(1 for p in practitioners for loc in p['clinic_locations'] if loc['website'])
        
        print(f"\n📊 CHECKPOINT {checkpoint_num} SUMMARY (Practitioners {total_processed-len(practitioners)+1}-{total_processed}):")
        print(f"   - Practitioners in this batch: {len(practitioners)}")
        print(f"   - Total clinic locations: {total_locations}")
        print(f"   - Websites found: {websites_found}")
        print(f"   - Website search attempts: {self.total_attempts}")
        print(f"   - Successful website finds: {self.successful_website_finds}")
        
        if self.total_attempts > 0:
            success_rate = (self.successful_website_finds / self.total_attempts) * 100
            print(f"   - Website success rate: {success_rate:.1f}%")
        
        if total_locations > 0:
            location_success_rate = (websites_found / total_locations) * 100
            print(f"   - Locations with websites: {location_success_rate:.1f}%")
    
    def scrape_next_200_practitioners(self) -> List[Dict]:
        """Scrape the next 200 practitioners (101-300) with checkpoint saving"""
        all_practitioners = []
        page_num = 1
        checkpoint_count = 0
        practitioners_seen = 0  # Track how many we've seen total
        
        print(f"🚀 Starting scrape for the NEXT 200 kinesiologists (practitioners 101-300)...")
        print(f"💾 Checkpoint saving every {self.checkpoint_interval} practitioners")
        print(f"⏭️  Skipping first {self.target_start} practitioners to continue from where we left off")
        
        while len(all_practitioners) < self.max_practitioners:
            practitioners = self.extract_practitioners_from_page(page_num)
            
            if not practitioners:
                logger.info(f"No more practitioners found on page {page_num}")
                break
            
            for practitioner in practitioners:
                practitioners_seen += 1
                
                # Skip practitioners until we reach our target start point
                if practitioners_seen <= self.target_start:
                    logger.info(f"⏭️  Skipping practitioner {practitioners_seen}: {practitioner['name']} (already processed)")
                    continue
                
                if len(all_practitioners) >= self.max_practitioners:
                    break
                
                detailed_practitioner = self.get_detailed_profile(practitioner)
                
                # Only include practitioners with clinic locations (addresses)
                if detailed_practitioner['clinic_locations']:
                    all_practitioners.append(detailed_practitioner)
                    current_number = self.target_start + len(all_practitioners)
                    logger.info(f"✅ Added {detailed_practitioner['name']} - practitioner #{current_number} - has {len(detailed_practitioner['clinic_locations'])} clinic locations")
                    
                    # Check if we need to save a checkpoint
                    if len(all_practitioners) % self.checkpoint_interval == 0:
                        checkpoint_count += 1
                        current_total = self.target_start + len(all_practitioners)
                        checkpoint_filename = f'kinesiologists_200_checkpoint_{current_total}.csv'
                        self.save_to_csv(all_practitioners, checkpoint_filename)
                        self.print_progress_summary(all_practitioners, checkpoint_count, current_total)
                        print(f"💾 Checkpoint saved: {checkpoint_filename}")
                        print(f"🔄 Continuing to process remaining practitioners...\n")
                        
                else:
                    current_number = self.target_start + len(all_practitioners) + 1
                    logger.info(f"⏭️  Skipped {detailed_practitioner['name']} - practitioner #{current_number} - no clinic addresses")
                
                logger.info(f"Processed {len(all_practitioners)} new practitioners with clinic addresses")
                
                # Shorter delay between practitioners for efficiency
                time.sleep(random.uniform(3, 6))
            
            page_num += 1
            time.sleep(random.uniform(5, 10))  # Pause between pages
        
        return all_practitioners

def main():
    """Main function to run the scraper for the next 200 kinesiologists"""
    print("BC Association of Kinesiologists Scraper - Next 200 (Practitioners 101-300)")
    print("=" * 85)
    print("Enhanced website finding for the next 200 kinesiologists with checkpoint saving every 25")
    
    scraper = KinesiologistNext200()
    
    try:
        practitioners = scraper.scrape_next_200_practitioners()
        
        if practitioners:
            # Save final results
            final_filename = 'kinesiologists_next_200_final.csv'
            scraper.save_to_csv(practitioners, final_filename)
            
            print(f"\n🎉 FINAL RESULTS - Next 200 scrape completed!")
            print(f"✅ Processed {len(practitioners)} NEW practitioners with clinic addresses (practitioners 101-{100 + len(practitioners)})")
            print(f"💾 Final data saved to '{final_filename}'")
            
            # Show final summary statistics
            total_locations = sum(len(p['clinic_locations']) for p in practitioners)
            websites_found = sum(1 for p in practitioners for loc in p['clinic_locations'] if loc['website'])
            
            print(f"\n📊 Final Summary Statistics:")
            print(f"   - NEW practitioners processed: {len(practitioners)}")
            print(f"   - Total clinic locations: {total_locations}")
            print(f"   - Websites found: {websites_found}")
            print(f"   - Website search attempts: {scraper.total_attempts}")
            print(f"   - Successful website finds: {scraper.successful_website_finds}")
            
            if scraper.total_attempts > 0:
                success_rate = (scraper.successful_website_finds / scraper.total_attempts) * 100
                print(f"   - Website success rate: {success_rate:.1f}%")
            
            if total_locations > 0:
                location_success_rate = (websites_found / total_locations) * 100
                print(f"   - Locations with websites: {location_success_rate:.1f}%")
            
            print(f"\n🎯 Data Quality Features:")
            print(f"   - ✅ Complete practitioner profiles")
            print(f"   - ✅ Detailed clinic locations with addresses")
            print(f"   - ✅ Website discovery using multiple methods")
            print(f"   - ✅ Rate limiting protection")
            print(f"   - ✅ Checkpoint saving every 25 practitioners")
            print(f"   - ✅ Continuation from previous batches (practitioners 101+)")
            
            # List checkpoint files created
            checkpoint_files = [f for f in os.listdir('.') if f.startswith('kinesiologists_200_checkpoint_')]
            if checkpoint_files:
                print(f"\n💾 Checkpoint files created:")
                for file in sorted(checkpoint_files):
                    print(f"   - {file}")
            
            print(f"\n📈 Combined Progress:")
            print(f"   - First batch: 50 practitioners (1-50)")
            print(f"   - Second batch: 50 practitioners (51-100)")
            print(f"   - Current batch: {len(practitioners)} practitioners (101-{100 + len(practitioners)})")
            print(f"   - Total processed: {100 + len(practitioners)} practitioners")
            
        else:
            print("No new practitioners with clinic addresses found.")
            
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        print("💾 Progress has been saved in checkpoint files")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        print(f"❌ Error: {e}")
        print("💾 Any progress made has been saved in checkpoint files")

if __name__ == "__main__":
    main()
