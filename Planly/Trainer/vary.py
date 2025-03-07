import json
from parrot import Parrot
import torch
import warnings

warnings.filterwarnings("ignore")

def random_state(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
random_state(1234)

# Initialize the Parrot paraphraser
parrot = Parrot(model_tag="prithivida/parrot_paraphraser_on_T5", use_gpu=False)

# Load input data from JSON file
with open("test.json", "r") as file:
    data = json.load(file)

output_data = []

# Process each sentence in the dataset
for item in data:
    original_sentence = item["sentence"]
    label = item["label"]
    
    # Generate paraphrases
    print(original_sentence)
    para_phrases = parrot.augment(input_phrase=original_sentence)
    
    # Store original sentence
    print(para_phrases)
    output_data.append({"sentence": original_sentence, "label": label})
    
    # Store paraphrases with the same label
    if para_phrases:
        for para in para_phrases:
            output_data.append({"sentence": para[0], "label": label})

# Write output to a JSON file
with open("output.json", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print("Paraphrasing complete. Results saved to output.json.")
