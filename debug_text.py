import sys
import pdfplumber

with pdfplumber.open(sys.argv[1]) as pdf:
    page = pdf.pages[0]
    clean = page.filter(lambda o: o.get("object_type") != "char" or o.get("upright", True))
    print("chars before:", len(page.chars), "after:", len(clean.chars))
    print("-----")
    print(clean.extract_text())