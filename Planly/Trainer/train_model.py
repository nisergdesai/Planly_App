import torch
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from torch import nn
from transformers import DistilBertForSequenceClassification, Trainer, TrainingArguments, EarlyStoppingCallback, get_cosine_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
#from textaugment import EDA  # For data augmentation

# Re-define the EmailDataset class
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

# Compute evaluation metrics
def compute_metrics(p):
    logits, labels = p
    logits = torch.tensor(logits)
    pred = torch.argmax(logits, axis=1)
    
    precision, recall, f1, _ = precision_recall_fscore_support(labels, pred, average='weighted')
    
    plot_confusion_matrix(labels, pred, filename="confusion_matrix_train.png")
    
    return {
        'accuracy': accuracy_score(labels, pred),
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# Confusion matrix visualization
def plot_confusion_matrix(labels, pred, filename="confusion_matrix.png", show=False):
    cm = confusion_matrix(labels, pred)
    
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Task', 'Important Note', 'Non-Task'], 
                yticklabels=['Task', 'Important Note', 'Non-Task'])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    
    if show:
        plt.show()
    
    plt.savefig(filename)
    plt.close()

# Load datasets
train_dataset = torch.load("train_dataset.pt")
val_dataset = torch.load("val_dataset.pt")
test_dataset = torch.load("test_dataset.pt")

# Extract labels properly
train_labels = np.array([train_dataset[i]["labels"].item() for i in range(len(train_dataset))])

# Compute class weights
class_labels = np.unique(train_labels)
class_weights = compute_class_weight(class_weight='balanced', classes=class_labels, y=train_labels)
class_weights_tensor = torch.tensor(list(class_weights)).float().to("cuda" if torch.cuda.is_available() else "cpu")

print("Class weights:", class_weights_tensor)

# Define Focal Loss function
class FocalLoss(nn.Module):
    def __init__(self, alpha=0.5, gamma=2, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean() if self.reduction == 'mean' else focal_loss.sum()

# Custom model with additional dropout
class CustomDistilBertForSequenceClassification(DistilBertForSequenceClassification):
    def __init__(self, config, class_weights_tensor):
        super().__init__(config)
        self.class_weights_tensor = class_weights_tensor
        self.loss_fn = FocalLoss(alpha=0.5, gamma=2)  # Replacing CE loss with Focal Loss
        self.dropout = nn.Dropout(0.5)  # Increased dropout
        self.fc1 = nn.Linear(config.hidden_size, 128)
        self.fc2 = nn.Linear(128, config.num_labels)

    def forward(self, input_ids=None, attention_mask=None, labels=None):
        outputs = self.distilbert(input_ids=input_ids, attention_mask=attention_mask)
        hidden_state = outputs.last_hidden_state[:, 0, :]
        hidden_state = self.fc1(hidden_state)
        hidden_state = torch.relu(hidden_state)
        hidden_state = self.dropout(hidden_state)
        logits = self.fc2(hidden_state)

        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)
            return (loss, logits)
        return logits

# Use the custom model
custom_model = CustomDistilBertForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=3, class_weights_tensor=class_weights_tensor
)

# Define training arguments
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=10,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_dir='./logs',
    logging_steps=10,
    learning_rate=3e-5,  # Increased learning rate slightly
    weight_decay=0.1,  # Increased weight decay to prevent overfitting
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",  # Cosine decay learning rate
    save_total_limit=2,
    load_best_model_at_end=True
)

# Add early stopping
trainer = Trainer(
    model=custom_model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],  # Stops training if eval loss increases
)

# Train the model
trainer.train()

# Evaluate on the test dataset
test_results = trainer.evaluate(test_dataset)
print("Test results:", test_results)
with open("test_metrics.json", "w") as f:
    json.dump(test_results, f)

# Generate predictions for the test dataset
predictions = trainer.predict(test_dataset)
logits = predictions.predictions
true_labels = predictions.label_ids
pred_labels = np.argmax(logits, axis=1)

# Save and show the confusion matrix
plot_confusion_matrix(true_labels, pred_labels, filename="confusion_matrix_test.png", show=True)

# Save the trained model
custom_model.save_pretrained("email_task_classifier")
print("Model saved successfully!")
