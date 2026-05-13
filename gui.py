import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os
import re
import requests
from bs4 import BeautifulSoup
import random
import streamlit_authenticator as stauth
from auth_config import config  # Importujemy Twoje ustawienia
from thefuzz import process, fuzz

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="AI Ultra Betting Center", page_icon="⚽", layout="wide")

# --- SYSTEM AUTENTYKACJI ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 1. W nowej wersji podajemy tylko lokalizację jako słowo kluczowe
authenticator.login(location='main')

# 2. Sprawdzamy status logowania korzystając z session_state
if st.session_state["authentication_status"]:
    # Pobieramy dane zalogowanego użytkownika
    name = st.session_state["name"]
    username = st.session_state["username"]
    
    # Reszta Twojego kodu aplikacji (ten, który ma się wykonać po zalogowaniu)
    
elif st.session_state["authentication_status"] is False:
    st.error('Błędny login lub hasło')
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning('Wprowadź dane logowania')
    st.stop()

# Jeśli logowanie się uda (status == True), reszta kodu się wykona:

# --- CUSTOM CSS: STYLIZACJA DASHBOARDU I MENU ---
st.markdown("""
<style>
    /* Klasa dla karty premium */
    .premium-card {
        background: linear-gradient(145deg, #1e212b, #11131a);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        transition: transform 0.2s ease;
    }
    .premium-card:hover {
        transform: translateY(-3px);
        border: 1px solid rgba(0, 255, 136, 0.2);
    }
    .league-tag {
        color: #00b8ff;
        font-size: 0.75rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .match-title {
        font-size: 1.5rem;
        font-weight: 900;
        color: white;
        margin-bottom: 12px;
    }
    .pick-box {
        background: rgba(255,255,255,0.03);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border-left: 5px solid;
    }
    .prob-text {
        font-size: 0.85rem;
        color: #9da5b1;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SILNIK DANYCH ---
@st.cache_data(ttl=3600)
def load_data():
    seasons = ["2526", "2425", "2324", "2223"]
    leagues = {
        "Premier League": "E0", "Bundesliga": "D1", "Ligue 1": "F1",
        "La Liga": "SP1", "Serie A": "I1", "Liga Portugal": "P1"
    }
    dfs = {}
    for name, code in leagues.items():
        league_frames = []
        for season in seasons:
            url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
            try:
                df = pd.read_csv(url)
                df = df.dropna(subset=['HomeTeam', 'AwayTeam'])
                df['Season'] = season
                league_frames.append(df)
            except: 
                continue
        if league_frames:
            dfs[name] = pd.concat(league_frames, ignore_index=True)
    return dfs

all_data = load_data()
if not all_data:
    st.error("Błąd pobierania danych. Sprawdź połączenie z siecią.")
    st.stop()

# --- POBIERANIE KURSÓW DLA KONKRETNEGO MECZU (Do Centrum Analizy) ---
@st.cache_data(ttl=300)
def fetch_live_odds(api_key, league_name, h_team, a_team):
    if not api_key or api_key == "TWÓJ_KLUCZ_API_TUTAJ": return None
    
    odds_api_leagues = {
        "Premier League": "soccer_epl",
        "Bundesliga": "soccer_germany_bundesliga",
        "Ligue 1": "soccer_france_ligue_one",
        "La Liga": "soccer_spain_la_liga",
        "Serie A": "soccer_italy_serie_a",
        "Liga Portugal": "soccer_portugal_primeira_liga"
    }
    
    sport_key = odds_api_leagues.get(league_name)
    if not sport_key: return None
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    # ZMIANA: Dodano "totals" do rynków!
    params = {"apiKey": api_key, "regions": "eu", "markets": "h2h,totals"}
    
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            for match in data:
                h_api, a_api = match['home_team'], match['away_team']
                # Substring match ze względu na różnice w nazwach
                if h_team[:5].lower() in h_api.lower() or h_api[:5].lower() in h_team.lower():
                    bookmakers = match.get('bookmakers', [])
                    if bookmakers:
                        markets = bookmakers[0].get('markets', [])
                        if markets:
                            outcomes = markets[0].get('outcomes', [])
                            odds = {out['name']: out['price'] for out in outcomes}
                            return {
                                '1': odds.get(h_api, 0),
                                'X': odds.get('Draw', 0),
                                '2': odds.get(a_api, 0),
                                'bookmaker': bookmakers[0].get('title', 'API')
                            }
    except Exception as e:
        return None
    return None

def get_schedule_from_api(api_key, league_name):
    odds_api_leagues = {
        "Premier League": "soccer_epl", "Bundesliga": "soccer_germany_bundesliga",
        "Ligue 1": "soccer_france_ligue_one", "La Liga": "soccer_spain_la_liga",
        "Serie A": "soccer_italy_serie_a", "Liga Portugal": "soccer_portugal_primeira_liga"
    }
    sport_key = odds_api_leagues.get(league_name)
    if not sport_key: return []
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    # ZMIANA: Dodano "totals" tutaj też, żeby skaner widział kursy na bramki!
    params = {"apiKey": api_key, "regions": "eu", "markets": "h2h,totals"}
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            dane = res.json()
            if len(dane) > 0:
                return dane
            else:
                st.info("🛠️ System API działa, ale bukmacher nie wystawił jeszcze kursów na tę ligę.")
            return dane
        else:
            st.error(f"🚨 Błąd z serwera API: {res.text}")
            return []
    except Exception as e:
        st.error(f"🚨 Błąd połączenia: {e}")
        return []

# =====================================================================
# --- NAWIGACJA GŁÓWNA (SIDEBAR) ---
# =====================================================================
# =====================================================================
# --- NAWIGACJA GŁÓWNA (SIDEBAR) ---
# =====================================================================
with st.sidebar:
    # --- NOWE: BEZPIECZNE DODAWANIE LOGO ---
    import os
    
    # Pobieramy ścieżkę do folderu, w którym jest ten skrypt
    base_dir = os.path.dirname(__file__)
    logo_path = os.path.join(base_dir, "logo.png")

    if os.path.exists(logo_path):
        col_l1, col_l2, col_l3 = st.columns([1, 4, 1])
        with col_l2:
            st.image(logo_path, use_container_width=True)
            st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Nie znaleziono pliku logo.png w folderze projektu!")

    menu_choice = st.radio(
        "Nawigacja Główna", 
        ["🎯 Centrum Analizy", "🔮 Złote Typy AI", "📈 Dziennik Zysków (ROI)"],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.1); margin: 15px 0;'>", unsafe_allow_html=True)
    
    if menu_choice == "🎯 Centrum Analizy":
        st.markdown("<p style='color: #00b8ff; font-weight: bold; font-size: 0.85rem; text-transform: uppercase;'>🌍 Baza Rozgrywek</p>", unsafe_allow_html=True)
        league_choice = st.selectbox("Wybierz Ligę", list(all_data.keys()), label_visibility="collapsed")
        df = all_data[league_choice]
        
        current_season_df = df[df['Season'] == '2526']
        if not current_season_df.empty:
            teams = sorted(current_season_df['HomeTeam'].unique())
        else:
            teams = sorted(df['HomeTeam'].unique())
            
        st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.1); margin: 15px 0;'>", unsafe_allow_html=True)

    # --- KLUCZ API WPISANY NA SZTYWNO (Ukryty w interfejsie) ---
    user_api_key = "b8aca90a6e292cd21be009ba58b2e73e"

    # NAPRAWIONA RAMKA SYSTEM ONLINE (Usunięty zduplikowany div)
    st.markdown("""
<div style="background: rgba(255,255,255,0.02); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05); position: relative;">
<div style="display: flex; align-items: center; margin-bottom: 10px;">
<div style="width: 10px; height: 10px; border-radius: 50%; background: #00ff88; margin-right: 10px; box-shadow: 0 0 8px #00ff88; animation: pulse 2s infinite;"></div>
<span style="color: white; font-size: 0.85rem; font-weight: bold;">System Online</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9da5b1; margin-bottom: 5px;">
<span>Wersja Silnika:</span>
<span style="color: #ffcc00;">v5.0 PRO (xG + Time Decay)</span>
</div>
<style>
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); } }
</style>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# --- FUNKCJE POMOCNICZE (SUPER-MODEL v5.0) ---
# =====================================================================

def get_auto_motivation(team_name):
    if 'df' not in globals() or 'league_choice' not in globals(): return "Normalna", 1.0, "Brak danych", "#ffcc00"
    curr_df = df[df['Season'] == '2526'] if 'Season' in df.columns else df
    stats = {}
    for t in curr_df['HomeTeam'].unique():
        df_t = curr_df[(curr_df['HomeTeam']==t) | (curr_df['AwayTeam']==t)]
        pkt = 0
        for _, row in df_t.iterrows():
            if (row['HomeTeam'] == t and row['FTR'] == 'H') or (row['AwayTeam'] == t and row['FTR'] == 'A'): pkt += 3
            elif row['FTR'] == 'D': pkt += 1
        stats[t] = {'M': len(df_t), 'Pkt': pkt}
        
    if team_name not in stats or stats[team_name]['M'] == 0: return "Normalna", 1.0, "Początek sezonu", "#ffcc00"
        
    sorted_teams = sorted(stats.items(), key=lambda x: x[1]['Pkt'], reverse=True)
    total_teams = len(sorted_teams)
    rank = next((idx + 1 for idx, (t, _) in enumerate(sorted_teams) if t == team_name), 1)
    matches_played, team_pts = stats[team_name]['M'], stats[team_name]['Pkt']
    
    league_rules = {
        "Premier League": {"max_m": 38, "cl": 5, "eur": 7, "rel": 18},
        "La Liga":        {"max_m": 38, "cl": 5, "eur": 7, "rel": 18},
        "Serie A":        {"max_m": 38, "cl": 4, "eur": 6, "rel": 18},
        "Bundesliga":     {"max_m": 34, "cl": 4, "eur": 6, "rel": 16},
        "Ligue 1":        {"max_m": 34, "cl": 4, "eur": 6, "rel": 16},
        "Liga Portugal":  {"max_m": 34, "cl": 2, "eur": 5, "rel": 16}
    }
    rules = league_rules.get(league_choice, {"max_m": 34, "cl": 3, "eur": 5, "rel": 16})
    if matches_played < 10: return "Normalna", 1.0, "Spokojny początek sezonu", "#ffcc00"

    def get_pts_at(r):
        if total_teams >= r: return sorted_teams[r - 1][1]['Pkt']
        elif total_teams > 0: return sorted_teams[-1][1]['Pkt']
        return 0

    pts_1st, pts_2nd, pts_cl, pts_eur, pts_safe = get_pts_at(1), get_pts_at(2), get_pts_at(rules["cl"]), get_pts_at(rules["eur"]), get_pts_at(rules["rel"] - 1)
    max_pts_left = (rules["max_m"] - matches_played) * 3

    if matches_played >= rules["max_m"] - 10:
        if team_pts + max_pts_left < pts_safe: return "Minimalna", 0.75, "Pewny spadek (Rozbicie zespołu)", "#9da5b1"
        if rank == 1 and (team_pts - pts_2nd) > max_pts_left: return "Zrelaksowana", 0.85, "Mistrzostwo zapewnione (Rezerwy)", "#9da5b1"
        if team_pts >= pts_safe and team_pts + max_pts_left < get_pts_at(rules["eur"]): return "Wakacyjna", 0.85, "Utrzymanie pewne, o nic nie grają", "#9da5b1"
        
        if team_pts >= pts_1st - 6 and rank <= 3: return "Mecz o życie!", 1.3, "Walka o Mistrzostwo!", "#00ff88"
        elif team_pts >= pts_cl - 5 and rank <= rules["cl"] + 2: return "Wysoka", 1.2, "Walka o Ligę Mistrzów", "#00d4ff"
        elif team_pts >= pts_eur - 5 and rank <= rules["eur"] + 2: return "Wysoka", 1.15, "Pościg za pucharami", "#00ff88"
        elif team_pts <= pts_safe + 5: return "Mecz o życie!", 1.35, "Desperacja (Utrzymanie)", "#ff4b4b"
        else: return "Normalna", 1.0, "Środek tabeli (Brak presji)", "#ffcc00"
    else:
        if rank <= rules["cl"]: return "Wysoka", 1.15, "Strefa Ligi Mistrzów", "#00d4ff"
        elif rank <= rules["eur"]: return "Wysoka", 1.1, "Strefa pucharowa", "#00ff88"
        elif rank >= rules["rel"]: return "Wysoka", 1.15, "Strefa spadkowa", "#ff4b4b"
        else: return "Normalna", 1.0, "Bezpieczny środek", "#ffcc00"

def calc_power(stats, mot_val, missing):
    killer_score = stats['killer'] / 10.0
    team_rating = (stats['dom'] * 0.3) + (killer_score * 0.35) + (stats['safety'] * 0.35)
    raw_power = (team_rating / 5.5) * 100 
    motivated_power = raw_power * mot_val
    absence_penalty = 1.0 - (missing * 0.05) 
    final_power = motivated_power * absence_penalty
    if final_power > 105:
        final_power = 105 + (np.log(final_power - 104) * 4) 
    return round(np.clip(final_power, 40, 115), 1)

# ... tutaj kończy się funkcja calc_power ...
    return round(np.clip(final_power, 40, 115), 1)

# === TUTAJ WKLEJASZ NOWY KOD ===
def calculate_kelly(prob_pct, odds, bankroll=1000):
    """Oblicza sugerowaną stawkę na podstawie przewagi matematycznej."""
    p = prob_pct / 100.0
    q = 1.0 - p
    b = float(odds) - 1.0
    
    if b <= 0: return 0
    f = (b * p - q) / b
    
    # Używamy "Fractional Kelly" (0.25), żeby nie zbankrutować przy jednej pomyłce
    safe_f = f * 0.25 
    stake = max(0, safe_f * bankroll)
    return round(stake, 1) # Zwraca np. 42.5 jednostki
# ===============================

def save_bet_to_tracker(date, league, match, pick, prob, odds_key=None):
    file_name = "roi_tracker.csv"
    
    # Wyciągamy kurs wpisany przez Ciebie przed chwilą w okienko
    final_odds = st.session_state.get(odds_key, 1.85) if odds_key else 1.85
    
    new_data = pd.DataFrame([{
        "Data": date,
        "Liga": league,
        "Mecz": match,
        "Typ": pick,
        "Pewnosc_AI": round(prob, 1),
        "Status": "Oczekujący",
        "Kurs": round(float(final_odds), 2), 
        "Zysk_Strata": 0.0
    }])
    
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        new_data.to_csv(file_name, mode='a', header=False, index=False)
    else:
        new_data.to_csv(file_name, index=False)
        
    st.toast(f"✅ Zapisano mecz {match} po kursie {final_odds} do Dziennika ROI!")

def auto_settle_bets():
    file_name = "roi_tracker.csv"
    if not os.path.exists(file_name) or os.path.getsize(file_name) == 0:
        return 0
        
    try:
        df_bets = pd.read_csv(file_name)
    except pd.errors.EmptyDataError:
        return 0
        
    zmiany = 0
    for i, row in df_bets.iterrows():
        if row['Status'] == 'Oczekujący':
            liga = row['Liga']
            mecz = row['Mecz']
            typ = row['Typ']
            data_kuponu = row['Data']
            
            if liga not in all_data: continue
            df_liga = all_data[liga]
            
            if " - " not in mecz: continue
            home_team, away_team = mecz.split(" - ", 1)
            
            # Szukamy tego konkretnego meczu w naszej bazie CSV
            match_data = df_liga[(df_liga['HomeTeam'] == home_team) & (df_liga['AwayTeam'] == away_team)].copy()
            if match_data.empty: continue
            
            # Sortujemy, żeby wziąć najnowsze starcie
            match_data['Date'] = pd.to_datetime(match_data['Date'], dayfirst=True, errors='coerce')
            match_data = match_data.sort_values('Date', ascending=False)
            najnowszy_mecz = match_data.iloc[0].fillna(0)
            
            try:
                bet_date = pd.to_datetime(data_kuponu).date()
                match_date = pd.to_datetime(najnowszy_mecz['Date']).date()
                # Dopuszczamy 1 dzień różnicy ze względu na strefy czasowe (API vs CSV)
                # Jeśli różnica jest większa, znaczy, że strona football-data jeszcze nie wgrała wczorajszych wyników.
                if abs((bet_date - match_date).days) > 1:
                    continue 
            except:
                continue
                
            fthg = najnowszy_mecz.get('FTHG', 0)
            ftag = najnowszy_mecz.get('FTAG', 0)
            ftr = najnowszy_mecz.get('FTR', '')
            
            wygrany = None
            liczby = re.findall(r"[-+]?\d*\.\d+|\d+", typ)
            linia = float(liczby[0]) if liczby else 0
            
            # Weryfikacja 1X2
            if "1X2" in typ:
                if "(1)" in typ and ftr == 'H': wygrany = True
                elif "(2)" in typ and ftr == 'A': wygrany = True
                elif "(X)" in typ and ftr == 'D': wygrany = True
                else: wygrany = False
                
            # Weryfikacja GOLI
            elif "gola" in typ:
                gole = fthg + ftag
                if "Powyżej" in typ: wygrany = gole > linia
                elif "Poniżej" in typ: wygrany = gole < linia
                
            # Weryfikacja KARTEK (Żółte + Czerwone)
            elif "kartek" in typ:
                kartki = najnowszy_mecz.get('HY', 0) + najnowszy_mecz.get('AY', 0) + najnowszy_mecz.get('HR', 0) + najnowszy_mecz.get('AR', 0)
                if "Powyżej" in typ: wygrany = kartki > linia
                elif "Poniżej" in typ: wygrany = kartki < linia
                
            # Weryfikacja ROŻNYCH
            elif "rożnych" in typ:
                rozne = najnowszy_mecz.get('HC', 0) + najnowszy_mecz.get('AC', 0)
                if "Powyżej" in typ: wygrany = rozne > linia
                elif "Poniżej" in typ: wygrany = rozne < linia

            # Zmiana statusu z Oczekującego na rozliczony
            if wygrany is True:
                df_bets.at[i, 'Status'] = 'Wygrany'
                df_bets.at[i, 'Zysk_Strata'] = (100 * row['Kurs']) - 100
                zmiany += 1
            elif wygrany is False:
                df_bets.at[i, 'Status'] = 'Przegrany'
                df_bets.at[i, 'Zysk_Strata'] = -100
                zmiany += 1
                
    if zmiany > 0:
        df_bets.to_csv(file_name, index=False)
        
    return zmiany

def get_advanced_stats(team, side, mode, last_n=None):
    if 'df' not in globals(): return None
    current_df = df[df['Season'] == '2526'].copy()
    
    if mode == "Wszystkie":
        t_data = current_df[(current_df['HomeTeam'] == team) | (current_df['AwayTeam'] == team)].copy()
    else:
        t_data = current_df[current_df['HomeTeam'] == team].copy() if side == 'Home' else current_df[current_df['AwayTeam'] == team].copy()
        
    if len(t_data) == 0: return None
    
    # TIME-DECAY (WAGA CZASU)
    if 'Date' in t_data.columns:
        t_data['Date'] = pd.to_datetime(t_data['Date'], dayfirst=True, errors='coerce')
        t_data = t_data.sort_values('Date', ascending=False)
        
    if last_n: t_data = t_data.head(last_n)
    
    n_matches = len(t_data)
    weights = np.linspace(1.0, 0.3, n_matches) if n_matches > 1 else np.array([1.0])
    t_data['Weight'] = weights
    
    def w_avg(col_h, col_a):
        vals = t_data.apply(lambda r: r.get(col_h, 0) if r['HomeTeam'] == team else r.get(col_a, 0), axis=1).fillna(0)
        return np.average(vals, weights=t_data['Weight'])

    gf, ga = w_avg('FTHG', 'FTAG'), w_avg('FTAG', 'FTHG')
    shots, opp_shots = w_avg('HS', 'AS'), w_avg('AS', 'HS')
    shots_ot, opp_shots_ot = w_avg('HST', 'AST'), w_avg('AST', 'HST')
    corners, opp_corners = w_avg('HC', 'AC'), w_avg('AC', 'HC')
    fouls, yellows, reds = w_avg('HF', 'AF'), w_avg('HY', 'AY'), w_avg('HR', 'AR')
    ht_gf = w_avg('HTHG', 'HTAG') if 'HTHG' in t_data.columns else gf/2
    
    # WŁASNE xG (EXPECTED GOALS)
    xg_for = (gf * 0.4) + (shots_ot * 0.4) + (corners * 0.05)
    xg_against = (ga * 0.4) + (opp_shots_ot * 0.4) + (opp_corners * 0.05)

    dom = np.clip((shots_ot * 1.0 + corners * 0.5) / 1.5, 1, 10)
    killer = np.clip((gf / shots_ot * 100) if shots_ot > 0 else 0, 0, 100)
    safety = np.clip(12 - (xg_against * 2.5), 1, 10)
    chaos = np.clip((fouls * 0.3 + yellows * 1.5) / 1.2, 1, 10)
    
    return {
        'gf': gf, 'ga': ga, 'ht_gf': ht_gf, 'shots': shots, 'shots_ot': shots_ot, 
        'opp_shots_ot': opp_shots_ot, 'xg_for': xg_for, 'xg_against': xg_against,
        'fouls': fouls, 'yellows': yellows, 'reds': reds,
        'corners': corners, 'opp_corners': opp_corners,
        'dom': dom, 'killer': killer, 'safety': safety, 'chaos': chaos, 'matches': n_matches
    }

def get_team_form_trend(team, side, mode, last_n=5):
    if 'df' not in globals(): return "", "", ""
    if mode == "Wszystkie": t_data = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].copy()
    else: t_data = df[df['HomeTeam'] == team].copy() if side == 'Home' else df[df['AwayTeam'] == team].copy()
        
    if 'Date' in t_data.columns:
        t_data['Date'] = pd.to_datetime(t_data['Date'], dayfirst=True, errors='coerce')
        t_data = t_data.sort_values('Date', ascending=False)
        
    t_data = t_data.head(last_n).iloc[::-1]

    symbols, points = [], []
    for _, row in t_data.iterrows():
        is_h = row['HomeTeam'] == team
        if row['FTR'] == ('H' if is_h else 'A'): symbols.append('🟢'); points.append(3)
        elif row['FTR'] == 'D': symbols.append('🟡'); points.append(1)
        else: symbols.append('🔴'); points.append(0)
            
    total_pts = sum(points)
    if total_pts <= 3: trend_text, trend_color = "🚨 Tragiczna forma", "#ff4b4b"
    elif total_pts >= 13: trend_text, trend_color = "🔥 Wybitna forma", "#00ff88"
    elif len(points) >= 4:
        recent_avg = sum(points[-2:]) / 2.0
        older_avg = sum(points[:-2]) / len(points[:-2])
        if recent_avg > older_avg + 0.5: trend_text, trend_color = "📈 Trend wzrostowy", "#00ff88"
        elif recent_avg < older_avg - 0.5: trend_text, trend_color = "📉 Zjazd formy", "#ff4b4b"
        else: trend_text, trend_color = "➡️ Stabilna / Mieszana", "#ffcc00"
    else: trend_text, trend_color = "➡️ Brak danych", "#9da5b1"
        
    return "".join(symbols), trend_text, trend_color

def get_h2h_stats(team1, team2, last_n=5):
    if 'df' not in globals(): return None
    h2h_df = df[((df['HomeTeam'] == team1) & (df['AwayTeam'] == team2)) | ((df['HomeTeam'] == team2) & (df['AwayTeam'] == team1))].copy()
    if len(h2h_df) == 0: return None
    if 'Date' in h2h_df.columns:
        h2h_df['Date'] = pd.to_datetime(h2h_df['Date'], dayfirst=True, errors='coerce')
        h2h_df = h2h_df.sort_values('Date', ascending=False)
    h2h_df = h2h_df.head(last_n)
    t1_wins = draws = t2_wins = 0
    for _, row in h2h_df.iterrows():
        if row['FTR'] == 'D': draws += 1
        elif (row['HomeTeam'] == team1 and row['FTR'] == 'H') or (row['AwayTeam'] == team1 and row['FTR'] == 'A'): t1_wins += 1
        else: t2_wins += 1
    avg_goals = (h2h_df['FTHG'].sum() + h2h_df['FTAG'].sum()) / len(h2h_df) if len(h2h_df) > 0 else 0
    return {'data': h2h_df, 't1_w': t1_wins, 'draws': draws, 't2_w': t2_wins, 'avg_goals': avg_goals, 'total_matches': len(h2h_df)}

def create_radar_chart(h_data, a_data, h_name, a_name):
    categories = ['🔥 Dominacja', '🎯 Kiler', '🧱 Obrona', '🧨 Chaos']
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[h_data['dom']*10, h_data['killer'], h_data['safety']*10, h_data['chaos']*10], theta=categories, fill='toself', name=h_name, line_color='#00ff88'))
    fig.add_trace(go.Scatterpolar(r=[a_data['dom']*10, a_data['killer'], a_data['safety']*10, a_data['chaos']*10], theta=categories, fill='toself', name=a_name, line_color='#ff4b4b'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False), bgcolor="rgba(0,0,0,0)"), showlegend=True, legend=dict(itemclick=False, itemdoubleclick=False), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=14))
    return fig


# =====================================================================
# --- EKRAN 1: CENTRUM ANALIZY ---
# =====================================================================
if menu_choice == "🎯 Centrum Analizy":
    st.markdown("<h2 style='text-align: center; color: #00ff88; text-transform: uppercase; letter-spacing: 2px;'>🏆 Centrum Analizy Meczowej</h2>", unsafe_allow_html=True)
    col_h, col_vs, col_a = st.columns([4, 1, 4])

    with col_h: h_team = st.selectbox("🏠 DRUŻYNA GOSPODARZY", teams, index=0)
    with col_vs: st.markdown("<h1 style='text-align: center; margin-top: 25px; color: #ffcc00; text-shadow: 0 0 15px rgba(255, 204, 0, 0.5);'>🆚</h1>", unsafe_allow_html=True)
    with col_a: a_team = st.selectbox("✈️ DRUŻYNA GOŚCI", teams, index=1 if len(teams) > 1 else 0)

    # NOWOŚĆ: Kontrola Osłabień Kadrowych
    st.markdown("<div style='margin-top: -10px; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    col_miss_h, col_miss_vs, col_miss_a = st.columns([4, 1, 4])
    with col_miss_h:
        h_missing = st.slider(f"🚑 Kluczowe osłabienia ({h_team})", min_value=0, max_value=5, value=0, help="Ilu kluczowych zawodników z podstawowej '11' dzisiaj nie zagra? (Kontuzje, kartki)")
    with col_miss_a:
        a_missing = st.slider(f"🚑 Kluczowe osłabienia ({a_team})", min_value=0, max_value=5, value=0, help="Ilu kluczowych zawodników z podstawowej '11' dzisiaj nie zagra? (Kontuzje, kartki)")

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 20px 0;'>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 ANALIZA PRO", "📊 STATYSTYKI AI", "📋 PREDYKCJE", "🟨 KARTKI", "⛳ ROŻNE"])

    with tab1:
        st.header("🧠 AI Scenario Simulator & Analysis")
        h_stats = get_advanced_stats(h_team, 'Home', 'Wszystkie')
        a_stats = get_advanced_stats(a_team, 'Away', 'Wszystkie')
        
        if h_stats and a_stats:
            st.markdown("### 🏟️ Kontekst Meczu i Motywacja (Smart System)")
            st.markdown("<p style='color: #9da5b1; font-size: 0.85rem;'>AI analizuje układ tabeli i punkty potrzebne do celu. Jeśli cel jest już osiągnięty, motywacja drastycznie spada.</p>", unsafe_allow_html=True)
            
            def get_auto_motivation(team_name):
                curr_df = df[df['Season'] == '2526'] if 'Season' in df.columns else df
                stats = {}
                for t in curr_df['HomeTeam'].unique():
                    df_t = curr_df[(curr_df['HomeTeam']==t) | (curr_df['AwayTeam']==t)]
                    pkt = 0
                    for _, row in df_t.iterrows():
                        if (row['HomeTeam'] == t and row['FTR'] == 'H') or (row['AwayTeam'] == t and row['FTR'] == 'A'): pkt += 3
                        elif row['FTR'] == 'D': pkt += 1
                    stats[t] = {'M': len(df_t), 'Pkt': pkt}
                    
                if team_name not in stats or stats[team_name]['M'] == 0: return "Normalna", 1.0, "Początek sezonu", "#ffcc00"
                    
                sorted_teams = sorted(stats.items(), key=lambda x: x[1]['Pkt'], reverse=True)
                total_teams = len(sorted_teams)
                rank = next((idx + 1 for idx, (t, _) in enumerate(sorted_teams) if t == team_name), 1)
                matches_played, team_pts = stats[team_name]['M'], stats[team_name]['Pkt']
                
                league_rules = {
                    "Premier League": {"max_m": 38, "cl": 5, "eur": 7, "rel": 18},
                    "La Liga":        {"max_m": 38, "cl": 5, "eur": 7, "rel": 18},
                    "Serie A":        {"max_m": 38, "cl": 4, "eur": 6, "rel": 18},
                    "Bundesliga":     {"max_m": 34, "cl": 4, "eur": 6, "rel": 16},
                    "Ligue 1":        {"max_m": 34, "cl": 4, "eur": 6, "rel": 16},
                    "Liga Portugal":  {"max_m": 34, "cl": 2, "eur": 5, "rel": 16}
                }
                rules = league_rules.get(league_choice, {"max_m": 34, "cl": 3, "eur": 5, "rel": 16})
                if matches_played < 10: return "Normalna", 1.0, "Spokojny początek sezonu", "#ffcc00"

                def get_pts_at(r):
                    if total_teams >= r: return sorted_teams[r - 1][1]['Pkt']
                    elif total_teams > 0: return sorted_teams[-1][1]['Pkt']
                    return 0

                pts_1st, pts_2nd, pts_cl, pts_eur, pts_safe = get_pts_at(1), get_pts_at(2), get_pts_at(rules["cl"]), get_pts_at(rules["eur"]), get_pts_at(rules["rel"] - 1)
                max_pts_left = (rules["max_m"] - matches_played) * 3

                if matches_played >= rules["max_m"] - 10:
                    # SMART MOTIVATION: Cel już osiągnięty lub szanse stracone
                    if team_pts + max_pts_left < pts_safe: return "Minimalna", 0.75, "Pewny spadek (Rozbicie zespołu)", "#9da5b1"
                    if rank == 1 and (team_pts - pts_2nd) > max_pts_left: return "Zrelaksowana", 0.85, "Mistrzostwo zapewnione (Rezerwy)", "#9da5b1"
                    if team_pts >= pts_safe and team_pts + max_pts_left < get_pts_at(rules["eur"]): return "Wakacyjna", 0.85, "Utrzymanie pewne, o nic nie grają", "#9da5b1"
                    
                    if team_pts >= pts_1st - 6 and rank <= 3: return "Mecz o życie!", 1.3, "Walka o Mistrzostwo!", "#00ff88"
                    elif team_pts >= pts_cl - 5 and rank <= rules["cl"] + 2: return "Wysoka", 1.2, "Walka o Ligę Mistrzów", "#00d4ff"
                    elif team_pts >= pts_eur - 5 and rank <= rules["eur"] + 2: return "Wysoka", 1.15, "Pościg za pucharami", "#00ff88"
                    elif team_pts <= pts_safe + 5: return "Mecz o życie!", 1.35, "Desperacja (Utrzymanie)", "#ff4b4b"
                    else: return "Normalna", 1.0, "Środek tabeli (Brak presji)", "#ffcc00"
                else:
                    if rank <= rules["cl"]: return "Wysoka", 1.15, "Strefa Ligi Mistrzów", "#00d4ff"
                    elif rank <= rules["eur"]: return "Wysoka", 1.1, "Strefa pucharowa", "#00ff88"
                    elif rank >= rules["rel"]: return "Wysoka", 1.15, "Strefa spadkowa", "#ff4b4b"
                    else: return "Normalna", 1.0, "Bezpieczny środek", "#ffcc00"

            mot_h_label, mot_h_val, mot_h_desc, mot_h_col = get_auto_motivation(h_team)
            mot_a_label, mot_a_val, mot_a_desc, mot_a_col = get_auto_motivation(a_team)
            
            c_mot1, c_mot2 = st.columns(2)
            with c_mot1:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.02); border-left: 4px solid {mot_h_col}; padding: 12px 15px; border-radius: 6px; margin-bottom: 20px;"><div style="font-size: 0.75rem; color: #9da5b1; text-transform: uppercase;">Kontekst: {h_team}</div><div style="font-size: 1.1rem; font-weight: bold; color: {mot_h_col};">{mot_h_label}</div><div style="font-size: 0.85rem; margin-top: 3px; color: white;">{mot_h_desc}</div></div>""", unsafe_allow_html=True)
            with c_mot2:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.02); border-left: 4px solid {mot_a_col}; padding: 12px 15px; border-radius: 6px; margin-bottom: 20px;"><div style="font-size: 0.75rem; color: #9da5b1; text-transform: uppercase;">Kontekst: {a_team}</div><div style="font-size: 1.1rem; font-weight: bold; color: {mot_a_col};">{mot_a_label}</div><div style="font-size: 0.85rem; margin-top: 3px; color: white;">{mot_a_desc}</div></div>""", unsafe_allow_html=True)

            def calc_power(stats, mot_val, missing):
                killer_score = stats['killer'] / 10.0
                team_rating = (stats['dom'] * 0.3) + (killer_score * 0.35) + (stats['safety'] * 0.35)
                
                raw_power = (team_rating / 5.5) * 100 
                motivated_power = raw_power * mot_val
                # OSŁABIENIA: Każdy brak kluczowego gracza to spadek o ok 5%
                absence_penalty = 1.0 - (missing * 0.05) 
                
                final_power = motivated_power * absence_penalty
                
                # CAPPING: Logarytmiczne spłaszczenie (żeby nie było cyborgów po 140%)
                if final_power > 105:
                    final_power = 105 + (np.log(final_power - 104) * 4) 
                    
                return round(np.clip(final_power, 40, 115), 1)

            auto_h_power, auto_a_power = calc_power(h_stats, mot_h_val, h_missing), calc_power(a_stats, mot_a_val, a_missing)
            h_adj, a_adj = auto_h_power, auto_a_power

            st.markdown("### ⚡ Obliczona Siła Zespołów (AI Power Index)")
            st.markdown("<p style='color: #9da5b1; font-size: 0.85rem;'>System przemnożył bazowe statystyki przez motywację i nałożył kary za osłabienia w składzie.</p>", unsafe_allow_html=True)
            
            c_pow1, c_pow2 = st.columns(2)
            with c_pow1:
                st.markdown(f"""<div style="background: rgba(0, 255, 136, 0.05); border: 1px dashed #00ff88; border-radius: 12px; padding: 15px; text-align: center;"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Algorytm wyliczył moc: <b>{h_team}</b></div><div style="color: #00ff88; font-size: 2.2rem; font-weight: 900;">{auto_h_power}%</div></div>""", unsafe_allow_html=True)
            with c_pow2:
                st.markdown(f"""<div style="background: rgba(255, 75, 75, 0.05); border: 1px dashed #ff4b4b; border-radius: 12px; padding: 15px; text-align: center;"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Algorytm wyliczył moc: <b>{a_team}</b></div><div style="color: #ff4b4b; font-size: 2.2rem; font-weight: 900;">{auto_a_power}%</div></div>""", unsafe_allow_html=True)
            st.write("")
            
            # =====================================================================
            # --- SUPER-MODEL: xG + ELO + ZAAWANSOWANY DIXON-COLES ---
            # =====================================================================
            base_l_h = (h_stats['gf'] + a_stats['ga']) / 2.0
            base_l_a = (a_stats['gf'] + h_stats['ga']) / 2.0
            
            l_h = max(0.1, base_l_h * (h_adj / 100.0))
            l_a = max(0.1, base_l_a * (a_adj / 100.0))

            s_h = np.random.poisson(l_h, 20000)
            s_a = np.random.poisson(l_a, 20000)
            
            raw_win, raw_draw, raw_loss = np.mean(s_h > s_a), np.mean(s_h == s_a), np.mean(s_h < s_a)
            
            # ZAAWANSOWANA KOREKTA NA REMISY (Dixon-Coles Upgrade)
            prob_00 = np.mean((s_h == 0) & (s_a == 0))
            prob_11 = np.mean((s_h == 1) & (s_a == 1))
            
            # Jeśli mecz jest zacięty i underowy, remis jest dużo bardziej prawdopodobny
            dc_boost_draw = 0.04 + (prob_00 * 0.2) + (prob_11 * 0.2)
            if abs(h_adj - a_adj) < 10: dc_boost_draw += 0.05
                
            chaos_factor = (h_stats['chaos'] + a_stats['chaos']) / 20.0 
            
            # Duży chaos zmniejsza szansę na ułożony remis
            adj_draw = raw_draw + dc_boost_draw - (chaos_factor * 0.03) 
            
            if raw_win > raw_loss:
                adj_win = raw_win - (dc_boost_draw * 0.7)
                adj_loss = raw_loss - (dc_boost_draw * 0.3)
            else:
                adj_loss = raw_loss - (dc_boost_draw * 0.7)
                adj_win = raw_win - (dc_boost_draw * 0.3)
                
            adj_win, adj_draw, adj_loss = max(0, adj_win), max(0, adj_draw), max(0, adj_loss)
            total = adj_win + adj_draw + adj_loss
            win, draw, loss = adj_win/total, adj_draw/total, adj_loss/total
            # =====================================================================

            st.write("")
            st.markdown("### 🎯 Przewidywane Prawdopodobieństwo (1X2)")
            p_win, p_draw, p_loss = win * 100, draw * 100, loss * 100
            
            st.markdown(f"""
            <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                <div style="flex: 1; background: rgba(0, 255, 136, 0.05); border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2);"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">🏠 1 ({h_team})</div><div style="color: #00ff88; font-size: 2.2rem; font-weight: 900; margin-top: 5px;">{p_win:.1f}%</div></div>
                <div style="flex: 1; background: rgba(255, 204, 0, 0.05); border: 1px solid rgba(255, 204, 0, 0.3); border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2);"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">⚖️ X (REMIS)</div><div style="color: #ffcc00; font-size: 2.2rem; font-weight: 900; margin-top: 5px;">{p_draw:.1f}%</div></div>
                <div style="flex: 1; background: rgba(255, 75, 75, 0.05); border: 1px solid rgba(255, 75, 75, 0.3); border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2);"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">✈️ 2 ({a_team})</div><div style="color: #ff4b4b; font-size: 2.2rem; font-weight: 900; margin-top: 5px;">{p_loss:.1f}%</div></div>
            </div>
            <div style="width: 100%; height: 12px; border-radius: 6px; display: flex; overflow: hidden; background-color: #2b2f3b; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);"><div style="width: {p_win}%; background-color: #00ff88;"></div><div style="width: {p_draw}%; background-color: #ffcc00;"></div><div style="width: {p_loss}%; background-color: #ff4b4b;"></div></div>
            <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.75rem; color: #9da5b1; margin-bottom: 20px;"><span>Szansa Gospodarza</span><span>Szansa Remisu</span><span>Szansa Gościa</span></div>
            """, unsafe_allow_html=True)

            st.write("")
            st.markdown("### 📊 Rynki Bramkowe i Połowiczne")
            
            btts_yes = np.clip(np.mean((s_h > 0) & (s_a > 0)) * 1.05, 0, 1)
            total_goals = s_h + s_a
            o15, o25, o35 = np.mean(total_goals > 1.5), np.mean(total_goals > 2.5), np.mean(total_goals > 3.5)

            # REALISTYCZNE HT (Ok. 43% bramek wpada w 1. połowie)
            l_h_ht = l_h * 0.43
            l_a_ht = l_a * 0.43
            s_h_ht, s_a_ht = np.random.poisson(max(0.1, l_h_ht), 8000), np.random.poisson(max(0.1, l_a_ht), 8000)
            ht_win, ht_draw, ht_loss = np.mean(s_h_ht > s_a_ht), np.mean(s_h_ht == s_a_ht), np.mean(s_h_ht < s_a_ht)
            
            total_goals_ht = s_h_ht + s_a_ht
            o05_ht, o15_ht, btts_ht = np.mean(total_goals_ht > 0.5), np.mean(total_goals_ht > 1.5), np.mean((s_h_ht > 0) & (s_a_ht > 0))

            def get_bar_color(val):
                if val >= 0.60: return "#00ff88"
                elif val >= 0.40: return "#ffcc00"
                else: return "#ff4b4b"

            def make_row(label, val):
                pct, color = val * 100, get_bar_color(val)
                return f"""<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 15px; background: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 8px; border-left: 3px solid {color}; box-shadow: 0 2px 5px rgba(0,0,0,0.1);"><span style="color: #ffffff; font-weight: bold; font-size: 0.9rem;">{label}</span><div style="display: flex; align-items: center; gap: 12px;"><div style="width: 70px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;"><div style="width: {pct}%; height: 100%; background: {color};"></div></div><span style="color: {color}; font-weight: 900; font-size: 1.1rem; min-width: 55px; text-align: right;">{pct:.1f}%</span></div></div>"""

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown(f"""<div style="background: linear-gradient(180deg, rgba(30,33,43,1) 0%, rgba(22,25,34,1) 100%); padding: 15px; border-radius: 12px; border: 1px solid rgba(0, 255, 136, 0.1);"><h4 style="color: #9da5b1; text-align: center; margin-top: 0; margin-bottom: 15px; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;">⚽ Gole w meczu (FT)</h4>{make_row("Obie strzelą (BTTS)", btts_yes)}{make_row("Powyżej 1.5 gola", o15)}{make_row("Powyżej 2.5 gola", o25)}{make_row("Powyżej 3.5 gola", o35)}</div>""", unsafe_allow_html=True)
            with col_b2:
                st.markdown(f"""<div style="background: linear-gradient(180deg, rgba(30,33,43,1) 0%, rgba(22,25,34,1) 100%); padding: 15px; border-radius: 12px; border: 1px solid rgba(0, 255, 136, 0.1);"><h4 style="color: #9da5b1; text-align: center; margin-top: 0; margin-bottom: 15px; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;">⏱️ Wynik i Gole do przerwy (HT)</h4>{make_row(f"1. połowa: {h_team}", ht_win)}{make_row("Remis do przerwy", ht_draw)}{make_row(f"1. połowa: {a_team}", ht_loss)}<hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 15px 0;">{make_row("Powyżej 0.5 gola (HT)", o05_ht)}{make_row("Powyżej 1.5 gola (HT)", o15_ht)}{make_row("Obie strzelą do przerwy", btts_ht)}</div>""", unsafe_allow_html=True)
            st.write("")
            
            st.markdown("#### 🎯 Najbardziej Prawdopodobne Wyniki Meczu")
            results = []
            for h_g in range(6): # Szukamy wyników od 0 do 5 bramek
                for a_g in range(6):
                    prob = np.mean((s_h == h_g) & (s_a == a_g)) * 100
                    if prob > 1.0: results.append((h_g, a_g, prob))

            results = sorted(results, key=lambda x: x[2], reverse=True)[:8]
            
            if len(results) > 0:
                cols = st.columns(4)
                for idx, (h_g, a_g, prob) in enumerate(results):
                    with cols[idx % 4]:
                        st.markdown(f"""<div style="background: linear-gradient(135deg, #1e212b, #161922); border-radius: 12px; padding: 15px; text-align: center; border: 2px solid rgba(0, 255, 136, 0.3); margin-bottom: 10px;"><h2 style="margin: 0; color: #00ff88;">{h_g} - {a_g}</h2><p style="margin: 5px 0 0 0; font-size: 1.1em; color: white;"><strong>{prob:.1f}%</strong></p></div>""", unsafe_allow_html=True)
            else:
                st.info("⚠️ System rozproszył prawdopodobieństwo (zbyt duży chaos bramkowy). Brak wyraźnie dominującego wyniku.")

            st.divider()
            st.markdown("<h3 style='text-align: center; color: #00ff88;'>⚖️ Zaawansowany Value Bet Finder (1X2)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #9da5b1;'>Teraz z uwzględnieniem matematycznego sufitu dla faworytów. System łapie prawdziwe różnice w kursach.</p>", unsafe_allow_html=True)

            # INTEGRACJA THE ODDS API DLA KURSÓW
            fetched_odds = fetch_live_odds(user_api_key, league_choice, h_team, a_team)
            default_1, default_x, default_2 = 2.50, 3.20, 2.80
            provider_text = "Brak API / Wpisz ręcznie"
            
            if fetched_odds:
                default_1 = fetched_odds.get('1', default_1)
                default_x = fetched_odds.get('X', default_x)
                default_2 = fetched_odds.get('2', default_2)
                provider_text = f"Pobrano z The Odds API ({fetched_odds.get('bookmaker', 'Auto')})"
                st.success(f"✅ {provider_text}")

            col_o1, col_ox, col_o2 = st.columns(3)
            odds_1 = col_o1.number_input(f"Kurs 1 ({h_team})", min_value=1.01, value=float(default_1), step=0.05)
            odds_x = col_ox.number_input("Kurs X (Remis)", min_value=1.01, value=float(default_x), step=0.05)
            odds_2 = col_o2.number_input(f"Kurs 2 ({a_team})", min_value=1.01, value=float(default_2), step=0.05)

            if odds_1 > 1.01 and odds_x > 1.01 and odds_2 > 1.01:
                prob_1, prob_x, prob_2 = 1/odds_1, 1/odds_x, 1/odds_2
                margin = ((prob_1 + prob_x + prob_2) - 1) * 100
                ev_1_pct, ev_x_pct, ev_2_pct = ((win * odds_1) - 1) * 100, ((draw * odds_x) - 1) * 100, ((loss * odds_2) - 1) * 100
                best_ev = max(ev_1_pct, ev_x_pct, ev_2_pct)
                
                if best_ev == ev_1_pct: best_pick, best_odds, ai_prob = f"1 ({h_team})", odds_1, win
                elif best_ev == ev_x_pct: best_pick, best_odds, ai_prob = "X (Remis)", odds_x, draw
                else: best_pick, best_odds, ai_prob = f"2 ({a_team})", odds_2, loss

                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta", value=best_ev,
                    title={'text': f"Rekomendacja: <b>{best_pick}</b><br><span style='font-size:0.8em;color:#9da5b1'>Kurs: {best_odds} | Szansa AI: {ai_prob*100:.1f}%</span>"},
                    delta={'reference': 0, 'increasing': {'color': "#00ff88"}, 'decreasing': {'color': "#ff4b4b"}},
                    gauge={'axis': {'range': [-30, 30], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': "#00ff88" if best_ev > 0 else "#ff4b4b"}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 2, 'bordercolor': "#2b2f3b", 'steps': [{'range': [-30, 0], 'color': "rgba(255, 75, 75, 0.15)"}, {'range': [0, 10], 'color': "rgba(255, 204, 0, 0.15)"}, {'range': [10, 30], 'color': "rgba(0, 255, 136, 0.15)"}], 'threshold': {'line': {'color': "white", 'width': 3}, 'thickness': 0.75, 'value': best_ev}}
                ))
                fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=350, margin=dict(l=20, r=20, t=50, b=20))
                
                col_g1, col_g2 = st.columns([1.2, 1])
                with col_g1: st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
                with col_g2:
                    st.write("")
                    margin_txt = f"🟢 Bardzo niska ({margin:.1f}%)" if margin < 3.5 else (f"🟡 Przeciętna ({margin:.1f}%)" if margin < 6.0 else f"🔴 Złodziejska ({margin:.1f}%)")
                    st.markdown(f"<div style='padding:10px; background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 15px;'><b>Marża bukmachera:</b> {margin_txt}</div>", unsafe_allow_html=True)
                    if best_ev > 5: st.success(f"🔥 **POTĘŻNE VALUE!**\nGrając na **{best_pick}** przy tym kursie, masz matematyczną przewagę w długim terminie ({best_ev:.1f}% zysku na każdym zakładzie).")
                    elif best_ev > 0: st.warning(f"⚖️ **MINIMALNE VALUE**\nGra na **{best_pick}** jest lekko opłacalna (+{best_ev:.1f}%), ale bukmacher wystawił mocne kursy.")
                    else: st.error(f"❌ **BRAK VALUE W TYM MECZU**\nBukmacher idealnie wycenił szanse. Najmniejsza strata to {best_pick} ({best_ev:.1f}%).")
        else: st.warning("Brak wystarczających danych.")

    with tab2:
        with st.expander("📖 Przewodnik: Jak czytać wskaźniki AI?"):
            st.markdown("""<div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px;"><h3 style="color: #00ff88; margin-top: 0;">🧠 System Taktyczny AI</h3><p style="color: #9da5b1;">Nasze algorytmy analizują twarde dane, aby stworzyć unikalny profil DNA zespołu.</p><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;"><div style="border-left: 3px solid #00ff88; padding-left: 15px;"><b style="color: #00ff88;">🔥 Dominacja</b><br><small>Kontrola tempa gry.</small></div><div style="border-left: 3px solid #ff4b4b; padding-left: 15px;"><b style="color: #ff4b4b;">🎯 Kiler</b><br><small>Skuteczność ataku.</small></div><div style="border-left: 3px solid #ffcc00; padding-left: 15px;"><b style="color: #ffcc00;">🧱 Obrona</b><br><small>Stabilność defensywy.</small></div><div style="border-left: 3px solid #00d4ff; padding-left: 15px;"><b style="color: #00d4ff;">🧨 Chaos</b><br><small>Agresja i ryzyko kartek.</small></div></div></div>""", unsafe_allow_html=True)
            st.write("")

        c_f1, c_f2 = st.columns([2, 1])
        with c_f1: stat_mode = st.radio("Zakres danych:", ["Wszystkie", "Tylko Dom/Wyjazd"], horizontal=True)
        with c_f2: use_form_filter = st.checkbox("🔥 Analiza ostatniej formy (5 meczów)", value=False)
        
        last_n_matches = 5 if use_form_filter else None
        h_data = get_advanced_stats(h_team, 'Home', stat_mode, last_n=last_n_matches)
        a_data = get_advanced_stats(a_team, 'Away', stat_mode, last_n=last_n_matches)
        h_symbols, h_trend_txt, h_trend_col = get_team_form_trend(h_team, 'Home', stat_mode, last_n=5)
        a_symbols, a_trend_txt, a_trend_col = get_team_form_trend(a_team, 'Away', stat_mode, last_n=5)

        if h_data and a_data:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""<div style="background: linear-gradient(135deg, #1e212b, #11131a); padding: 20px; border-radius: 20px; border: 1px solid rgba(0, 255, 136, 0.2); text-align: center;"><div style="font-size: 0.8rem; color: #00ff88; text-transform: uppercase; letter-spacing: 2px;">GOSPODARZ</div><div style="font-size: 1.8rem; font-weight: 900; color: white;">{h_team}</div><div style="font-size: 1.4rem; letter-spacing: 5px; margin: 10px 0;">{h_symbols}</div><div style="color: {h_trend_col}; font-weight: bold; font-size: 0.9rem;">{h_trend_txt}</div><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;"><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">DOMINACJA</small><br><b style="color:#00ff88;">{h_data['dom']:.1f}</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">KILER</small><br><b style="color:#ff4b4b;">{h_data['killer']:.1f}%</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">OBRONA</small><br><b style="color:#ffcc00;">{h_data['safety']:.1f}</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">CHAOS</small><br><b style="color:#00d4ff;">{h_data['chaos']:.1f}</b></div></div></div>""", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""<div style="background: linear-gradient(135deg, #1e212b, #11131a); padding: 20px; border-radius: 20px; border: 1px solid rgba(255, 75, 75, 0.2); text-align: center;"><div style="font-size: 0.8rem; color: #ff4b4b; text-transform: uppercase; letter-spacing: 2px;">GOŚĆ</div><div style="font-size: 1.8rem; font-weight: 900; color: white;">{a_team}</div><div style="font-size: 1.4rem; letter-spacing: 5px; margin: 10px 0;">{a_symbols}</div><div style="color: {a_trend_col}; font-weight: bold; font-size: 0.9rem;">{a_trend_txt}</div><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;"><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">DOMINACJA</small><br><b style="color:#00ff88;">{a_data['dom']:.1f}</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">KILER</small><br><b style="color:#ff4b4b;">{a_data['killer']:.1f}%</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">OBRONA</small><br><b style="color:#ffcc00;">{a_data['safety']:.1f}</b></div><div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 10px;"><small style="color:#9da5b1;">CHAOS</small><br><b style="color:#00d4ff;">{a_data['chaos']:.1f}</b></div></div></div>""", unsafe_allow_html=True)

            st.write("")
            st.markdown("<h3 style='text-align: center;'>⚔️ Bitwa na DNA (Radar Match)</h3>", unsafe_allow_html=True)
            st.plotly_chart(create_radar_chart(h_data, a_data, h_team, a_team), use_container_width=True)

            st.markdown("<h3 style='text-align: center;'>📊 Bezpośrednie Porównanie Średnich</h3>", unsafe_allow_html=True)
            def vs_row(label, val1, val2, color="#00ff88"):
                total = val1 + val2 if (val1 + val2) > 0 else 1
                return f"""<div style="margin-bottom: 15px;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-weight: bold; font-size: 0.85rem;"><span style="color: white;">{val1:.2f}</span><span style="color: #9da5b1; text-transform: uppercase;">{label}</span><span style="color: white;">{val2:.2f}</span></div><div style="display: flex; width: 100%; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden;"><div style="width: {(val1/total)*100}%; background: {color};"></div><div style="width: {(val2/total)*100}%; background: #ff4b4b;"></div></div></div>"""

            st.markdown(f"""<div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05);"><div style="color: #00ff88; font-size: 0.7rem; margin-bottom: 15px; text-align: center; letter-spacing: 2px;">SKUTECZNOŚĆ</div>{vs_row("Gole Zdobyte", h_data['gf'], a_data['gf'])}{vs_row("Gole Stracone", h_data['ga'], a_data['ga'])}<div style="color: #ffcc00; font-size: 0.7rem; margin: 20px 0 15px 0; text-align: center; letter-spacing: 2px;">AKTYWNOŚĆ</div>{vs_row("Strzały Celne", h_data['shots_ot'], a_data['shots_ot'], "#ffcc00")}{vs_row("Rzuty Rożne", h_data['corners'], a_data['corners'], "#ffcc00")}<div style="color: #00d4ff; font-size: 0.7rem; margin: 20px 0 15px 0; text-align: center; letter-spacing: 2px;">DYSCYPLINA</div>{vs_row("Faule", h_data['fouls'], a_data['fouls'], "#00d4ff")}{vs_row("Żółte Kartki", h_data['yellows'], a_data['yellows'], "#00d4ff")}</div>""", unsafe_allow_html=True)
            st.divider()

            def build_html_table(data, team1, team2):
                stats = []
                for t in data['HomeTeam'].unique():
                    df_t = data[(data['HomeTeam']==t) | (data['AwayTeam']==t)]
                    if len(df_t) == 0: continue
                    w, r, p, gz, gs, pkt = 0, 0, 0, 0, 0, 0
                    for _, row in df_t.iterrows():
                        is_h = row['HomeTeam'] == t
                        z, s = (row['FTHG'], row['FTAG']) if is_h else (row['FTAG'], row['FTHG'])
                        gz += z; gs += s
                        if (is_h and row['FTR'] == 'H') or (not is_h and row['FTR'] == 'A'): pkt += 3; w += 1
                        elif row['FTR'] == 'D': pkt += 1; r += 1
                        else: p += 1
                    stats.append({'Drużyna': t, 'M': len(df_t), 'W': w, 'R': r, 'P': p, 'Bramki': f"{int(gz)}:{int(gs)}", 'Pkt': pkt})
                full_df = pd.DataFrame(stats).sort_values(by=['Pkt'], ascending=False).reset_index(drop=True)
                full_df.index += 1
                final_view = full_df[full_df['Drużyna'].isin([team1, team2])].copy()
                final_view.insert(0, 'LP', final_view.index)
                return final_view

            st.write("")
            st.markdown("<h3 style='text-align: center; color: white;'>🏆 Sytuacja w Tabeli i Historia H2H</h3>", unsafe_allow_html=True)
            st.markdown("<style>.bet-table { width: 100%; border-collapse: collapse; border-radius: 12px; overflow: hidden; background: linear-gradient(180deg, #1e212b 0%, #161922 100%); border: 1px solid rgba(255,255,255,0.05); margin-top: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); } .bet-table th { background: rgba(0, 0, 0, 0.4); color: #9da5b1; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; padding: 15px 10px; border-bottom: 2px solid rgba(255,255,255,0.05); text-align: center; } .bet-table td { padding: 12px 10px; color: #ffffff; border-bottom: 1px solid rgba(255,255,255,0.02); text-align: center; font-size: 0.9rem; transition: background 0.3s ease; } .bet-table tr:hover td { background: rgba(0, 184, 255, 0.05); } .bet-table tr:last-child td { border-bottom: none; }</style>", unsafe_allow_html=True)

            t_mini, t_h2h = st.tabs(["📊 Tabela Ligowa", "⚔️ Bezpośrednie Starcia (H2H)"])
            with t_mini:
                mini_tab = build_html_table(df[df['Season'] == '2526'], h_team, a_team)
                table_html = "<table class='bet-table'><thead><tr><th style='width: 50px;'>LP</th><th style='text-align: left;'>Drużyna</th><th>M</th><th style='color: #00ff88;'>W</th><th style='color: #ffcc00;'>R</th><th style='color: #ff4b4b;'>P</th><th>Bramki</th><th style='color: #00b8ff;'>Pkt</th></tr></thead><tbody>"
                for _, row in mini_tab.iterrows(): table_html += f"<tr><td style='color: #9da5b1; font-weight: bold;'>{row['LP']}</td><td style='text-align: left; font-weight: bold; font-size: 1rem;'>{row['Drużyna']}</td><td>{row['M']}</td><td style='color: #00ff88; font-weight: bold;'>{row['W']}</td><td style='color: #ffcc00; font-weight: bold;'>{row['R']}</td><td style='color: #ff4b4b; font-weight: bold;'>{row['P']}</td><td style='color: #9da5b1; letter-spacing: 1px;'>{row['Bramki']}</td><td style='color: #00b8ff; font-weight: 900; font-size: 1.1rem;'>{row['Pkt']}</td></tr>"
                st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)

            with t_h2h:
                h2h = get_h2h_stats(h_team, a_team, last_n=8)
                if h2h and h2h.get('total_matches', 0) > 0:
                    table_html = "<table class='bet-table'><thead><tr><th style='text-align: left;'>Data</th><th style='text-align: right;'>Gospodarz</th><th>Wynik</th><th style='text-align: left;'>Gość</th><th title='Strzały Celne'>🎯 Celne</th><th title='Rzuty Rożne'>⛳ Rożne</th></tr></thead><tbody>"
                    for _, row in h2h['data'].iterrows():
                        wynik = f"{int(row['FTHG'])} – {int(row['FTAG'])}"
                        kolor = "#00ff88" if row['FTR'] == 'H' else ("#ff4b4b" if row['FTR'] == 'A' else "#ffcc00")
                        d_str = pd.to_datetime(row['Date'], dayfirst=True, errors='coerce').strftime('%d.%m.%Y')
                        table_html += f"<tr><td style='color: #9da5b1; text-align: left; font-size: 0.85rem;'>{d_str}</td><td style='text-align: right; font-weight: bold;'>{row['HomeTeam']}</td><td style='color:{kolor}; font-weight:900; font-size: 1.1rem; letter-spacing: 2px;'>{wynik}</td><td style='text-align: left; font-weight: bold;'>{row['AwayTeam']}</td><td style='color: #f72585; font-weight: bold;'>{int(row['HST']) if pd.notna(row['HST']) else '-'} - {int(row['AST']) if pd.notna(row['AST']) else '-'}</td><td style='color: #00d4ff; font-weight: bold;'>{int(row['HC']) if pd.notna(row['HC']) else '-'} - {int(row['AC']) if pd.notna(row['AC']) else '-'}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
                else: st.info("⚠️ Brak wspólnych spotkań.")

    with tab3:
        st.header("📋 AI Betting Predictions & Insights")
        st.markdown("<p style='color: #9da5b1;'>Ostateczne wnioski algorytmu na podstawie symulacji 20,000 scenariuszy oraz analizy DNA zespołów.</p>", unsafe_allow_html=True)
        if h_stats and a_stats:
            if win > loss and win > draw: main_pick, main_prob, main_col, main_icon = h_team, win, "#00ff88", "🏠"
            elif loss > win and loss > draw: main_pick, main_prob, main_col, main_icon = a_team, loss, "#ff4b4b", "✈️"
            else: main_pick, main_prob, main_col, main_icon = "REMIS", draw, "#ffcc00", "⚖️"

            st.markdown(f"""<div style="background: linear-gradient(135deg, #1e212b, #161922); padding: 30px; border-radius: 20px; border: 2px solid {main_col}; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);"><div style="font-size: 1rem; color: #9da5b1; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 10px;">Główny Werdykt AI</div><div style="font-size: 3.5rem; margin-bottom: 10px;">{main_icon}</div><div style="font-size: 2.5rem; font-weight: 900; color: white; line-height: 1.1;">{main_pick}</div><div style="font-size: 1.5rem; color: {main_col}; font-weight: bold; margin-top: 10px;">Prawdopodobieństwo: {main_prob*100:.1f}%</div></div>""", unsafe_allow_html=True)

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                safe_tips = []
                if o15 > 0.75: safe_tips.append(("Powyżej 1.5 gola", o15))
                if btts_yes > 0.65: safe_tips.append(("Obie strzelą (BTTS)", btts_yes))
                if ht_draw > 0.40: safe_tips.append(("Remis do przerwy", ht_draw))
                if o05_ht > 0.70: safe_tips.append(("Gol w 1. połowie", o05_ht))

                st.markdown("""<div style="background: rgba(0, 212, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(0, 212, 255, 0.2); height: 100%;"><h4 style="color: #00d4ff; margin-top: 0; margin-bottom: 20px; text-align: center;">🛡️ Bezpieczne Propozycje</h4>""", unsafe_allow_html=True)
                for tip, prob in safe_tips[:3]: st.markdown(f"""<div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; margin-bottom: 10px;"><span style="color: white; font-weight: bold;">{tip}</span><span style="color: #00ff88; font-weight: 900;">{prob*100:.1f}%</span></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with col_t2:
                st.markdown("""<div style="background: rgba(255, 204, 0, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(255, 204, 0, 0.2); height: 100%;"><h4 style="color: #ffcc00; margin-top: 0; margin-bottom: 20px; text-align: center;">💎 Typy Eksperckie (High Value)</h4>""", unsafe_allow_html=True)
                expert_tips = []
                if o25 > 0.55: expert_tips.append(("Powyżej 2.5 gola", o25))
                if o35 > 0.40: expert_tips.append(("Powyżej 3.5 gola", o35))
                if btts_ht > 0.25: expert_tips.append(("BTTS w 1. połowie", btts_ht))
                
                # ZABEZPIECZENIE: Sprawdzamy czy AI znalazło jakikolwiek prawdopodobny wynik
                if len(results) > 0:
                    expert_tips.append((f"Wynik: {results[0][0]}-{results[0][1]}", results[0][2]/100))

                for tip, prob in expert_tips[:3]: st.markdown(f"""<div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; margin-bottom: 10px;"><span style="color: white; font-weight: bold;">{tip}</span><span style="color: #ffcc00; font-weight: 900;">{prob*100:.1f}%</span></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            risk_level = "NISKIE" if main_prob > 0.65 else ("ŚREDNIE" if main_prob > 0.45 else "WYSOKIE")
            risk_color = "#00ff88" if risk_level == "NISKIE" else ("#ffcc00" if risk_level == "ŚREDNIE" else "#ff4b4b")
            st.markdown(f"""<div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border-top: 4px solid {risk_color}; text-align: center;"><span style="color: #9da5b1; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 2px;">Ogólna Ocena Ryzyka</span><div style="color: {risk_color}; font-size: 2rem; font-weight: 900; margin-top: 5px;">{risk_level}</div><p style="color: #9da5b1; font-size: 0.9rem; margin-top: 10px; max-width: 600px; margin-left: auto; margin-right: auto;">Werdykt oparty na aktualnej formie strzeleckiej oraz stabilności defensywnej. Pamiętaj, że w sporcie zawsze istnieje element losowości. Graj odpowiedzialnie!</p></div>""", unsafe_allow_html=True)

    with tab4:
        st.header("🟨 Card & Aggression Analyzer")
        h_stats_recent = get_advanced_stats(h_team, 'Home', 'Wszystkie', last_n=5)
        a_stats_recent = get_advanced_stats(a_team, 'Away', 'Wszystkie', last_n=5)
        
        if h_stats_recent and a_stats_recent:
            h_agg_score = (h_stats_recent['fouls'] * 2) + (h_stats_recent['yellows'] * 10) + (h_stats_recent['reds'] * 25)
            a_agg_score = (a_stats_recent['fouls'] * 2) + (a_stats_recent['yellows'] * 10) + (a_stats_recent['reds'] * 25)
            
            h_agg_pct = np.clip(h_agg_score / 0.8, 0, 100)
            a_agg_pct = np.clip(a_agg_score / 0.8, 0, 100)
            total_match_heat = (h_agg_pct + a_agg_pct) / 2

            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.markdown(f"""
                <div style="background: rgba(255, 204, 0, 0.05); border: 1px solid rgba(255, 204, 0, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #ffcc00; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Indeks Agresji: {h_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{h_agg_pct:.0f}%</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. fauli: {h_stats_recent['fouls']:.1f} | Kartki: {h_stats_recent['yellows']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_c2:
                st.markdown(f"""
                <div style="background: rgba(255, 204, 0, 0.05); border: 1px solid rgba(255, 204, 0, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #ffcc00; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Indeks Agresji: {a_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{a_agg_pct:.0f}%</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. fauli: {a_stats_recent['fouls']:.1f} | Kartki: {a_stats_recent['yellows']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            
            heat_color = "#00ff88" if total_match_heat < 40 else ("#ffcc00" if total_match_heat < 70 else "#ff4b4b")
            heat_desc = "CZYSTA GRA" if total_match_heat < 40 else ("OSTRA WALKA" if total_match_heat < 70 else "BRUTALNY MECZ")
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border-top: 4px solid {heat_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #9da5b1; font-weight: bold;">PRZEWIDYWANA TEMPERATURA MECZU:</span>
                    <span style="color: {heat_color}; font-weight: 900; font-size: 1.2rem;">{heat_desc}</span>
                </div>
                <div style="width: 100%; height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin-top: 10px; overflow: hidden;">
                    <div style="width: {total_match_heat}%; height: 100%; background: {heat_color}; box-shadow: 0 0 10px {heat_color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("")
            st.subheader("🎯 Typy na Kartki (AI Prediction)")
            
            c_tip1, c_tip2 = st.columns(2)
            with c_tip1:
                line = 3.5 if total_match_heat < 50 else 4.5
                prob_over = np.clip(total_match_heat * 1.1, 30, 95)
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; border-left: 4px solid #ffcc00;">
                    <span style="color: #9da5b1; font-size: 0.8rem;">GŁÓWNA LINIA</span><br>
                    <b style="color: white;">Powyżej {line} kartek</b><br>
                    <span style="color: #00ff88; font-weight: bold;">Prawdopodobieństwo: {prob_over:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

            with c_tip2:
                more_agg = h_team if h_agg_score > a_agg_score else a_team
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; border-left: 4px solid #ff4b4b;">
                    <span style="color: #9da5b1; font-size: 0.8rem;">DRUŻYNA Z WIĘKSZĄ LICZBĄ KARTREK</span><br>
                    <b style="color: white;">{more_agg}</b><br>
                    <span style="color: #ff4b4b; font-weight: bold;">DNA: {h_stats_recent['chaos'] if h_agg_score > a_agg_score else a_stats_recent['chaos']:.1f}/10 (Wysoki Chaos)</span>
                </div>
                """, unsafe_allow_html=True)
                
            h2h = get_h2h_stats(h_team, a_team, last_n=5)
            if h2h:
                st.write("")
                st.subheader("⚔️ Historia Kartek w H2H")
                h2h_table = "<table class='bet-table'><thead><tr><th>Data</th><th>Mecz</th><th>Żółte</th><th>Czerwone</th></tr></thead><tbody>"
                for _, row in h2h['data'].iterrows():
                    ty = int(row.get('HY', 0) + row.get('AY', 0))
                    tr = int(row.get('HR', 0) + row.get('AR', 0))
                    d_str = pd.to_datetime(row['Date'], dayfirst=True, errors='coerce').strftime('%d.%m.%Y')
                    h2h_table += f"<tr><td>{d_str}</td><td>{row['HomeTeam']} - {row['AwayTeam']}</td><td style='color:#ffcc00; font-weight:bold;'>{ty}</td><td style='color:#ff4b4b; font-weight:bold;'>{tr}</td></tr>"
                st.markdown(h2h_table + "</tbody></table>", unsafe_allow_html=True)

    with tab5:
        st.header("⛳ Corner Kick Analytics")
        st.markdown("<p style='color: #9da5b1;'>Analiza potencjału na rzuty rożne w oparciu o ostatnie 5 spotkań (aktualna forma).</p>", unsafe_allow_html=True)
        
        h_stats_recent = get_advanced_stats(h_team, 'Home', 'Wszystkie', last_n=5)
        a_stats_recent = get_advanced_stats(a_team, 'Away', 'Wszystkie', last_n=5)
        
        if h_stats_recent and a_stats_recent:
            h_corner_pot = (h_stats_recent['corners'] + a_stats_recent['opp_corners']) / 2
            a_corner_pot = (a_stats_recent['corners'] + h_stats_recent['opp_corners']) / 2
            total_expected_corners = h_corner_pot + a_corner_pot
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown(f"""
                <div style="background: rgba(0, 184, 255, 0.05); border: 1px solid rgba(0, 184, 255, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #00b8ff; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Potencjał Rożnych: {h_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{h_corner_pot:.1f}</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. nabijanych: {h_stats_recent['corners']:.1f} | Dopuszczanych: {h_stats_recent['opp_corners']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_r2:
                st.markdown(f"""
                <div style="background: rgba(0, 184, 255, 0.05); border: 1px solid rgba(0, 184, 255, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #00b8ff; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Potencjał Rożnych: {a_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{a_corner_pot:.1f}</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. nabijanych: {a_stats_recent['corners']:.1f} | Dopuszczanych: {a_stats_recent['opp_corners']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border-top: 4px solid #00b8ff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #9da5b1; font-weight: bold;">PRZEWIDYWANA SUMA ROŻNYCH:</span>
                    <span style="color: #00b8ff; font-weight: 900; font-size: 1.5rem;">ok. {total_expected_corners:.1f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("")
            st.subheader("🎯 Rekomendowane Linie (AI Corner Predictor)")
            
            c_tip1, c_tip2, c_tip3 = st.columns(3)
            line_low = np.floor(total_expected_corners - 1.5)
            line_mid = np.floor(total_expected_corners - 0.5)
            
            with c_tip1:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #00ff88;"><span style="color: #9da5b1; font-size: 0.7rem;">BEZPIECZNA</span><br><b style="color: white;">Powyżej {line_low:.1f}</b></div>""", unsafe_allow_html=True)
            with c_tip2:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #ffcc00;"><span style="color: #9da5b1; font-size: 0.7rem;">OPTYMALNA</span><br><b style="color: white;">Powyżej {line_mid:.1f}</b></div>""", unsafe_allow_html=True)
            with c_tip3:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #ff4b4b;"><span style="color: #9da5b1; font-size: 0.7rem;">RYZYKOWNA</span><br><b style="color: white;">Powyżej {line_mid + 1:.1f}</b></div>""", unsafe_allow_html=True)

            h2h = get_h2h_stats(h_team, a_team, last_n=5)
            if h2h:
                st.write("")
                st.subheader("⚔️ Historia Rzutów Rożnych w H2H")
                h2h_table = "<table class='bet-table'><thead><tr><th>Data</th><th>Mecz</th><th>Rożne (Suma)</th><th>Wynik Rożnych</th></tr></thead><tbody>"
                for _, row in h2h['data'].iterrows():
                    hc = int(row.get('HC', 0))
                    ac = int(row.get('AC', 0))
                    total_c = hc + ac
                    d_str = pd.to_datetime(row['Date'], dayfirst=True, errors='coerce').strftime('%d.%m.%Y')
                    h2h_table += f"<tr><td>{d_str}</td><td>{row['HomeTeam']} - {row['AwayTeam']}</td><td style='font-weight:bold;'>{total_c}</td><td style='color:#00b8ff;'>{hc} : {ac}</td></tr>"
                st.markdown(h2h_table + "</tbody></table>", unsafe_allow_html=True)

# =====================================================================
# --- EKRAN 2: ZŁOTE TYPY AI (Z SUWAKIEM DATY I OVER/UNDER) ---
# =====================================================================
elif menu_choice == "🔮 Złote Typy AI":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #ffcc00; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px;">🔮 Złote Typy AI</h2>
        <p style="color: #9da5b1; font-size: 0.9rem;">System skanuje terminarz i wyłapuje najlepsze okazje zarówno na <b>OVERY</b> (🔥) jak i <b>UNDERY</b> (🧊).</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='color: white; text-align: center; margin-top: 20px;'>📅 Wybierz dzień skanowania</h4>", unsafe_allow_html=True)
    days_map = {0: "Dzisiaj", 1: "Jutro", 2: "Pojutrze", 3: "Za 3 dni", 4: "Za 4 dni", 5: "Za 5 dni", 6: "Za 6 dni", 7: "Za 7 dni"}
    
    selected_day_offset = st.select_slider(
        "", 
        options=list(days_map.keys()), 
        format_func=lambda x: f"{days_map[x]} ({(pd.Timestamp.now() + pd.Timedelta(days=x)).strftime('%d.%m')})"
    )
    
    target_date = (pd.Timestamp.now() + pd.Timedelta(days=selected_day_offset)).strftime('%Y-%m-%d')
    st.write("")

    # ZMIANA 1: Guzik zapisuje w pamięci, że chcesz odpalić skaner dla tej daty
    if st.button(f"🚀 Uruchom Globalny Skaner AI na: {days_map[selected_day_offset]}", use_container_width=True):
        st.session_state['run_scanner'] = target_date

    # ZMIANA 2: Sprawdzamy, czy w pamięci skaner jest włączony (dzięki temu po kliknięciu "Graj" ekran nie zniknie!)
    if st.session_state.get('run_scanner') == target_date:
        if not user_api_key or user_api_key == "TWÓJ_NOWY_KLUCZ_TUTAJ":
            st.error("⚠️ Brak klucza API! System potrzebuje klucza The Odds API, aby pobrać dzisiejszy terminarz.")
        else:
            # ZMIANA 3: Robimy te długie obliczenia tylko jeśli NIE MA ich jeszcze w pamięci
            if 'skan_wyniki' not in st.session_state or st.session_state.get('skan_data') != target_date:
                with st.spinner(f'🌍 Globalny Skaner pracuje! Przeszukuję wszystkie ligi na {target_date}...'):
                    analyzed_matches = []
                    
                    for current_league in all_data.keys():
                        league_choice = current_league
                        df = all_data[current_league]
                        
                        current_season_df = df[df['Season'] == '2526']
                        if not current_season_df.empty:
                            teams = sorted(current_season_df['HomeTeam'].unique())
                        else:
                            teams = sorted(df['HomeTeam'].unique())
                            
                        api_matches = get_schedule_from_api(user_api_key, current_league)
                        if not api_matches: continue 
                            
                        for m in api_matches:
                            match_date_full = m.get('commence_time', '')
                            if not match_date_full.startswith(target_date): continue 
                                
                            h_api, a_api = m['home_team'], m['away_team']
                            
                            def dopasuj(api_nazwa, lista_csv):
                                def clean_name(txt):
                                    return txt.lower().replace("-", " ").replace(".", "").replace("é", "e").replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n").strip()
                                
                                n = clean_name(api_nazwa)
                                
                                if "saint germain" in n or "psg" in n:
                                    for t in lista_csv:
                                        t_c = clean_name(t)
                                        if "paris sg" in t_c or "psg" in t_c or "saint germain" in t_c: return t
                                
                                if "paris fc" in n:
                                    for t in lista_csv:
                                        if "paris fc" in clean_name(t): return t

                                slownik = {
                                    "manchester city": "Man City", "manchester united": "Man United",
                                    "wolverhampton": "Wolves", "nottingham": "Nott'm Forest",
                                    "sheffield": "Sheff Utd", "newcastle": "Newcastle",
                                    "west ham": "West Ham", "tottenham": "Tottenham",
                                    "aston villa": "Aston Villa", "crystal palace": "Crystal Palace",
                                    "alavés": "Alaves", "alaves": "Alaves",
                                    "athletic bilbao": "Ath Bilbao", "athletic club": "Ath Bilbao",
                                    "espanyol": "Espanol", "español": "Espanol",
                                    "atletico madrid": "Ath Madrid", "celta vigo": "Celta",
                                    "real betis": "Betis", "real sociedad": "Sociedad"
                                }
                                for klucz, wartosc in slownik.items():
                                    if klucz in n:
                                        for t in lista_csv:
                                            if t == wartosc: return t
                                
                                for t in lista_csv:
                                    t_l = clean_name(t)
                                    if t_l == n or t_l in n or n in t_l: return t
                                return None

                            h_csv = dopasuj(h_api, teams)
                            a_csv = dopasuj(a_api, teams)
                            
                            if not (h_csv and a_csv and h_csv != a_csv): continue
                                
                            h_stats = get_advanced_stats(h_csv, 'Home', "Wszystkie", 5)
                            a_stats = get_advanced_stats(a_csv, 'Away', "Wszystkie", 5)
                            
                            if not (h_stats and a_stats): continue

                            _, mot_h_val, _, _ = get_auto_motivation(h_csv)
                            _, mot_a_val, _, _ = get_auto_motivation(a_csv)
                            
                            h_adj = calc_power(h_stats, mot_h_val, 0)
                            a_adj = calc_power(a_stats, mot_a_val, 0)
                            
                            l_h = max(0.1, ((h_stats['gf'] + a_stats['ga']) / 2.0) * (h_adj / 100.0))
                            l_a = max(0.1, ((a_stats['gf'] + h_stats['ga']) / 2.0) * (a_adj / 100.0))

                            s_h = np.random.poisson(l_h, 20000)
                            s_a = np.random.poisson(l_a, 20000)
                            
                            r_w, r_d, r_l = np.mean(s_h > s_a), np.mean(s_h == s_a), np.mean(s_h < s_a)
                            
                            p00, p11 = np.mean((s_h==0)&(s_a==0)), np.mean((s_h==1)&(s_a==1))
                            dc_boost = 0.04 + (p00 * 0.2) + (p11 * 0.2)
                            if abs(h_adj - a_adj) < 10: dc_boost += 0.05
                            
                            chaos = (h_stats['chaos'] + a_stats['chaos']) / 20.0
                            adj_d = r_d + dc_boost - (chaos * 0.03)
                            
                            if r_w > r_l:
                                adj_w, adj_l = r_w - (dc_boost * 0.7), r_l - (dc_boost * 0.3)
                            else:
                                adj_l, adj_w = r_l - (dc_boost * 0.7), r_w - (dc_boost * 0.3)
                                
                            total = max(0.001, adj_w + adj_d + adj_l)
                            p_win_raw, p_draw_raw, p_loss_raw = adj_w/total, adj_d/total, adj_l/total
                            
                            max_prob = max(p_win_raw, p_draw_raw, p_loss_raw)
                            if max_prob == p_win_raw: best_pick = f"Wygra {h_csv} (1)"
                            elif max_prob == p_loss_raw: best_pick = f"Wygra {a_csv} (2)"
                            else: best_pick = "Remis (X)"
                            
                            real_exp_goals = (h_stats['gf'] + a_stats['ga'])/2 + (a_stats['gf'] + h_stats['ga'])/2
                            exp_cards = (h_stats['yellows'] + a_stats['yellows'])/2 + 1.2
                            exp_corners = (h_stats['corners'] + a_stats['opp_corners'])/2 + (a_stats['corners'] + h_stats['opp_corners'])/2
                            
                            date_str = match_date_full[:16].replace('T', ' ')
                            
                            analyzed_matches.append({
                                'match': f"{h_csv} - {a_csv}",
                                'league': current_league, 
                                'date': date_str,
                                'safe_prob': max_prob * 100,
                                'pick': best_pick,
                                'exp_goals_val': real_exp_goals,
                                'card_val': exp_cards,
                                'corner_val': exp_corners,
                                'api_data': m,     # <--- Zapisujemy surowe dane z API
                                'h_api': h_api,    # <--- Zapisujemy nazwy z API do szukania kursów
                                'a_api': a_api
                            })
                    
                    for m in analyzed_matches:
                        candidates = []
                        if m['safe_prob'] > 50.0: 
                            prob_1x2 = min(94.0, m['safe_prob'] * 1.15)
                            candidates.append(("1X2: " + m['pick'], prob_1x2, "🛡️ 1X2", "#00ff88"))
                        if m['exp_goals_val'] >= 2.9: 
                            prob_over = min(92.0, 50.0 + (m['exp_goals_val'] - 2.5) * 18)
                            candidates.append(("Powyżej 2.5 gola", prob_over, "⚽ GOLE", "#00d4ff"))
                        elif m['exp_goals_val'] <= 2.2: 
                            prob_under = min(92.0, 50.0 + (2.5 - m['exp_goals_val']) * 22)
                            candidates.append(("Poniżej 2.5 gola", prob_under, "🧊 GOLE (Under)", "#a020f0"))
                        if m['card_val'] >= 4.8: 
                            prob_cards_over = min(90.0, 50.0 + (m['card_val'] - 4.0) * 12)
                            candidates.append(("Powyżej 4.5 kartek", prob_cards_over, "🟨 KARTKI", "#ffcc00"))
                        elif m['card_val'] <= 3.2:
                            prob_cards_under = min(90.0, 50.0 + (4.0 - m['card_val']) * 15)
                            candidates.append(("Poniżej 3.5 kartek", prob_cards_under, "🟨 KARTKI (Under)", "#a020f0"))
                        if m['corner_val'] >= 10.8: 
                            prob_corn_over = min(90.0, 50.0 + (m['corner_val'] - 9.5) * 10)
                            candidates.append(("Powyżej 9.5 rożnych", prob_corn_over, "⛳ ROŻNE", "#f72585"))
                        elif m['corner_val'] <= 8.2:
                            prob_corn_under = min(90.0, 50.0 + (9.5 - m['corner_val']) * 12)
                            candidates.append(("Poniżej 9.5 rożnych", prob_corn_under, "⛳ ROŻNE (Under)", "#a020f0"))

                        if candidates:
                            best_signal = max(candidates, key=lambda x: x[1])
                            m['master_pick'] = best_signal[0]
                            m['master_prob'] = best_signal[1]
                            m['master_category'] = best_signal[2]
                            m['master_color'] = best_signal[3]
                            
                            # --- WYCIĄGANIE PRAWDZIWYCH KURSÓW Z THE ODDS API ---
                            m['master_odds'] = 1.85 # Domyślny kurs dla kartek/rożnych
                            try:
                                for b in m['api_data'].get('bookmakers', []):
                                    for market in b.get('markets', []):
                                        if market['key'] == 'h2h' and "1X2" in m['master_category']:
                                            for out in market['outcomes']:
                                                if (out['name'] == m['h_api'] and "(1)" in m['master_pick']) or \
                                                   (out['name'] == m['a_api'] and "(2)" in m['master_pick']) or \
                                                   (out['name'] == 'Draw' and "(X)" in m['master_pick']):
                                                    m['master_odds'] = out['price']
                                                    break
                                        elif market['key'] == 'totals' and "GOLE" in m['master_category']:
                                            for out in market['outcomes']:
                                                if out['name'] == 'Over' and "Powyżej" in m['master_pick']:
                                                    m['master_odds'] = out['price']
                                                    break
                                                elif out['name'] == 'Under' and "Poniżej" in m['master_pick']:
                                                    m['master_odds'] = out['price']
                                                    break
                            except:
                                pass
                        else:
                            m['master_prob'] = 0

                    top_matches = sorted([m for m in analyzed_matches if m['master_prob'] > 60], key=lambda x: x['master_prob'], reverse=True)
                    st.session_state['skan_wyniki'] = top_matches
                    st.session_state['skan_data'] = target_date

            # ---- WYŚWIETLAMY ZAPISANE WYNIKI Z PAMIĘCI ----
            top_matches = st.session_state.get('skan_wyniki', [])

            st.write("")
            st.markdown("<h3 style='text-align: center; color: #ffcc00; text-transform: uppercase;'>🏆 TOP 5 ZŁOTYCH TYPÓW DNIA 🏆</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #9da5b1; margin-bottom: 25px;'>System odrzucił słabe sygnały i wybrał absolutnie najlepszy rynek do obstawienia dla każdego meczu.</p>", unsafe_allow_html=True)
            
            if not top_matches:
                st.info("⚠️ Algorytm uznał, że dzisiejsze mecze są zbyt ryzykowne na żaden pewny typ. Wróć jutro!")
            else:
                for idx, m in enumerate(top_matches[:5]): 
                    # KARTA MECZU PRO
                    st.markdown(f"""
                    <div class="premium-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="league-tag">🌍 {m['league']} | {m['date'][11:]} | RANKING #{idx + 1}</div>
                                <div class="match-title">{m['match']}</div>
                                <div style="display: flex; gap: 10px;">
                                    <span style="background: rgba(0, 184, 255, 0.1); color: #00b8ff; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold;">
                                        KATEGORIA: {m['master_category']}
                                    </span>
                                </div>
                            </div>
                            <div class="pick-box" style="border-left-color: {m['master_color']}; min-width: 180px;">
                                <div style="color: {m['master_color']}; font-size: 1.6rem; font-weight: 900; text-transform: uppercase;">
                                    {m['master_pick']}
                                </div>
                                <div class="prob-text">
                                    PEWNOŚĆ AI: <b style="color: #00ff88;">{m['master_prob']:.1f}%</b> | 
                                    SUG. STAWKA: <b style="color: #ffcc00;">{calculate_kelly(m['master_prob'], m['master_odds'])}j</b>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # PANEL AKCJI (Kursy i Zapis) - Zaraz pod kartą
                    col_info, col_odds, col_btn = st.columns([1.5, 1, 1.5])
                    
                    odds_input_key = f"odds_input_{idx}_{m['match'].replace(' ', '')}"
                    
                    with col_info:
                        st.markdown("<p style='color: #9da5b1; font-size: 0.8rem; margin-top: 10px;'>Wpisz kurs i zatwierdź zakład, aby AI zaczęło go śledzić.</p>", unsafe_allow_html=True)
                    
                    with col_odds:
                        st.number_input("Kurs u buka:", min_value=1.01, value=1.85, step=0.05, format="%.2f", key=odds_input_key)
                        
                    with col_btn:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        st.button(
                            f"💾 Zagraj ten typ", 
                            key=f"roi_btn_{idx}_{m['match'].replace(' ', '')}", 
                            on_click=save_bet_to_tracker,
                            args=(m['date'], m['league'], m['match'], m['master_pick'], m['master_prob'], odds_input_key),
                            use_container_width=True
                        )
                    st.divider()

# =====================================================================
# --- EKRAN 3: DZIENNIK ZYSKÓW (TRACKER ROI) ---
# =====================================================================
elif menu_choice == "📈 Dziennik Zysków (ROI)":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #00ff88; font-weight: 900; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 5px;">📈 DZIENNIK INWESTORA (ROI)</h2>
        <p style="color: #9da5b1; font-size: 0.95rem; opacity: 0.8;">Śledź swoją drogę do profesjonalnego tradingu i analizuj przewagę nad bukmacherem.</p>
    </div>
    """, unsafe_allow_html=True)

    file_name = "roi_tracker.csv"
    
    if not os.path.exists(file_name) or os.path.getsize(file_name) == 0:
        st.info("📊 Twój Dziennik jest jeszcze pusty. Dodaj pierwszy zakład z poziomu 'Złote Typy AI'!")
    else:
        try:
            df_bets = pd.read_csv(file_name)
        except:
            st.error("⚠️ Błąd bazy danych.")
            st.stop()
        
        if not df_bets.empty:
            # --- OBLICZENIA STATYSTYK ---
            rozliczone = df_bets[df_bets['Status'].isin(['Wygrany', 'Przegrany'])]
            suma_stawek = len(rozliczone) * 100 
            zysk_strata = 0
            wygrane = 0
            
            for _, row in rozliczone.iterrows():
                if row['Status'] == 'Wygrany':
                    wygrane += 1
                    zysk_strata += (100 * row['Kurs']) - 100
                elif row['Status'] == 'Przegrany':
                    zysk_strata -= 100
                    
            yield_pct = (zysk_strata / suma_stawek * 100) if suma_stawek > 0 else 0
            win_rate = (wygrane / len(rozliczone) * 100) if len(rozliczone) > 0 else 0
            
            # --- NOWOCZESNE KAFELKI KPI (PREMIUM) ---
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;">
                <div class="premium-card" style="text-align: center; padding: 15px;">
                    <div style="color: #9da5b1; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;">Zagrane Typy</div>
                    <div style="color: #00b8ff; font-size: 1.8rem; font-weight: 900;">{len(df_bets)}</div>
                </div>
                <div class="premium-card" style="text-align: center; padding: 15px; border-bottom: 2px solid #ffcc00;">
                    <div style="color: #9da5b1; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;">Skuteczność</div>
                    <div style="color: #ffcc00; font-size: 1.8rem; font-weight: 900;">{win_rate:.1f}%</div>
                </div>
                <div class="premium-card" style="text-align: center; padding: 15px; border-bottom: 2px solid #00ff88;">
                    <div style="color: #9da5b1; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;">Zysk Netto</div>
                    <div style="color: #00ff88; font-size: 1.8rem; font-weight: 900;">{zysk_strata:.1f}j</div>
                </div>
                <div class="premium-card" style="text-align: center; padding: 15px; border-bottom: 2px solid {'#00ff88' if yield_pct >= 0 else '#ff4b4b'};">
                    <div style="color: #9da5b1; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;">Yield (ROI)</div>
                    <div style="color: {'#00ff88' if yield_pct >= 0 else '#ff4b4b'}; font-size: 1.8rem; font-weight: 900;">{yield_pct:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- WYKRES TRENDU ---
            if not rozliczone.empty:
                rozliczone = rozliczone.copy()
                rozliczone['Data_DT'] = pd.to_datetime(rozliczone['Data'])
                rozliczone = rozliczone.sort_values('Data_DT')
                rozliczone['Skumulowany_Zysk'] = rozliczone['Zysk_Strata'].cumsum()
                
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(x=list(range(len(rozliczone) + 1)), y=[0] + rozliczone['Skumulowany_Zysk'].tolist(), mode='lines+markers', line=dict(color='#00ff88', width=3), fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.05)', name='Kapitał'))
                fig_equity.update_layout(title="📈 TREND KAPITAŁU (JEDNOSTKI)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), margin=dict(l=0, r=0, t=40, b=0), height=250, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'))
                st.plotly_chart(fig_equity, use_container_width=True)

            # --- PRZYCISKI AKCJI (ŁADNIEJSZE) ---
            c_auto, c_exp = st.columns([1, 1])
            with c_auto:
                if st.button("🔄 Uruchom Auto-Weryfikację AI", use_container_width=True, type="secondary"):
                    with st.spinner("Przeszukuję bazę wyników..."):
                        ile = auto_settle_bets()
                        if ile > 0:
                            st.success(f"✅ Rozliczono automatycznie {ile} kuponów!")
                            st.rerun()
                        else: st.info("ℹ️ Brak nowych wyników w systemie.")
            with c_exp:
                csv = df_bets.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Pobierz kopię Dziennika (CSV)", data=csv, file_name=f"moje_roi.csv", mime='text/csv', use_container_width=True)

            # --- EDYTOR ZAKŁADÓW ---
            st.write("")
            st.markdown("<div class='premium-card' style='padding: 20px;'> <h3 style='margin-top: 0; color: white;'>📝 Edytor Zakładów na Żywo</h3>", unsafe_allow_html=True)
            edited_df = st.data_editor(
                df_bets,
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Oczekujący", "Wygrany", "Przegrany", "Zwrot"], required=True),
                    "Kurs": st.column_config.NumberColumn("Kurs", min_value=1.01, format="%.2f"),
                    "Pewnosc_AI": st.column_config.NumberColumn("AI %", disabled=True, format="%.1f%%"),
                    "Data": st.column_config.TextColumn("Data", disabled=True),
                    "Mecz": st.column_config.TextColumn("Mecz", disabled=True),
                    "Typ": st.column_config.TextColumn("Typ Typ", disabled=True),
                },
                hide_index=True, use_container_width=True
            )

            if st.button("💾 Zapisz zmiany ręczne", type="primary", use_container_width=True):
                for i, row in edited_df.iterrows():
                    if row['Status'] == 'Wygrany': edited_df.at[i, 'Zysk_Strata'] = (100 * row['Kurs']) - 100
                    elif row['Status'] == 'Przegrany': edited_df.at[i, 'Zysk_Strata'] = -100
                    else: edited_df.at[i, 'Zysk_Strata'] = 0
                edited_df.to_csv(file_name, index=False)
                st.success("✅ Zapisano!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)