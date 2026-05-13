import numpy as np
from scipy.stats import poisson

def advanced_match_simulator(home_xg, away_xg, rho=-0.05):
    """
    ULTRA PRO MATCH SIMULATOR
    home_xg: Oczekiwane gole gospodarzy
    away_xg: Oczekiwane gole gości
    rho: Parametr korelacji Dixona-Colesa (zazwyczaj -0.05 w piłce nożnej)
    """
    max_goals = 10 # Maksymalna liczba goli, jaką rozpatrujemy dla jednej drużyny
    
    # 1. Generujemy idealne prawdopodobieństwa matematyczne dla każdego wyniku goli (0 do 9)
    home_probs = poisson.pmf(np.arange(max_goals), home_xg)
    away_probs = poisson.pmf(np.arange(max_goals), away_xg)
    
    # 2. Tworzymy Macierz Prawdopodobieństw (Wszystkie możliwe wyniki np. 0:0, 2:1, 3:3)
    prob_matrix = np.outer(home_probs, away_probs)
    
    # 3. KOREKTA DIXONA-COLESA (Święty Graal analityki piłkarskiej)
    # Ręcznie korygujemy prawdopodobieństwa wyników niskobramkowych, gdzie psychologia
    # piłkarska łamie zasady czystej statystyki (np. murowanie bramki przy remisie)
    prob_matrix[0, 0] *= max(0, 1 - home_xg * away_xg * rho)
    prob_matrix[0, 1] *= max(0, 1 + home_xg * rho)
    prob_matrix[1, 0] *= max(0, 1 + away_xg * rho)
    prob_matrix[1, 1] *= max(0, 1 - rho)
    
    # Normalizacja macierzy, by suma szans wynosiła idealne 1.0 (100%)
    prob_matrix /= np.sum(prob_matrix)
    
    # 4. WYCIĄGAMY RYNKI BUKMACHERSKIE Z MACIERZY
    # 1X2
    home_win = np.tril(prob_matrix, -1).sum()  # Suma wszystkiego pod przekątną (1:0, 2:1 itd)
    draw = np.trace(prob_matrix)               # Suma przekątnej (0:0, 1:1, 2:2)
    away_win = np.triu(prob_matrix, 1).sum()   # Suma wszystkiego nad przekątną (0:1, 1:2)
    
    # Over / Under 2.5
    under_25 = prob_matrix[0,0] + prob_matrix[1,0] + prob_matrix[0,1] + \
               prob_matrix[1,1] + prob_matrix[2,0] + prob_matrix[0,2]
    over_25 = 1.0 - under_25
    
    # BTTS (Obie strzelą)
    btts_no = prob_matrix[0, :].sum() + prob_matrix[:, 0].sum() - prob_matrix[0,0]
    btts_yes = 1.0 - btts_no
    
    # Dokładny wynik (TOP 3)
    flat_indices = np.argsort(prob_matrix.flatten())[::-1]
    top_scores = []
    for idx in flat_indices[:3]:
        h_g, a_g = np.unravel_index(idx, prob_matrix.shape)
        top_scores.append((f"{h_g}:{a_g}", prob_matrix[h_g, a_g]))

    return {
        "1X2": {
            "HOME": round(home_win * 100, 2),
            "DRAW": round(draw * 100, 2),
            "AWAY": round(away_win * 100, 2)
        },
        "GOALS": {
            "OVER_2.5": round(over_25 * 100, 2),
            "UNDER_2.5": round(under_25 * 100, 2),
            "BTTS_YES": round(btts_yes * 100, 2),
            "BTTS_NO": round(btts_no * 100, 2)
        },
        "TOP_CORRECT_SCORES": [
            { "score": score, "prob": round(prob * 100, 2)} for score, prob in top_scores
        ]
    }

# Przykład użycia:
# wynik = advanced_match_simulator(home_xg=1.85, away_xg=1.10)
# print(wynik)