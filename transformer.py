from transformers import BartTokenizer, BartForConditionalGeneration

# Download and cache the model and tokenizer
model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")

# Save to a directory
model.save_pretrained("./bart-large-cnn")
tokenizer.save_pretrained("./bart-large-cnn")
