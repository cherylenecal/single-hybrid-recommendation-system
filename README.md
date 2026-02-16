## 📌 Research Overview
This project is a research-based implementation designed to assist aspiring entrepreneurs in identifying suitable business sectors based on their psychological profiles. By addressing the information overload and cold-start problem, this system provides personalized recommendations using a combination of psychological constructs and advanced filtering techniques.

## 🧠 Methodology
The core of this research is a comparative analysis between two recommendation strategies:
Knowledge-Based Filtering (Single): Utilizes explicit user input and rule-based logic to map personality traits directly to business sectors.
Cascade Hybrid Filtering: A multi-stage approach that integrates Knowledge-Based filtering with Content-Based Filtering (TF-IDF) to enhance recommendation diversity.

The system calculates similarity using Euclidean Distance to ensure precise mapping between user characteristics (such as the Big Five, Self-Efficacy, and Innovativeness) and sectoral requirements.

## 🛠️ Tech Stack
Language: Python 
Machine Learning & Data: Scikit-Learn, Pandas, NumPy, NLTK 
Database: TiDB (Distributed SQL Database) for scalable data storage and real-time monitoring of user interactions.
Web Framework: Streamlit for the interactive user interface.

## 🚀 Key Features
Personality Profiling: Processes user responses to psychological instruments to create a unique trait vector.
Hybrid Recommendation Engine: Implements a refined TF-IDF vectorizer to match business sector descriptions with user needs.
Database Integration: Seamlessly retrieves and manages data from TiDB to track recommendation performance and user analytics.
Cold-Start Solution: Specifically designed to provide relevant suggestions even when no historical user-item transaction data is available.

## 📊 Evaluation & Results
The system underwent rigorous User-Centered Evaluation involving 84 respondents. The results demonstrated:
Preference Accuracy: The Knowledge-Based (Single) method excelled in direct preference matching.
Recommendation Diversity: The Cascade Hybrid model significantly improved the variety of sectors suggested, effectively mitigating the limitations of single-method filtering.
User Satisfaction: High scores in perceived ease of use and recommendation relevance across both tested models.
