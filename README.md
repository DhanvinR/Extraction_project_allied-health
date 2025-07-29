"Hello everyone, Sorry this took a while to automate  it was quite complex. The instructions are in the README file . All you need to do is create an Excel file with the columns named according to the instructions, then run the script. It will automatically extract the booking links.I recommend running it in batches of 20–50 and spot-checking for accuracy. This is just a tool to speed up the process, but I still advise manually verifying the results. Based on my calculations, the accuracy is around 90%. I’ll work on automating the rest of the allied health professionals next and will update you soon."

# Comprehensive Booking Extractor - Setup Guide

A complete guide to set up and run the healthcare practitioner booking URL and operating hours extractor on any laptop with Python 3.

## 📋 Prerequisites

- **Python 3.7 or higher** installed on your system
- **Internet connection** for web scraping and API calls
- **Terminal/Command Prompt** access

## 🚀 Quick Setup (5 minutes)

### Step 1: Download the Script Files

Download these files to a folder on your laptop:
- `comprehensive_booking_extractor.py` (main script)
- `example_usage.py` (usage examples)
- `README_booking_extractor.md` (detailed documentation)

### Step 2: Install Required Packages

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:

```bash
pip install requests beautifulsoup4 pandas
```

**Alternative for Python 3 specifically:**
```bash
pip3 install requests beautifulsoup4 pandas
```

### Step 3: Test the Installation

Navigate to your script folder and test:

```bash
cd /path/to/your/script/folder
python3 -c "import requests, bs4, pandas; print('✅ All packages installed successfully!')"
```

### Step 4: Run Your First Test

```bash
python3 example_usage.py
```

## 📁 File Structure

Your project folder should look like this:
```
booking_extractor/
├── comprehensive_booking_extractor.py    # Main script
├── example_usage.py                      # Usage examples
├── README_booking_extractor.md           # Detailed documentation
├── README_SETUP_GUIDE.md                # This setup guide
└── results/                              # Output folder (created automatically)
    ├── test_results.csv
    └── comprehensive_booking_results.csv
```

## 🔧 Detailed Setup Instructions

### For Windows Users

1. **Check Python Installation:**
   ```cmd
   python --version
   ```
   or
   ```cmd
   python3 --version
   ```

2. **Install Packages:**
   ```cmd
   pip install requests beautifulsoup4 pandas
   ```

3. **Run Script:**
   ```cmd
   python comprehensive_booking_extractor.py
   ```

### For Mac Users

1. **Check Python Installation:**
   ```bash
   python3 --version
   ```

2. **Install Packages:**
   ```bash
   pip3 install requests beautifulsoup4 pandas
   ```

3. **Run Script:**
   ```bash
   python3 comprehensive_booking_extractor.py
   ```

### For Linux Users

1. **Install Python 3 (if not installed):**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

2. **Install Packages:**
   ```bash
   pip3 install requests beautifulsoup4 pandas
   ```

3. **Run Script:**
   ```bash
   python3 comprehensive_booking_extractor.py
   ```

## 🎯 Basic Usage Examples

### Example 1: Single Practitioner with Website

Create a file called `test_single.py`:

```python
from comprehensive_booking_extractor import ComprehensiveBookingExtractor

# Initialize extractor
extractor = ComprehensiveBookingExtractor()

# Extract data
result = extractor.extract_practitioner_data(
    practitioner_name="Dr. John Smith",
    clinic_website="https://example-clinic.com"
)

# Print results
print("Results:")
for key, value in result.items():
    print(f"  {key}: {value}")
```

Run it:
```bash
python3 test_single.py
```

### Example 2: Batch Processing

Create a file called `test_batch.py`:

```python
from comprehensive_booking_extractor import process_practitioners_batch
import pandas as pd

# Your practitioners data
practitioners_data = [
    {'name': 'Justin Chipperfield', 'clinic_website': 'https://www.chipperfieldphysio.ca/team'},
    {'name': 'Cathy Crawley', 'clinic_website': 'https://www.portcoquitlamphysio.com/'},
    {'name': 'Kirk Boechler', 'clinic_website': 'https://physicalpursuit.ca/'},
]

# Process practitioners
results = process_practitioners_batch(practitioners_data)

# Save to CSV
df = pd.DataFrame(results)
df.to_csv('my_results.csv', index=False)

print(f"✅ Processed {len(results)} practitioners")
print("📁 Results saved to: my_results.csv")
```

Run it:
```bash
python3 test_batch.py
```

### Example 3: Process from CSV File

If you have a CSV file with practitioner data:

```python
import pandas as pd
from comprehensive_booking_extractor import process_practitioners_batch

# Load your CSV file
df = pd.read_csv('your_practitioners.csv')

# Convert to required format
practitioners_data = []
for _, row in df.iterrows():
    practitioners_data.append({
        'name': row['practitioner_name'],  # Adjust column name as needed
        'clinic_website': row.get('clinic_website', '')  # Adjust column name as needed
    })

# Process
results = process_practitioners_batch(practitioners_data)

# Save enhanced results
enhanced_df = pd.DataFrame(results)
enhanced_df.to_csv('enhanced_results.csv', index=False)

print("✅ Processing complete!")
```

## 🌐 Google APIs Setup (Optional but Recommended)

For practitioners without clinic websites, the script can use Google APIs as a fallback.

### Step 1: Get Google API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Places API**
4. Create credentials → API Key
5. Copy your API key

### Step 2: Set Up API Key

**Option A: Environment Variable (Recommended)**
```bash
# Mac/Linux
export GOOGLE_API_KEY='your_api_key_here'

# Windows
set GOOGLE_API_KEY=your_api_key_here
```

**Option B: Direct in Code**
```python
from comprehensive_booking_extractor import ComprehensiveBookingExtractor

extractor = ComprehensiveBookingExtractor(google_api_key='your_api_key_here')
```

### Step 3: Test Google APIs

```python
from comprehensive_booking_extractor import ComprehensiveBookingExtractor

extractor = ComprehensiveBookingExtractor(google_api_key='your_key')

# Test with practitioner without website
result = extractor.extract_practitioner_data(
    practitioner_name="Dr. Smith Physiotherapy Vancouver BC"
    # No clinic_website provided - will use Google APIs
)

print("Google API Result:", result)
```

## 📊 Understanding the Output

The script returns data in this format:

```python
{
    'practitioner_name': 'Dr. John Smith',           # Input name
    'clinic_website': 'https://example.com',        # Input or found website
    'booking_url': 'https://clinic.janeapp.com/',   # Found booking URL
    'weekday_earliest_am': '08:00 AM',              # Weekday opening time
    'weekday_latest_pm': '05:00 PM',                # Weekday closing time
    'weekend_earliest_am': '09:00 AM',              # Weekend opening time
    'weekend_latest_pm': '02:00 PM',                # Weekend closing time
    'days_closed': 'Sunday',                        # Days when closed
    'data_source': 'clinic_website'                 # Where data came from
}
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. "Module not found" Error
```
ModuleNotFoundError: No module named 'requests'
```
**Solution:**
```bash
pip3 install requests beautifulsoup4 pandas
```

#### 2. "Permission denied" Error
**Solution:**
```bash
# Mac/Linux
sudo pip3 install requests beautifulsoup4 pandas

# Or use user installation
pip3 install --user requests beautifulsoup4 pandas
```

#### 3. Python Command Not Found
**Solution:**
- Windows: Use `python` instead of `python3`
- Mac: Install Python 3 from [python.org](https://python.org)
- Linux: `sudo apt install python3`

#### 4. SSL Certificate Errors
**Solution:**
```bash
pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org requests beautifulsoup4 pandas
```

#### 5. Slow Performance
**Causes & Solutions:**
- **Slow internet**: Script waits for website responses
- **Many practitioners**: Use smaller batches
- **Rate limiting**: Built-in delays prevent server overload

### Debug Mode

Enable detailed logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from comprehensive_booking_extractor import ComprehensiveBookingExtractor
# Your code here...
```

## 📈 Performance Expectations

- **Single practitioner**: 3-5 seconds
- **Batch of 10**: 30-50 seconds  
- **With Google APIs**: +1-2 seconds per practitioner
- **Success rate**: 70-90% for booking URLs, 30-60% for hours

## 🔒 Best Practices

### 1. Rate Limiting
The script includes built-in delays. Don't remove them to avoid being blocked by websites.

### 2. Error Handling
Always check results for empty values:
```python
if result['booking_url']:
    print(f"✅ Found booking URL: {result['booking_url']}")
else:
    print("❌ No booking URL found")
```

### 3. Data Validation
Verify important results manually for critical applications.

### 4. Batch Processing
Process large datasets in smaller batches (10-20 practitioners) to avoid timeouts.

## 📝 Sample Data Format

### Input CSV Format
```csv
practitioner_name,clinic_website
Dr. John Smith,https://example-clinic.com
Dr. Jane Doe,https://another-clinic.com
Dr. Mike Johnson,
```

### Output CSV Format
```csv
practitioner_name,clinic_website,booking_url,weekday_earliest_am,weekday_latest_pm,weekend_earliest_am,weekend_latest_pm,days_closed,data_source
Dr. John Smith,https://example-clinic.com,https://clinic.janeapp.com/,08:00 AM,05:00 PM,09:00 AM,02:00 PM,Sunday,clinic_website
```

## 🆘 Getting Help

### Check These First:
1. **Python version**: `python3 --version` (should be 3.7+)
2. **Package installation**: `pip3 list | grep requests`
3. **Internet connection**: Can you browse websites normally?
4. **File permissions**: Can you create files in the script directory?

### Common Solutions:
- **Restart terminal** after installing packages
- **Use full file paths** if script can't find files
- **Check firewall settings** if network requests fail
- **Try different Python command**: `python` vs `python3`

## 🎉 You're Ready!

Once you've completed the setup:

1. ✅ Python 3 installed and working
2. ✅ Required packages installed
3. ✅ Script files downloaded
4. ✅ Test run completed successfully

You can now process healthcare practitioner data to extract booking URLs and operating hours efficiently!

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Test with the provided examples first
4. Check Python and package versions

The script is designed to be robust and handle most common scenarios automatically.
