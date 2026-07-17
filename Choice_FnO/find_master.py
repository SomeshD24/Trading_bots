import pypdf
import re
try:
    reader = pypdf.PdfReader('choice api.pdf')
    text = ''.join(page.extract_text() for page in reader.pages)
    matches = re.findall(r'https?://[^\s\"\']*master[^\s\"\']*', text, re.IGNORECASE)
    print("Master URLs:", set(matches))
except Exception as e:
    print(e)
