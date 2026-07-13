# StegPDF-21: A Benchmark Dataset for PDF Steganography Detection

<p align="center">
  <img src="https://img.shields.io/badge/Dataset-Steganography-blue" />
  <img src="https://img.shields.io/badge/PDF-Digital%20Forensics-red" />
  <img src="https://img.shields.io/badge/Machine%20Learning-Benchmark-success" />
  <img src="https://img.shields.io/badge/License-Apache%202.0-green" />
</p>

---

## Overview

**StegPDF-21** is a benchmark dataset developed for machine learning-based **PDF steganography detection**. The dataset consists of clean and steganographic PDF documents generated using multiple information-hiding techniques and is intended to support research in:

- PDF Steganalysis
- Digital Forensics
- Cybersecurity
- Document Security
- Explainable Artificial Intelligence (XAI)
- Machine Learning Benchmarking

Unlike image and audio steganography, publicly available benchmark datasets for **PDF steganography** are extremely limited. StegPDF-21 addresses this gap by providing engineered feature representations extracted from PDF document structures.

---

# Dataset Statistics

| Property | Value |
|-----------|------:|
| Dataset Name | StegPDF-21 |
| Total Samples | 19,372 |
| Clean PDFs | 9,621 |
| Stego PDFs | 9,751 |
| Engineered Features | 25 |
| Classes | 2 |
| Labels | Clean (0), Stego (1) |

---

# Repository Structure

```
StegPDF-21/
│
├── extraction.py
├── stego_generation.py
├── README.md
├── LICENSE
```

---

# Steganographic Techniques

Stego PDF documents were generated using multiple embedding strategies.

- Metadata Hiding
- Invisible (White) Text Insertion
- Text Spacing Manipulation
- Zero-Width Unicode Characters
- PDF Comment Injection
- Unused PDF Objects
- Stream Padding
- Embedded Image Steganography

---

# Engineered Features

The dataset contains **25 engineered features** extracted from each PDF document.

## Structural Features

- File Size
- Page Count
- Object Count
- Average Objects per Page
- Orphan Object Count
- Orphan Object Depth
- Unused Object Ratio
- Cross Reference Gap Score
- Structural Complexity Score
- Page Object Distribution Entropy

---

## Metadata Features

- Metadata Length
- Metadata Key Count
- Custom Metadata Key Count
- Metadata Value Entropy

---

## Text Features

- Zero Width Unicode Density
- Invisible Text Ratio
- Character Spacing Deviation
- Whitespace Run Variance
- Text-to-Nontext Ratio

---

## Comment Features

- Comment Object Count
- Comment Length Ratio

---

## Stream Features

- Padding Byte Ratio

---

## Image Features

- Image Count
- Image Entropy Delta
- Image Size Anomaly

---

# Feature Extraction

The repository provides an automated feature extraction pipeline.

```
PDF Document
      │
      ▼
PDF Parsing
      │
      ▼
Metadata Analysis
      │
      ▼
Structure Analysis
      │
      ▼
Text Analysis
      │
      ▼
Image Analysis
      │
      ▼
Feature Engineering
      │
      ▼
CSV Dataset
```

---

# Machine Learning Benchmark

The dataset was evaluated using representative machine learning classifiers.

| Classifier | Accuracy | Precision | Recall | F1-score | ROC-AUC |
|------------|---------:|----------:|--------:|---------:|--------:|
| Logistic Regression | 0.6487 | 0.6459 | 0.6688 | 0.6572 | 0.7111 |
| Gaussian Naïve Bayes | 0.6024 | 0.6838 | 0.3910 | 0.4975 | 0.6901 |
| Random Forest | 0.7978 | 0.8137 | 0.7761 | 0.7945 | 0.8799 |
| XGBoost | **0.8109** | 0.8290 | **0.7867** | **0.8073** | 0.8900 |
| LightGBM | 0.8083 | **0.8302** | 0.7785 | 0.8035 | **0.8922** |
| Support Vector Machine | *(Coming Soon)* | | | | |

---

# Evaluation Protocol

The benchmark experiments followed a standardized evaluation protocol.

- Stratified 70:30 Train-Test Split
- Stratified 5-Fold Cross Validation
- Optuna Hyperparameter Optimization
- Median Pruner
- Independent Test Evaluation

Performance metrics include

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

---

# Requirements

Python ≥ 3.10

Required packages

```
numpy
pandas
PyPDF2
pikepdf
scikit-learn
xgboost
lightgbm
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

# Usage

## Generate Stego PDFs

```bash
python stego_generation.py
```

---

## Extract Features

```bash
python extraction.py
```

The extracted features are automatically stored as

```
output/features_25_FINAL.csv
```

---

# Applications

StegPDF-21 can be used for

- PDF Steganography Detection
- Machine Learning Research
- Digital Forensics
- Cybersecurity Research
- Explainable AI
- Benchmark Dataset Evaluation
- Feature Selection
- Classification Research

---

# Citation

If you use this dataset in your research, please cite:

```
Amaan Hamid et al.

StegPDF-21: A Benchmark Dataset for PDF Steganography Detection.

Data in Brief.

(Under Review)
```

---

# License

This project is licensed under the **Apache License 2.0**.

See the LICENSE file for details.

---

# Author

**Mohd. Amaan Hamid**

M.Sc. Cyber Security Researcher

Research Interests

- PDF Steganography
- Digital Forensics
- Machine Learning
- Explainable AI
- Cybersecurity

GitHub

https://github.com/amn2905

---

# Acknowledgements

This dataset was developed to facilitate reproducible research in PDF steganography detection and digital document forensics by providing a standardized benchmark for evaluating machine learning models.
