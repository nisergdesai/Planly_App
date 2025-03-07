import json
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Ensure necessary NLTK resources are available
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Load data from JSON file
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# Preprocess text (without removing non-alphanumeric characters or stopwords)
def preprocess_text(text):
    text = text.lower()  # Convert to lowercase
    tokens = word_tokenize(text)  # Tokenize text
    lemmatizer = WordNetLemmatizer()
    # Lemmatize tokens, but don't remove stopwords or non-alphanumeric characters
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    return ' '.join(tokens)

# Process the data
def process_data(data):
    processed_data = []
    
    for item in data:
        sentence = item.get('sentence', '')
        label = item.get('label', '')
        processed_text = preprocess_text(sentence)
        processed_data.append({
            'sentence': processed_text,
            'label': label
        })
    
    # Remove duplicates based on the 'sentence' field
    seen = set()
    unique_data = []
    for item in processed_data:
        if item['sentence'] not in seen:
            unique_data.append(item)
            seen.add(item['sentence'])
    
    return unique_data

# Save processed data to JSON
def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    input_file = "email_drive_Data.json"  # Replace with actual JSON file path
    output_file = "email_drive_Data.json"
    
    data = load_data(input_file)
    processed_data = process_data(data)
    save_to_json(processed_data, output_file)
    
    print(f"Processed data saved to {output_file}")