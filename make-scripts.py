import os

def create_animal_scripts(animals, directory="scripts"):
    # Ensure the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    for animal in animals:
        # Define the file path
        file_path = os.path.join(directory, f"{animal.lower().replace(' ', '_')}.txt")
        
        # Write the content to the file
        with open(file_path, "w") as file:
            file.write(f"Make a video for children called facts about the {animal}.")

# Example usage
animals = ["saola", "vaquita", "pika", "marbled polecat", "tuatara"]
create_animal_scripts(animals)