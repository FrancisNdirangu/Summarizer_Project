# app/summarizer.py

from transformers import BartTokenizer, BartForConditionalGeneration

class BARTSummarizer:
    def _init_(self, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        self.tokenizer = BartTokenizer.from_pretrained(model_name)
        self.model = BartForConditionalGeneration.from_pretrained(model_name)

    def summarize(
        self,
        text: str,
        max_length: int = 300,    
        min_length: int = 100,       
        do_sample: bool = False,
        num_beams: int = 4,          
        length_penalty: float = 2.0, 
        early_stopping: bool = True
    ) -> str:
        inputs = self.tokenizer.encode(text, return_tensors="pt", max_length=1024, truncation=True)
        summary_ids = self.model.generate(
    inputs,
    max_length=200,
    min_length=80,
    do_sample=False,
    num_beams=1, 
    early_stopping=True
)
        return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)





