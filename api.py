import pandas as pd

def get_team_stats(team_name):
    # Lista linków do darmowych danych (Top 5 lig Europy)
    urls = [
        "https://www.football-data.co.uk/mmz4281/2526/E0.csv",  # Anglia
        "https://www.football-data.co.uk/mmz4281/2526/D1.csv",  # Niemcy
        "https://www.football-data.co.uk/mmz4281/2526/F1.csv",  # Francja (TU JEST LENS!)
        "https://www.football-data.co.uk/mmz4281/2526/SP1.csv", # Hiszpania
        "https://www.football-data.co.uk/mmz4281/2526/I1.csv"   # Włochy
    ]
    
    all_home_goals = []
    all_away_goals = []

    print(f"🔍 Przeszukuję bazy danych dla: {team_name}...")

    for url in urls:
        try:
            df = pd.read_csv(url)
            
            # ZABEZPIECZENIE: Usuwamy puste wiersze, które psują matematykę
            df = df.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
            
            # Wymuszamy, żeby gole były liczbami, a nie tekstem
            df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
            df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
            
            # Wyciągamy gole
            h_g = df[df['HomeTeam'] == team_name]['FTHG'].tolist()
            a_g = df[df['AwayTeam'] == team_name]['FTAG'].tolist()
            
            if h_g or a_g:
                all_home_goals.extend(h_g)
                all_away_goals.extend(a_g)
        except Exception as e:
            # Lepsze łapanie błędów, żeby wiedzieć, co ewentualnie padło
            # print(f"Błąd przy {url}: {e}")
            continue 

    all_goals = all_home_goals + all_away_goals
    
    if not all_goals:
        print(f"⚠️ Nie znaleziono danych dla {team_name}!")
        return None
            
    srednia = sum(all_goals) / len(all_goals)
    print(f"✅ Średnia goli dla {team_name}: {srednia:.2f} (na podstawie {len(all_goals)} meczów)")
    
    return srednia