# 🗳️ Secure E-Voting System

This project implements a **Secure E-Voting System** using Python, focusing on voter location anonymization, secure ballot handling and accurate vote tallying.

## 📋 Features
- **Location Anonymization**: Ensures voter privacy via distributed computation.
- **Secure Ballots**: Secret sharing for anonymized and confidential voting.
- **Concurrency**: Supports multiple voters and collectors using threading.

## 🔧 Tech Stack
- **Language**: Python 3
- **Development Environment**: Visual Studio Code
- **Modules**: `socket`, `json`, `threading`

## 🚀 How to Run
1. **Setup Election**
   Run `EA.py` to configure candidates and voters:
   python3 EA.py
2. **Start Collectors**
   Start collector.py on two separate terminals
3. **Cast Votes**
   Run voter.py for each voter to securely cast votes
   python3 voter.py

📊 Outputs
**EA.py:** Election details with candidates and total voters.
**Collectors:**
Partial and aggregated location shares.
Secret ballots and incremental aggregation.
Final tally results.
**Voters:** Computed unique location shares and secure ballot submissions.
