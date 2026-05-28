import re

_CYRILLIC_TO_LATIN = {
    'А': 'A', 'а': 'a',
    'Б': 'B', 'б': 'b',
    'В': 'V', 'в': 'v',
    'Г': 'G', 'г': 'g',
    'Д': 'D', 'д': 'd',
    'Ђ': 'Dj', 'ђ': 'd ',
    'Е': 'E', 'е': 'e',
    'Ж': 'Z', 'ж': 'z',
    'З': 'Z', 'з': 'z',
    'И': 'I', 'и': 'i',
    'Ј': 'J', 'ј': 'j',
    'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l',
    'Љ': 'Lj', 'љ': 'lj',
    'М': 'M', 'м': 'm',
    'Н': 'N', 'н': 'n',
    'Њ': 'Nj', 'њ': 'nj',
    'О': 'O', 'о': 'o',
    'П': 'P', 'п': 'p',
    'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's',
    'Т': 'T', 'т': 't',
    'Ћ': 'C', 'ћ': 'c',
    'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f',
    'Х': 'H', 'х': 'h',
    'Ц': 'C', 'ц': 'c',
    'Ч': 'C', 'ч': 'c',
    'Џ': 'Dz', 'џ': 'dz',
    'Ш': 'S', 'ш': 's',
}


class TextPreprocessor:
    def clean(self, text: str) -> str:
        text = self.cyrillic_to_latin(text)
        text = self.remove_extra_whitespace(text)
        text = self.normalize_newlines(text)
        return text.strip()

    def cyrillic_to_latin(self, text: str) -> str:
        result = []
        for ch in text:
            result.append(_CYRILLIC_TO_LATIN.get(ch, ch))
        return ''.join(result)

    def remove_extra_whitespace(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text)

    def normalize_newlines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)