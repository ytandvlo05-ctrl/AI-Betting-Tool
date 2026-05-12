import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os
import requests
from bs4 import BeautifulSoup
import random
import streamlit_authenticator as stauth
from auth_config import config  # Importujemy Twoje ustawienia

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
    /* Lista rozwijana z ligami */
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: linear-gradient(135deg, #161922 0%, #1a1d26 100%) !important;
        border: 1px solid rgba(0, 184, 255, 0.3) !important;
        border-radius: 10px !important;
        color: white !important;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.5) !important;
        transition: all 0.3s ease-in-out !important;
        cursor: pointer !important;
    }
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
        border: 1px solid #00b8ff !important;
        box-shadow: 0 0 15px rgba(0, 184, 255, 0.5), inset 0 2px 5px rgba(0,0,0,0.5) !important;
    }
    
    /* MAGIA: Zmiana standardowego Radio na Przyciski Menu PRO */
    div.stRadio > div[role="radiogroup"] > label {
        background: linear-gradient(135deg, #1e212b 0%, #161922 100%);
        padding: 12px 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div.stRadio > div[role="radiogroup"] > label:hover {
        border: 1px solid #00b8ff;
        background: rgba(0, 184, 255, 0.05);
        transform: translateY(-2px);
    }
    /* Aktywny przycisk menu */
    div.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        border: 1px solid #00ff88;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.2);
        background: rgba(0, 255, 136, 0.05);
    }
    /* Ukrycie standardowej kropki z formularza */
    div.stRadio > div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    /* Pogrubienie i kolor tekstu menu */
    div.stRadio > div[role="radiogroup"] > label p {
        font-weight: 900 !important;
        font-size: 1.1rem !important;
        letter-spacing: 1px;
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
    params = {"apiKey": api_key, "regions": "eu", "markets": "h2h"}
    
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
    params = {"apiKey": api_key, "regions": "eu", "markets": "h2h"}
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            dane = res.json()
            if len(dane) > 0:
                daty = sorted(list(set(m['commence_time'][:10] for m in dane)))
                daty_str = " | ".join(daty)
                # st.info(f"🛠️ System API żyje! Znalazł łącznie {len(dane)} meczów. Zaplanowane dni gry to: {daty_str}")
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
with st.sidebar:
    # 1. Przycisk wylogowania (zgodny z nową wersją biblioteki)
    authenticator.logout(button_name='Wyloguj się', location='sidebar')
    
    # 2. Powitanie zalogowanego użytkownika
    st.markdown(f"""
        <div style="text-align: center; margin-top: -15px; margin-bottom: 20px;">
            <p style="color: #9da5b1; font-size: 0.9rem; margin: 0;">Zalogowany jako:</p>
            <b style="color: #00ff88; font-size: 1.1rem;">{st.session_state['name']}</b>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # 3. Twój stylowy nagłówek AI BET PRO
    st.markdown("""
<div style="background: linear-gradient(135deg, #00ff88 0%, #00b8ff 100%); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0, 255, 136, 0.2);">
<h1 style="color: #111; margin: 0; font-size: 1.8rem; font-weight: 900; letter-spacing: 1px;">AI BET PRO</h1>
<p style="color: #111; font-weight: bold; margin: 5px 0 0 0; font-size: 0.85rem; opacity: 0.8;">SPORTS PREDICTION ENGINE</p>
</div>
""", unsafe_allow_html=True)

    menu_choice = st.radio(
        "Nawigacja Główna", 
        ["🎯 Centrum Analizy", "🔮 Złote Typy AI"],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.1); margin: 15px 0;'>", unsafe_allow_html=True)
    
    if menu_choice in ["🎯 Centrum Analizy", "🔮 Złote Typy AI"]:
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
    user_api_key = "6018066337170b1992549ba219aee5df"

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

    # --- NOWY SUWAK DATY ---
    st.markdown("<h4 style='color: white; text-align: center; margin-top: 20px;'>📅 Wybierz dzień skanowania</h4>", unsafe_allow_html=True)
    days_map = {0: "Dzisiaj", 1: "Jutro", 2: "Pojutrze", 3: "Za 3 dni", 4: "Za 4 dni", 5: "Za 5 dni", 6: "Za 6 dni", 7: "Za 7 dni"}
    
    # Generowanie ładnych etykiet z datami na żywo
    selected_day_offset = st.select_slider(
        "", 
        options=list(days_map.keys()), 
        format_func=lambda x: f"{days_map[x]} ({(pd.Timestamp.now() + pd.Timedelta(days=x)).strftime('%d.%m')})"
    )
    
    # Obliczamy dokładną datę docelową w formacie YYYY-MM-DD
    target_date = (pd.Timestamp.now() + pd.Timedelta(days=selected_day_offset)).strftime('%Y-%m-%d')
    st.write("")

    if st.button(f"🚀 Skanuj mecze na: {days_map[selected_day_offset]}", use_container_width=True):
        if not user_api_key or user_api_key == "TWÓJ_KLUCZ_API_TUTAJ":
            st.error("⚠️ Brak klucza API! System potrzebuje klucza The Odds API, aby pobrać dzisiejszy terminarz.")
        else:
            with st.spinner(f'Pobieram terminarz na {target_date} i wyliczam precyzyjne linie Over/Under...'):
                api_matches = get_schedule_from_api(user_api_key, league_choice)
                
                if not api_matches:
                    st.warning("Brak nadchodzących meczów dla tej ligi w najbliższym czasie.")
                else:
                    analyzed_matches = []
                    for m in api_matches:
                        # --- FILTROWANIE PO DACIE ---
                        match_date_full = m.get('commence_time', '')
                        if not match_date_full.startswith(target_date):
                            continue # Jeśli mecz nie jest z wybranego dnia, pomijamy go!
                            
                        h_api, a_api = m['home_team'], m['away_team']
                        
                        # --- LEPSZE DOPASOWANIE NAZW (SMART MATCH) ---
                        def dopasuj(api_nazwa, lista_csv):
                            # Funkcja pomocnicza do czyszczenia nazw z myślników i kropek
                            def clean_name(txt):
                                return txt.lower().replace("-", " ").replace(".", "").strip()
                            
                            n = clean_name(api_nazwa)
                            
                            # --- 1. SPECJALNY RADAR DLA PSG ---
                            # Szukamy "saint germain" (bez myślnika) lub "psg"
                            if "saint germain" in n or "psg" in n:
                                for t in lista_csv:
                                    t_c = clean_name(t)
                                    if "paris sg" in t_c or "psg" in t_c or "saint germain" in t_c:
                                        return t
                            
                            # --- 2. SPECJALNY RADAR DLA PARIS FC ---
                            if "paris fc" in n:
                                for t in lista_csv:
                                    if "paris fc" in clean_name(t): return t

                            # --- 3. SŁOWNIK ANGIELSKI ---
                            slownik = {
                                "manchester city": "Man City", "manchester united": "Man United",
                                "wolverhampton": "Wolves", "nottingham": "Nott'm Forest",
                                "sheffield": "Sheff Utd", "newcastle": "Newcastle",
                                "west ham": "West Ham", "tottenham": "Tottenham",
                                "aston villa": "Aston Villa", "crystal palace": "Crystal Palace"
                            }
                            for klucz, wartosc in slownik.items():
                                if klucz in n:
                                    for t in lista_csv:
                                        if t == wartosc: return t
                            
                            # --- 4. KLASYCZNE SZUKANIE ---
                            for t in lista_csv:
                                t_l = clean_name(t)
                                if t_l == n or t_l in n or n in t_l: return t
                            return None

                        h_csv = dopasuj(h_api, teams)
                        a_csv = dopasuj(a_api, teams)
                        
                        if not (h_csv and a_csv and h_csv != a_csv):
                            st.warning(f"⚠️ Odrzucono: **{h_api} vs {a_api}** (Brak zgodności nazw API z plikiem CSV)")
                            continue
                            
                        # Symulujemy konkretny mecz
                        h_stats = get_advanced_stats(h_csv, 'Home', "Wszystkie", 5)
                        a_stats = get_advanced_stats(a_csv, 'Away', "Wszystkie", 5)
                        
                        if not (h_stats and a_stats):
                            st.warning(f"⚠️ Odrzucono: **{h_csv} vs {a_csv}** (Za mało statystyk w bazie CSV)")
                            continue

                        if h_stats and a_stats:
                                # 1. 1X2 Szanse - IDENTYCZNA LOGIKA JAK W CENTRUM ANALIZY
                                _, mot_h_val, _, _ = get_auto_motivation(h_csv)
                                _, mot_a_val, _, _ = get_auto_motivation(a_csv)
                                
                                # Wyliczamy siłę (Power Index) z uwzględnieniem motywacji
                                h_adj = calc_power(h_stats, mot_h_val, 0) # 0 osłabień domyślnie
                                a_adj = calc_power(a_stats, mot_a_val, 0)
                                
                                l_h = max(0.1, ((h_stats['gf'] + a_stats['ga']) / 2.0) * (h_adj / 100.0))
                                l_a = max(0.1, ((a_stats['gf'] + h_stats['ga']) / 2.0) * (a_adj / 100.0))

                                # Symulacja Monte Carlo
                                s_h = np.random.poisson(l_h, 20000)
                                s_a = np.random.poisson(l_a, 20000)
                                
                                r_w, r_d, r_l = np.mean(s_h > s_a), np.mean(s_h == s_a), np.mean(s_h < s_a)
                                
                                # Dixon-Coles (Korekta na remisy)
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
                                
                                # 2. Czyste Oczekiwane Wartości
                                real_exp_goals = (h_stats['gf'] + a_stats['ga'])/2 + (a_stats['gf'] + h_stats['ga'])/2
                                exp_cards = (h_stats['yellows'] + a_stats['yellows'])/2 + 1.2
                                exp_corners = (h_stats['corners'] + a_stats['opp_corners'])/2 + (a_stats['corners'] + h_stats['opp_corners'])/2
                                
                                date_str = match_date_full[:16].replace('T', ' ')
                                
                                analyzed_matches.append({
                                    'match': f"{h_csv} - {a_csv}",
                                    'date': date_str,
                                    'p1': p_win_raw * 100,
                                    'px': p_draw_raw * 100,
                                    'p2': p_loss_raw * 100,
                                    'safe_prob': max_prob * 100,
                                    'pick': best_pick,
                                    'exp_goals_val': real_exp_goals,
                                    'card_val': exp_cards,
                                    'corner_val': exp_corners
                                })
                    
                    if not analyzed_matches:
                        st.warning(f"Brak dopasowanych meczów na dzień: {target_date}. Spróbuj przesunąć suwak.")
                    else:
                        # Teraz pokaże wszystko, co ma chociaż 40% szans (czyli PSG i Strasbourg wrócą)
                        safe_m = sorted([m for m in analyzed_matches if m['safe_prob'] >= 40.0], key=lambda x: x['safe_prob'], reverse=True)[:5]
                        
                        # Gole (Granica: 2.6 gola)
                        over_goals = sorted([m for m in analyzed_matches if m['exp_goals_val'] >= 2.6], key=lambda x: x['exp_goals_val'], reverse=True)[:3]
                        under_goals = sorted([m for m in analyzed_matches if m['exp_goals_val'] < 2.6], key=lambda x: x['exp_goals_val'])[:3]
                        
                        # Kartki (Granica: 4.0 kartek)
                        over_cards = sorted([m for m in analyzed_matches if m['card_val'] >= 4.0], key=lambda x: x['card_val'], reverse=True)[:3]
                        under_cards = sorted([m for m in analyzed_matches if m['card_val'] < 4.0], key=lambda x: x['card_val'])[:3]
                        
                        # Rożne (Granica: 10.0 rożnych)
                        over_corners = sorted([m for m in analyzed_matches if m['corner_val'] >= 10.0], key=lambda x: x['corner_val'], reverse=True)[:3]
                        under_corners = sorted([m for m in analyzed_matches if m['corner_val'] < 10.0], key=lambda x: x['corner_val'])[:3]
                        
                        st.write("")
                        t_safe, t_goals, t_cards, t_corners = st.tabs(["🛡️ Pewniaki (1X2)", "⚽ Gole (O/U)", "🟨 Kartki (O/U)", "⛳ Rożne (O/U)"])
                        
                        def make_match_card(match_name, date, value_html, desc_top, desc_bottom, border_color):
                            return f"""<div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid {border_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div style="display: flex; flex-direction: column;"><span style="color: #9da5b1; font-size: 0.7rem; text-transform: uppercase;">MECZ: {date} | <b style="color:white;">{desc_top}</b></span><span style="font-size: 1.1rem; font-weight: bold; color: white; margin-top: 5px;">{match_name}</span></div><div style="text-align: right;"><div style="font-size: 1.3rem; font-weight: 900;">{value_html}</div><div style="font-size: 0.75rem; color: #9da5b1; margin-top: 3px;">{desc_bottom}</div></div></div>"""

                        with t_safe:
                            st.markdown("<h4 style='color: #00ff88;'>🛡️ Najwyższe Szanse na Wynik 1X2</h4>", unsafe_allow_html=True)
                            for m in safe_m: 
                                # Tworzymy ładny pasek z rozkładem procentów
                                rozklad_html = f"""
                                <span style='color:#00ff88;'>1: {m['p1']:.0f}%</span> | 
                                <span style='color:#ffcc00;'>X: {m['px']:.0f}%</span> | 
                                <span style='color:#ff4b4b;'>2: {m['p2']:.0f}%</span>
                                """
                                st.markdown(make_match_card(
                                    m['match'], 
                                    m['date'], 
                                    f"<span style='color:#00ff88;'>{m['safe_prob']:.1f}%</span>", 
                                    f"TYP: {m['pick']}", 
                                    rozklad_html, # Tutaj wstawiamy nasz rozkład
                                    "#00ff88"
                                ), unsafe_allow_html=True)
                        
                        with t_goals:
                            col_g1, col_g2 = st.columns(2)
                            with col_g1:
                                st.markdown("<h4 style='color: #00d4ff;'>🔥 TOP OVERY (Dużo Goli)</h4>", unsafe_allow_html=True)
                                for m in over_goals:
                                    line = max(1.5, np.floor(m['exp_goals_val'] - 0.5) + 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#00d4ff;'>Powyżej {line}</span>", "BRAMKI W MECZU", f"Oczekiwane Gole: {m['exp_goals_val']:.2f}", "#00d4ff"), unsafe_allow_html=True)
                            with col_g2:
                                st.markdown("<h4 style='color: #a020f0;'>🧊 TOP UNDERY (Mało Goli)</h4>", unsafe_allow_html=True)
                                for m in under_goals:
                                    line = min(3.5, np.ceil(m['exp_goals_val'] + 0.5) - 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#a020f0;'>Poniżej {line}</span>", "BRAMKI W MECZU", f"Oczekiwane Gole: {m['exp_goals_val']:.2f}", "#a020f0"), unsafe_allow_html=True)

                        with t_cards:
                            col_c1, col_c2 = st.columns(2)
                            with col_c1:
                                st.markdown("<h4 style='color: #ffcc00;'>🔥 OVERY (Rzeźnicy)</h4>", unsafe_allow_html=True)
                                for m in over_cards:
                                    line = max(3.5, np.floor(m['card_val'] - 0.5) + 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#ffcc00;'>Powyżej {line}</span>", "TYP NA KARTKI", f"Oczekiwane Kartki: {m['card_val']:.1f}", "#ffcc00"), unsafe_allow_html=True)
                            with col_c2:
                                st.markdown("<h4 style='color: #a020f0;'>🧊 UNDERY (Czysta Gra)</h4>", unsafe_allow_html=True)
                                for m in under_cards:
                                    line = max(2.5, np.ceil(m['card_val']) - 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#a020f0;'>Poniżej {line}</span>", "TYP NA KARTKI", f"Oczekiwane Kartki: {m['card_val']:.1f}", "#a020f0"), unsafe_allow_html=True)

                        with t_corners:
                            col_cor1, col_cor2 = st.columns(2)
                            with col_cor1:
                                st.markdown("<h4 style='color: #f72585;'>🔥 OVERY (Atak Skrzydłami)</h4>", unsafe_allow_html=True)
                                for m in over_corners:
                                    line = max(8.5, np.floor(m['corner_val'] - 0.5) + 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#f72585;'>Powyżej {line}</span>", "TYP NA ROŻNE", f"Oczekiwane Rożne: {m['corner_val']:.1f}", "#f72585"), unsafe_allow_html=True)
                            with col_cor2:
                                st.markdown("<h4 style='color: #a020f0;'>🧊 UNDERY (Gra Środkiem)</h4>", unsafe_allow_html=True)
                                for m in under_corners:
                                    line = max(7.5, np.ceil(m['corner_val']) - 0.5)
                                    st.markdown(make_match_card(m['match'], m['date'], f"<span style='color:#a020f0;'>Poniżej {line}</span>", "TYP NA ROŻNE", f"Oczekiwane Rożne: {m['corner_val']:.1f}", "#a020f0"), unsafe_allow_html=True)