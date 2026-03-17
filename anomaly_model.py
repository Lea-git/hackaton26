from sklearn.ensemble import IsolationForest
import numpy as np

# Simulation historique de montants
historique_montants = np.random.normal(1500, 500, 100).reshape(-1, 1)

# Initialisation de l'Isolation Forest
model = IsolationForest(contamination=0.05, random_state=42)
model.fit(historique_montants)

def detect_outlier(amount):
    """Prédit si un montant est aberrant par rapport à l'historique."""
    prediction = model.predict([[amount]])
    # IsolationForest renvoie -1 pour une anomalie, 1 pour une donnée normale
    return prediction[0] == -1