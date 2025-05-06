import csv
import ollama
import os

import re
import csv
import os
import ollama

def standardize_name(name):
    # Remove parentheses and their contents, numbers, dots, and extra spaces
    name = re.sub(r'\(.*?\)', '', name)  # remove parentheses and contents
    name = re.sub(r'^[\d\.\s]+', '', name)  # remove leading numbers/dots
    return name.strip().lower()

def get_new_animals():
    existing_animals = set()
    if os.path.exists('animal_names.csv'):
        with open('animal_names.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            existing_animals = {standardize_name(row[0]) for row in reader}

    prompt = f"""Given this list of animals that are already used: {sorted(existing_animals)}
Please provide exactly 5 new, unique animal names that are NOT in this list.
The animals should be interesting and educational for children.
Do NOT include animals closely related to or variations of animals already listed.
Return ONLY the 5 animal names, one per line, no numbers, no prefixes, no parentheses."""

    response = ollama.generate(model='mistral', prompt=prompt)
    raw_animals = response['response'].strip().split('\n')

    # Preserve your original detailed cleaning functionality here:
    new_animals = [animal.strip().lower() for animal in raw_animals if animal.strip()]
    new_animals = [animal.split('. ')[-1] if '. ' in animal else animal for animal in new_animals]  # Remove "1. " type prefixes
    new_animals = [animal.split('.')[-1] if '.' in animal else animal for animal in new_animals]  # Remove any remaining dots
    new_animals = [animal.strip() for animal in new_animals]

    # Now standardize and check against existing animals
    final_animals = []
    for animal in new_animals:
        clean_animal = standardize_name(animal)
        if clean_animal and clean_animal not in existing_animals and clean_animal not in final_animals:
            final_animals.append(animal)  # Keep original cleaned animal name (with possible descriptions)
        if len(final_animals) == 5:
            break

    return final_animals

def create_animal_scripts(animals):
    # Ensure scripts directory exists
    if not os.path.exists('scripts'):
        os.makedirs('scripts')
    
    # Create script for each animal
    created_files = []
    for animal in animals:
        # Clean filename - remove text in parentheses
        clean_filename = animal.split('(')[0].strip()
        
        # Just the clean animal name + .txt for the filename
        filename = f"{clean_filename}.txt"
        filepath = os.path.join('scripts', filename)
        
        # Keep full description in the content
        content = f"Make a video for children called facts about the {animal.title()}."
        
        with open(filepath, 'w') as f:
            f.write(content)
        created_files.append(filename)
        print(f"Created script: {filename}")
    
    return created_files

def main():
    # Get new animals
    print("Requesting new animals from Ollama...")
    new_animals = get_new_animals()
    
    # Create scripts
    print("\nCreating scripts for new animals...")
    created_files = create_animal_scripts(new_animals)
    
    print("\nCreated scripts for these animals:")
    for animal in new_animals:
        print(f"- {animal.title()}")

if __name__ == "__main__":
    main()