import json
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from transformers import DistilBertTokenizer

# Load dataset
with open("email_drive_Data.json", "r") as f:
    dataset = json.load(f)

# Convert to Pandas DataFrame
df = pd.DataFrame(dataset)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle the dataset
df["label"] = df["label"].astype(int) - 1

print(f"Total dataset size: {len(df)}")
print(df.head())  # Check data format

# Convert labels from {1, 2, 3} to {0, 1, 2}


# Splitting dataset into train (80%), validation (10%), test (10%)
train_texts, temp_texts, train_labels, temp_labels = train_test_split(
    df["sentence"], df["label"], test_size=0.2, stratify=df["label"], random_state=42
)

val_texts, test_texts, val_labels, test_labels = train_test_split(
    temp_texts, temp_labels, test_size=0.5, stratify=temp_labels, random_state=42
)

print(f"Train size: {len(train_texts)}, Validation size: {len(val_texts)}, Test size: {len(test_texts)}")

# Load DistilBERT tokenizer
tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

# Tokenizing text
train_encodings = tokenizer(list(train_texts), truncation=True, padding=True, max_length=128)
val_encodings = tokenizer(list(val_texts), truncation=True, padding=True, max_length=128)
test_encodings = tokenizer(list(test_texts), truncation=True, padding=True, max_length=128)

# Create PyTorch Dataset class
class EmailDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item

# Convert to PyTorch datasets
train_dataset = EmailDataset(train_encodings, list(train_labels))
val_dataset = EmailDataset(val_encodings, list(val_labels))
test_dataset = EmailDataset(test_encodings, list(test_labels))

# Save datasets for later use
torch.save(train_dataset, "train_dataset.pt")
torch.save(val_dataset, "val_dataset.pt")
torch.save(test_dataset, "test_dataset.pt")

print("Datasets saved as train_dataset.pt, val_dataset.pt, and test_dataset.pt")
