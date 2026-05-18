import re


class TextPreprocessor:
    def clean(self, text: str) -> str:
        text = self.remove_extra_whitespace(text)
        text = self.normalize_newlines(text)
        return text.strip()

    def remove_extra_whitespace(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text)

    def normalize_newlines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)