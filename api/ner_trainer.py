"""
ner_trainer.py - spaCy NER Model Trainer for OCR documents
Train: python -m api.ner_trainer
Output: models/ocr_ner_model
"""

import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import json, os, random

# ── Training Data ─────────────────────────────────────────────────────────────
TRAIN_DATA = [
    # INVOICE samples
    ("Invoice No: INV/2025/0118", {"entities": [(12, 25, "INVOICE_NO")]}),
    ("Invoice Number: INV-2024-001", {"entities": [(16, 28, "INVOICE_NO")]}),
    ("Invoice Date: 05 Feb 2025", {"entities": [(14, 25, "DATE")]}),
    ("Date: 15-01-2025", {"entities": [(6, 16, "DATE")]}),
    ("Bill To: Priya Textiles Ltd.", {"entities": [(9, 28, "VENDOR")]}),
    ("Grand Total: Rs. 88,983.50", {"entities": [(17, 26, "TOTAL_AMOUNT")]}),
    ("Total Amount: Rs. 1,50,000.00", {"entities": [(18, 29, "TOTAL_AMOUNT")]}),
    ("IGST (12%): Rs. 9,534.00", {"entities": [(16, 24, "GST_AMOUNT")]}),
    ("CGST: Rs. 4,767.00", {"entities": [(10, 18, "GST_AMOUNT")]}),
    ("Cotton Fabric - White (50m Roll)", {"entities": [(0, 32, "ITEM_NAME")]}),
    ("Polyester Blend Thread - Black", {"entities": [(0, 30, "ITEM_NAME")]}),
    ("HSN: 520811", {"entities": [(5, 11, "HSN_CODE")]}),
    ("520811", {"entities": [(0, 6, "HSN_CODE")]}),
    ("Qty: 10", {"entities": [(5, 7, "QUANTITY")]}),
    ("Rate (Rs.): 3,500.00", {"entities": [(12, 20, "UNIT_PRICE")]}),
    ("Amount (Rs.): 35,000.00", {"entities": [(14, 23, "AMOUNT")]}),

    # PURCHASE ORDER samples
    ("PO Number: PO-2025-0088", {"entities": [(11, 23, "PO_NUMBER")]}),
    ("PO-2025-441", {"entities": [(0, 11, "PO_NUMBER")]}),
    ("Delivery Date: 05 Mar 2025", {"entities": [(15, 26, "DELIVERY_DATE")]}),
    ("Vendor: Nova Systems Pvt. Ltd.", {"entities": [(8, 30, "VENDOR")]}),
    ("Payment Terms: 30 Days Net", {"entities": [(15, 26, "PAYMENT_TERMS")]}),

    # RESUME samples
    ("Email: karthik.rajan@gmail.com", {"entities": [(7, 30, "EMAIL")]}),
    ("Phone: +91 98765 43210", {"entities": [(7, 22, "PHONE")]}),
    ("CGPA: 8.4/10", {"entities": [(6, 12, "SCORE")]}),
    ("Senior Software Engineer", {"entities": [(0, 24, "JOB_TITLE")]}),
    ("TechSoft Solutions Pvt. Ltd., Chennai", {"entities": [(0, 29, "ORGANIZATION")]}),
    ("Jun 2022 – Present", {"entities": [(0, 18, "DURATION")]}),
    ("B.E. Computer Science Engineering", {"entities": [(0, 33, "DEGREE")]}),
    ("Anna University, Chennai", {"entities": [(0, 15, "INSTITUTION")]}),

    # NAME samples
    ("Karthik Rajan", {"entities": [(0, 13, "PERSON")]}),
    ("Mohamed Arsath", {"entities": [(0, 14, "PERSON")]}),
    ("Priya Sharma", {"entities": [(0, 12, "PERSON")]}),
    ("Rahul Verma", {"entities": [(0, 11, "PERSON")]}),
    ("Anitha Krishnan", {"entities": [(0, 15, "PERSON")]}),

    # INSTITUTION fix — must be actual institutions
    ("Anna University, Chennai", {"entities": [(0, 15, "INSTITUTION")]}),
    ("IIT Madras", {"entities": [(0, 10, "INSTITUTION")]}),
    ("VIT University", {"entities": [(0, 14, "INSTITUTION")]}),
    ("Innovate Labs, Bangalore", {"entities": [(0, 13, "ORGANIZATION")]}),

    # ID CARD samples
    ("Employee ID: NS-EMP-2024-0042", {"entities": [(13, 29, "EMPLOYEE_ID")]}),
    ("Designation: Senior Software Engineer", {"entities": [(13, 37, "DESIGNATION")]}),
    ("Department: Engineering & Product", {"entities": [(12, 33, "DEPARTMENT")]}),
    ("Valid Until: 31 December 2026", {"entities": [(13, 29, "VALIDITY")]}),
    ("Blood Group: O+", {"entities": [(13, 15, "BLOOD_GROUP")]}),
    ("Date of Joining: 15 June 2022", {"entities": [(17, 29, "DATE")]}),
]

def train_ner_model(output_dir="models/ocr_ner_model", n_iter=30):
    """Train spaCy NER model on OCR document entities."""

    # Create blank English model
    nlp = spacy.blank("en")

    # Add NER pipeline
    ner = nlp.add_pipe("ner")

    # Add all entity labels
    labels = set()
    for _, ann in TRAIN_DATA:
        for start, end, label in ann["entities"]:
            labels.add(label)
            ner.add_label(label)

    print(f"Training with {len(labels)} entity types: {sorted(labels)}")

    # Training
    optimizer = nlp.begin_training()

    for iteration in range(n_iter):
        random.shuffle(TRAIN_DATA)
        losses = {}
        for text, annotations in TRAIN_DATA:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            nlp.update([example], drop=0.3, losses=losses)

        if (iteration + 1) % 10 == 0:
            print(f"Iteration {iteration + 1}/{n_iter} - Loss: {losses.get('ner', 0):.3f}")

    # Save model
    os.makedirs(output_dir, exist_ok=True)
    nlp.to_disk(output_dir)
    print(f"\nModel saved to: {output_dir}")

    # Quick test
    print("\n--- Test Results ---")
    test_texts = [
        "Invoice No: INV/2025/0118 Date: 05 Feb 2025",
        "Grand Total: Rs. 88,983.50 IGST: Rs. 9,534.00",
        "PO Number: PO-2025-0088 Vendor: Nova Systems Pvt. Ltd.",
        "Employee ID: NS-EMP-2024-0042 Valid Until: 31 December 2026",
    ]
    for text in test_texts:
        doc = nlp(text)
        if doc.ents:
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            print(f"  {entities}")

    return nlp

if __name__ == "__main__":
    train_ner_model()