import json

# Load the dataset
with open("augmented_email_drive_Data.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Update labels
for entry in data:
    if entry["label"] == 2:
        entry["label"] = 1

# Save the modified dataset
with open("updated_augment_email_drive_Data.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)

print("Updated dataset saved as 'updated_augment_email_drive_Data.json'")
