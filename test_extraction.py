import pymupdf4llm

pdf_path = input("Enter PDF path: ").strip()
text = pymupdf4llm.to_markdown(pdf_path)

print(text[:5000])

with open("extracted_preview.txt", "w", encoding="utf-8") as f:
    f.write(text)