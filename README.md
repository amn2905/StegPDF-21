# StegPDF-21: A Benchmark Dataset for PDF Steganography Detection

## Overview

StegPDF-21 is a benchmark dataset designed for machine learning-based PDF steganography detection. The dataset contains both clean and steganographically modified PDF documents generated using multiple hiding techniques. It is intended to support research in PDF steganalysis, digital forensics, document security, and explainable artificial intelligence.

The dataset provides engineered structural, metadata, textual, and image-based features extracted from PDF documents for reproducible machine learning experiments.

---

## Dataset Statistics

| Property | Value |
|----------|------:|
| Total Samples | 19,372 |
| Clean PDFs | 9,621 |
| Stego PDFs | 9,751 |
| Total Features | 21 |
| Classes | Binary (Clean / Stego) |

---

## Repository Structure

```
StegPDF-21/
│
├── extraction.py              # Feature extraction script
├── stego_generation.py        # PDF steganography generation
├── LICENSE
└── README.md
```

---

## Steganographic Techniques

The dataset includes steganographic PDFs generated using the following techniques:

1. Metadata Hiding
2. Invisible (White) Text Insertion
3. Text Spacing Manipulation
4. Zero-Width Unicode Characters
5. PDF Comment Injection
6. Unused PDF Object Embedding
7. Stream Padding
8. Embedded Image Steganography

---

## Extracted Features

The dataset contains 21 engineered features representing multiple PDF characteristics.

### Structural Features

- File Size
- Page Count
- Object Count
- Average Objects per Page
- Orphan Object Depth
- Cross-Reference Gap Score
- Structural Complexity Score
- Page Object Distribution Entropy

### Metadata Features

- Metadata Length
- Metadata Key Count
- Metadata Value Entropy

### Text-Based Features

- Zero Width Unicode Density
- Invisible Text Ratio
- Character Spacing Deviation
- Whitespace Run Variance
- Comment Length Ratio
- Text-to-Nontext Ratio

### Image-Based Features

- Image Count
- Image Entropy Delta
- Image Size Anomaly

### Stream Feature

- Padding Byte Ratio

---

## Machine Learning Benchmark

The dataset was evaluated using several supervised machine learning classifiers.

| Model | Accuracy |
|--------|---------:|
| Logistic Regression | 64.87% |
| Gaussian Naïve Bayes | 60.24% |
| Random Forest | 79.78% |
| XGBoost | **81.09%** |
| LightGBM | 80.83% |

Evaluation Protocol:

- Stratified 70:30 Train-Test Split
- Stratified 5-Fold Cross Validation
- Optuna Hyperparameter Optimization
- Median Pruner

Evaluation Metrics:

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

---

## Requirements

Python 3.10+

Required libraries

```
numpy
pandas
PyMuPDF
PyPDF2
scikit-learn
lightgbm
xgboost
optuna
joblib
matplotlib
seaborn
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Generate Stego PDFs

```bash
python stego_generation.py
```

### Extract Features

```bash
python extraction.py
```

---

## Applications

- PDF Steganalysis
- Digital Forensics
- Machine Learning
- Explainable AI
- Cybersecurity
- Document Security
- Academic Benchmarking

---

## Citation

If you use this dataset in your research, please cite:

```
Author(s).

StegPDF-21: A Benchmark Dataset for PDF Steganography Detection.

Data in Brief.

(Under Review)
```

---

## License

This project is distributed under the Apache 2.0 License.

See the LICENSE file for details.

---

## Contact

**Mohd. Amaan Hamid**

Department of Cyber Security

Email: hamidamaan3@gmail.com

GitHub: https://github.com/amn2905
