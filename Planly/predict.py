import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from torch import nn
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import WordNetLemmatizer

# Re-define the custom model class
class CustomDistilBertForSequenceClassification(DistilBertForSequenceClassification):
    def __init__(self, config):
        super().__init__(config)
        # Initialize the custom layers that were not part of the pre-trained model
        self.fc1 = nn.Linear(config.hidden_size, 128)
        self.fc2 = nn.Linear(128, config.num_labels)
        self.dropout = nn.Dropout(0.3)
        self.loss_fn = nn.CrossEntropyLoss()

    def forward(self, input_ids=None, attention_mask=None, labels=None):
        # Get the output from the DistilBERT model
        outputs = self.distilbert(input_ids=input_ids, attention_mask=attention_mask)
        hidden_state = outputs[0][:, 0, :]  # Get the hidden state from the first token (CLS token)
        
        # Pass through custom layers
        hidden_state = self.fc1(hidden_state)
        hidden_state = torch.relu(hidden_state)
        hidden_state = self.dropout(hidden_state)
        logits = self.fc2(hidden_state)

        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)
            return (loss, logits)
        return logits

# Load the pre-trained DistilBERT model
base_model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=3)

# Load the custom model, using the base model's config and weights
model = CustomDistilBertForSequenceClassification.from_pretrained('trainer/email_task_classifier', config=base_model.config)

# Load the tokenizer
tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

# Function to preprocess the text (same as in process.py)
def preprocess_text(text):
    text = text.lower()  # Convert to lowercase
    tokens = word_tokenize(text)  # Tokenize text
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    return ' '.join(tokens)

# Function to predict the label of new text
def predict(text):
    # Preprocess the input text
    processed_text = preprocess_text(text)
    
    # Tokenize and encode the text for the model
    inputs = tokenizer(processed_text, truncation=True, padding=True, max_length=128, return_tensors='pt')

    # Ensure the model is in evaluation mode
    model.eval()

    # Predict the label
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs  # Now the output is a tensor directly
        prediction = torch.argmax(logits, dim=1).item()
        
    return prediction

# Function to predict each sentence in the input text
# Function to predict each sentence in the input text
def predict_sentences(text):
    sentences = sent_tokenize(text)  # Split the text into sentences
    results = []

    for sentence in sentences:
        label = predict(sentence)  # Predict the label for each sentence
        if label == 0:  # Check if the label is Action Task (0) or Important Note (1)
            results.append(sentence)  # Add the sentence to results if it matches the labels

    # Join the selected sentences into one paragraph
    return ' '.join(results)

def predict_sentences_action_notes(text):
    sentences = sent_tokenize(text)  # Split the text into sentences
    results = []

    for sentence in sentences:
        label = predict(sentence)  # Predict the label for each sentence
        if label == 0 or label == 1:  # Check if the label is Action Task (0) or Important Note (1)
            results.append(sentence)  # Add the sentence to results if it matches the labels

    # Join the selected sentences into one paragraph
    return ' '.join(results)

# Example: Feed a paragraph for prediction
text = """
While Stephen King is a bestselling horror author, his book On Writing is equal parts memoir and general writing advice for those seeking to hone their craft.  While aimed at writers of fiction, this chapter offers some helpful tips (as well as King's own pet peeves) that could be applied to a variety of writing situations.
In a 250-500 word response, what aspects of King's toolbox (or his advice) do you find the most useful for writers in WRIT 2?  What do find not so useful?  As a writer, what is in your "toolbox"?"""
# Get predictions for action tasks and important notes
#output_paragraph = predict_sentences_action_notes(text)

# Print the output paragraph
#print("Output Paragraph:")
#print(output_paragraph)

