import pandas as pd
from comprehensive_booking_extractor import process_practitioners_batch

# Load your CSV file
df = pd.read_csv('your_practitioners.csv')

# Convert to required format
practitioners_data = []
for _, row in df.iterrows():
    practitioners_data.append({
        'name': row['practitioner_name'],  # Adjust column name as needed
        'clinic_website': row.get(' ', '')  # Adjust column name as needed
    })

# Process
results = process_practitioners_batch(practitioners_data)

# Save enhanced results
enhanced_df = pd.DataFrame(results)
enhanced_df.to_csv('enhanced_results.csv', index=False)

print("✅ Processing complete!")
