import joblib
import os

# If model not found, fallback simple logic
if os.path.exists("intent_model.pkl"):
    model = joblib.load("intent_model.pkl")
    vectorizer = joblib.load("vectorizer.pkl")

    def predict_intent(text):
        X = vectorizer.transform([text])
        return model.predict(X)[0]
else:
    # Temporary fallback
    def predict_intent(text):
        text = text.lower()
        if "eligible" in text:
            return "eligibility"
        elif "hospital" in text:
            return "hospital_search"
        elif "cover" in text:
            return "coverage_query"
        return "unknown"
