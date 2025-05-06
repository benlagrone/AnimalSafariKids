import os
import csv

def create_animal_csv():
    # Directory containing the scripts
    scripts_dir = "scripts"
    
    # Get all .txt files in the scripts directory
    animal_names = []
    for filename in os.listdir(scripts_dir):
        if filename.endswith('.txt'):
            # Remove .txt extension and convert hyphens/underscores to spaces
            animal_name = filename[:-4].replace('-', ' ').replace('_', ' ')
            animal_names.append([animal_name])
    
    # Sort the animal names alphabetically
    animal_names.sort()
    
    # Write to CSV file
    with open('animal_names.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Animal Name'])  # Header
        writer.writerows(animal_names)
    
    print(f"Created CSV with {len(animal_names)} animal names")
    return animal_names  # Return the list in case it's needed

# Only run if script is run directly (not imported)
if __name__ == "__main__":
    create_animal_csv()