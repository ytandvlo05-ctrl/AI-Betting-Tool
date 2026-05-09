import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os  # do obsługi plików z historią

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="AI Ultra Betting Center", page_icon="⚽", layout="wide")

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

# =====================================================================
# --- NAWIGACJA GŁÓWNA (SIDEBAR) ---
# =====================================================================
with st.sidebar:
    st.markdown("""
<div style="background: linear-gradient(135deg, #00ff88 0%, #00b8ff 100%); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0, 255, 136, 0.2);">
<h1 style="color: #111; margin: 0; font-size: 1.8rem; font-weight: 900; letter-spacing: 1px;">AI BET PRO</h1>
<p style="color: #111; font-weight: bold; margin: 5px 0 0 0; font-size: 0.85rem; opacity: 0.8;">SPORTS PREDICTION ENGINE</p>
</div>
""", unsafe_allow_html=True)

    # Główne Menu jako Radio Buttons (Ostylowane na potężne przyciski)
    menu_choice = st.radio(
        "Nawigacja Główna", 
        ["🎯 Centrum Analizy", "🤖 Skaner Ligi", "🏦 Bet Tracker"],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.1); margin: 25px 0;'>", unsafe_allow_html=True)
    
    # Wybór ligi pojawia się tylko, gdy jesteśmy w analizie lub skanerze
    if menu_choice in ["🎯 Centrum Analizy", "🤖 Skaner Ligi"]:
        st.markdown("<p style='color: #00b8ff; font-weight: bold; font-size: 0.85rem; text-transform: uppercase;'>🌍 Baza Rozgrywek</p>", unsafe_allow_html=True)
        league_choice = st.selectbox("Wybierz Ligę", list(all_data.keys()), label_visibility="collapsed")
        df = all_data[league_choice]
        
        current_season_df = df[df['Season'] == '2526']
        if not current_season_df.empty:
            teams = sorted(current_season_df['HomeTeam'].unique())
        else:
            teams = sorted(df['HomeTeam'].unique())
            
        st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.1); margin: 25px 0;'>", unsafe_allow_html=True)

    # Status Serwera zawsze na dole
    st.markdown("""
<div style="background: rgba(255,255,255,0.02); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05); position: relative;">
<div style="display: flex; align-items: center; margin-bottom: 10px;">
<div style="width: 10px; height: 10px; border-radius: 50%; background: #00ff88; margin-right: 10px; box-shadow: 0 0 8px #00ff88; animation: pulse 2s infinite;"></div>
<span style="color: white; font-size: 0.85rem; font-weight: bold;">System Online</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9da5b1; margin-bottom: 5px;">
<span>Baza Danych:</span>
<span style="color: #00ff88;">Zsynchronizowana</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9da5b1; margin-bottom: 5px;">
<span>Algorytm POISSON:</span>
<span style="color: #00d4ff;">Aktywny</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9da5b1;">
<span>Wersja Silnika:</span>
<span style="color: #ffcc00;">v4.2.0 PRO</span>
</div>
<style>
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); } }
</style>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# --- FUNKCJE POMOCNICZE (Wspólne dla Skanera i Centrum Analizy) ---
# =====================================================================
if menu_choice in ["🎯 Centrum Analizy", "🤖 Skaner Ligi"]:
    def get_advanced_stats(team, side, mode, last_n=None):
        current_df = df[df['Season'] == '2526']
        if mode == "Wszystkie":
            t_data_h = current_df[current_df['HomeTeam'] == team].copy()
            t_data_a = current_df[current_df['AwayTeam'] == team].copy()
            t_data = pd.concat([t_data_h, t_data_a])
        else:
            t_data = current_df[current_df['HomeTeam'] == team].copy() if side == 'Home' else current_df[current_df['AwayTeam'] == team].copy()

        if last_n and len(t_data) > 0:
            if 'Date' in t_data.columns:
                t_data['Date'] = pd.to_datetime(t_data['Date'], dayfirst=True, errors='coerce')
                t_data = t_data.sort_values('Date', ascending=False)
            t_data = t_data.head(last_n)

        m = len(t_data)
        if m == 0: return None
        
        gf = t_data.apply(lambda row: row['FTHG'] if row['HomeTeam'] == team else row['FTAG'], axis=1).mean()
        ga = t_data.apply(lambda row: row['FTAG'] if row['HomeTeam'] == team else row['FTHG'], axis=1).mean()
        ht_gf = t_data.apply(lambda row: row.get('HTHG', 0) if row['HomeTeam'] == team else row.get('HTAG', 0), axis=1).mean()
        shots = t_data.apply(lambda row: row['HS'] if row['HomeTeam'] == team else row['AS'], axis=1).mean()
        shots_ot = t_data.apply(lambda row: row['HST'] if row['HomeTeam'] == team else row['AST'], axis=1).mean()
        opp_shots_ot = t_data.apply(lambda row: row['AST'] if row['HomeTeam'] == team else row['HST'], axis=1).mean()
        corners = t_data.apply(lambda row: row['HC'] if row['HomeTeam'] == team else row['AC'], axis=1).mean()
        opp_corners = t_data.apply(lambda row: row['AC'] if row['HomeTeam'] == team else row['HC'], axis=1).mean()
        fouls = t_data.apply(lambda row: row['HF'] if row['HomeTeam'] == team else row['AF'], axis=1).mean()
        yellows = t_data.apply(lambda row: row['HY'] if row['HomeTeam'] == team else row['AY'], axis=1).mean()
        reds = t_data.apply(lambda row: row.get('HR', 0) if row['HomeTeam'] == team else row.get('AR', 0), axis=1).mean()

        values = [gf, ga, ht_gf, shots, shots_ot, opp_shots_ot, corners, opp_corners, fouls, yellows, reds]
        values = [0 if pd.isna(v) else float(v) for v in values]
        gf, ga, ht_gf, shots, shots_ot, opp_shots_ot, corners, opp_corners, fouls, yellows, reds = values

        raw_dom = (shots * 0.5) + (shots_ot * 1.0) + (corners * 0.5)
        dom = np.clip(raw_dom / 2.0, 1.0, 10.0)

        raw_killer = (gf / shots_ot) * 100 if shots_ot > 0 else 0.0
        killer = np.clip(raw_killer, 0.0, 100.0)

        punkty_karne_obrony = (ga * 2.5) + (opp_shots_ot * 0.5) + (opp_corners * 0.2)
        safety = np.clip(12.0 - punkty_karne_obrony, 1.0, 10.0)

        raw_chaos = (fouls * 0.3) + (yellows * 1.5) + (reds * 5.0)
        chaos = np.clip(raw_chaos / 1.2, 1.0, 10.0)

        return {'gf': gf, 'ga': ga, 'ht_gf': ht_gf, 'shots': shots, 'shots_ot': shots_ot, 'opp_shots_ot': opp_shots_ot, 'corners': corners, 'opp_corners': opp_corners, 'fouls': fouls, 'yellows': yellows, 'reds': reds, 'killer': killer, 'dom': dom, 'safety': safety, 'chaos': chaos, 'matches': m}

    def get_team_form_trend(team, side, mode, last_n=5):
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
        if total_pts <= 3: trend_text, trend_color = "🚨 Tragiczna forma (Kryzys)", "#ff4b4b"
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

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 30px 0;'>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 ANALIZA PRO", "📊 STATYSTYKI AI", "📋 PREDYKCJE", "🟨 KARTKI", "⛳ ROŻNE"])

    with tab1:
        st.header("🧠 AI Scenario Simulator & Analysis")
        h_stats = get_advanced_stats(h_team, 'Home', 'Wszystkie')
        a_stats = get_advanced_stats(a_team, 'Away', 'Wszystkie')
        
        if h_stats and a_stats:
            st.markdown("### 🏟️ Kontekst Meczu i Motywacja")
            st.markdown("<p style='color: #9da5b1; font-size: 0.85rem;'>AI skanuje aktualną tabelę ligową i etap sezonu, aby samodzielnie określić o co grają drużyny.</p>", unsafe_allow_html=True)
            
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

                pts_1st, pts_cl, pts_eur, pts_safe = get_pts_at(1), get_pts_at(rules["cl"]), get_pts_at(rules["eur"]), get_pts_at(rules["rel"] - 1)
                max_pts_left = (rules["max_m"] - matches_played) * 3

                if matches_played >= rules["max_m"] - 10:
                    if team_pts + max_pts_left < pts_safe: return "Niska", 0.8, "Pewny spadek (Brak motywacji)", "#9da5b1"
                    if team_pts >= pts_1st - 6 and rank <= 3: return "Mecz o życie!", 1.3, "Walka o Mistrzostwo!", "#00ff88"
                    elif team_pts >= pts_cl - 5 and rank <= rules["cl"] + 2: return "Wysoka", 1.2, "Walka o Ligę Mistrzów", "#00d4ff"
                    elif team_pts >= pts_eur - 5 and rank <= rules["eur"] + 2: return "Wysoka", 1.15, "Pościg za pucharami", "#00ff88"
                    elif team_pts <= pts_safe + 5: return "Mecz o życie!", 1.3, "Desperacja (Utrzymanie)", "#ff4b4b"
                    else: return "Niska", 0.85, "Środek tabeli (Brak presji)", "#9da5b1"
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

            def calc_power(stats, mot_val):
                killer_score = stats['killer'] / 10.0
                team_rating = (stats['dom'] * 0.3) + (killer_score * 0.35) + (stats['safety'] * 0.35)
                return round(np.clip((team_rating / 5.5) * 100 * mot_val, 50, 150), 1)

            auto_h_power, auto_a_power = calc_power(h_stats, mot_h_val), calc_power(a_stats, mot_a_val)
            h_adj, a_adj = auto_h_power, auto_a_power

            st.markdown("### ⚡ Obliczona Siła Zespołów (AI Power Index)")
            st.markdown("<p style='color: #9da5b1; font-size: 0.85rem;'>System przemnożył statystyki meczowe przez wykrytą motywację. Zero zgadywania.</p>", unsafe_allow_html=True)
            
            c_pow1, c_pow2 = st.columns(2)
            with c_pow1:
                st.markdown(f"""<div style="background: rgba(0, 255, 136, 0.05); border: 1px dashed #00ff88; border-radius: 12px; padding: 15px; text-align: center;"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Algorytm wyliczył moc: <b>{h_team}</b></div><div style="color: #00ff88; font-size: 2.2rem; font-weight: 900;">{auto_h_power}%</div></div>""", unsafe_allow_html=True)
            with c_pow2:
                st.markdown(f"""<div style="background: rgba(255, 75, 75, 0.05); border: 1px dashed #ff4b4b; border-radius: 12px; padding: 15px; text-align: center;"><div style="color: #9da5b1; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Algorytm wyliczył moc: <b>{a_team}</b></div><div style="color: #ff4b4b; font-size: 2.2rem; font-weight: 900;">{auto_a_power}%</div></div>""", unsafe_allow_html=True)
            st.write("")
            
            avg_h_g, avg_a_g = df['FTHG'].mean() or 1.35, df['FTAG'].mean() or 1.25
            l_h = max(0.3, ((df[df['HomeTeam'] == h_team]['FTHG'].mean() or avg_h_g) / avg_h_g) * ((df[df['AwayTeam'] == a_team]['FTHG'].mean() or avg_h_g) / avg_h_g) * avg_h_g * (h_adj/100))
            l_a = max(0.3, ((df[df['AwayTeam'] == a_team]['FTAG'].mean() or avg_a_g) / avg_a_g) * ((df[df['HomeTeam'] == h_team]['FTAG'].mean() or avg_a_g) / avg_a_g) * avg_a_g * (a_adj/100))
            
            s_h, s_a = np.random.poisson(l_h, 10000), np.random.poisson(l_a, 10000)
            win, draw, loss = np.mean(s_h > s_a), np.mean(s_h == s_a), np.mean(s_h < s_a)

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

            l_h_ht, l_a_ht = h_stats['ht_gf'] * (h_adj / 100), a_stats['ht_gf'] * (a_adj / 100)
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
            for h_g in range(5):
                for a_g in range(5):
                    prob = np.mean((s_h == h_g) & (s_a == a_g)) * 100
                    if prob > 1.0: results.append((h_g, a_g, prob))

            results = sorted(results, key=lambda x: x[2], reverse=True)[:8]
            cols = st.columns(4)
            for idx, (h_g, a_g, prob) in enumerate(results):
                with cols[idx % 4]:
                    st.markdown(f"""<div style="background: linear-gradient(135deg, #1e212b, #161922); border-radius: 12px; padding: 15px; text-align: center; border: 2px solid rgba(0, 255, 136, 0.3); margin-bottom: 10px;"><h2 style="margin: 0; color: #00ff88;">{h_g} - {a_g}</h2><p style="margin: 5px 0 0 0; font-size: 1.1em; color: white;"><strong>{prob:.1f}%</strong></p></div>""", unsafe_allow_html=True)

            st.divider()
            st.markdown("<h3 style='text-align: center; color: #00ff88;'>⚖️ Zaawansowany Value Bet Finder (1X2)</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #9da5b1;'>Wpisz kursy bukmachera, aby sprawdzić ich realną opłacalność oraz ukrytą marżę.</p>", unsafe_allow_html=True)

            col_o1, col_ox, col_o2 = st.columns(3)
            odds_1 = col_o1.number_input(f"Kurs 1 ({h_team})", min_value=1.01, value=2.50, step=0.05)
            odds_x = col_ox.number_input("Kurs X (Remis)", min_value=1.01, value=3.20, step=0.05)
            odds_2 = col_o2.number_input(f"Kurs 2 ({a_team})", min_value=1.01, value=2.80, step=0.05)

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
        st.markdown("<p style='color: #9da5b1;'>Ostateczne wnioski algorytmu na podstawie symulacji 10,000 scenariuszy oraz analizy DNA zespołów.</p>", unsafe_allow_html=True)
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
                expert_tips.append((f"Wynik: {results[0][0]}-{results[0][1]}", results[0][2]/100))

                for tip, prob in expert_tips[:3]: st.markdown(f"""<div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; margin-bottom: 10px;"><span style="color: white; font-weight: bold;">{tip}</span><span style="color: #ffcc00; font-weight: 900;">{prob*100:.1f}%</span></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            risk_level = "NISKIE" if main_prob > 0.65 else ("ŚREDNIE" if main_prob > 0.45 else "WYSOKIE")
            risk_color = "#00ff88" if risk_level == "NISKIE" else ("#ffcc00" if risk_level == "ŚREDNIE" else "#ff4b4b")
            st.markdown(f"""<div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border-top: 4px solid {risk_color}; text-align: center;"><span style="color: #9da5b1; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 2px;">Ogólna Ocena Ryzyka</span><div style="color: {risk_color}; font-size: 2rem; font-weight: 900; margin-top: 5px;">{risk_level}</div><p style="color: #9da5b1; font-size: 0.9rem; margin-top: 10px; max-width: 600px; margin-left: auto; margin-right: auto;">Werdykt oparty na aktualnej formie strzeleckiej oraz stabilności defensywnej. Pamiętaj, że w sporcie zawsze istnieje element losowości. Graj odpowiedzialnie!</p></div>""", unsafe_allow_html=True)

    with tab4:
        st.header("🟨 Card & Aggression Analyzer")
        # 🔥 ZMIANA: Pobieramy statystyki tylko z ostatnich 5 meczów (forma)
        h_stats_recent = get_advanced_stats(h_team, 'Home', 'Wszystkie', last_n=5)
        a_stats_recent = get_advanced_stats(a_team, 'Away', 'Wszystkie', last_n=5)
        
        if h_stats_recent and a_stats_recent:
            h_agg_score = (h_stats_recent['fouls'] * 2) + (h_stats_recent['yellows'] * 10) + (h_stats_recent['reds'] * 25)
            a_agg_score = (a_stats_recent['fouls'] * 2) + (a_stats_recent['yellows'] * 10) + (a_stats_recent['reds'] * 25)
            
            # Normalizacja i suma agresji dla Kartek
            h_agg_pct = np.clip(h_agg_score / 0.8, 0, 100)
            a_agg_pct = np.clip(a_agg_score / 0.8, 0, 100)
            total_match_heat = (h_agg_pct + a_agg_pct) / 2

            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.markdown(f"""
                <div style="background: rgba(255, 204, 0, 0.05); border: 1px solid rgba(255, 204, 0, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #ffcc00; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Indeks Agresji: {h_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{h_agg_pct:.0f}%</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. fauli: {h_stats['fouls']:.1f} | Kartki: {h_stats['yellows']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_c2:
                st.markdown(f"""
                <div style="background: rgba(255, 204, 0, 0.05); border: 1px solid rgba(255, 204, 0, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #ffcc00; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Indeks Agresji: {a_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{a_agg_pct:.0f}%</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. fauli: {a_stats['fouls']:.1f} | Kartki: {a_stats['yellows']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            
            # Termometr temperatury meczu
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
                    <span style="color: #ff4b4b; font-weight: bold;">DNA: {h_stats['chaos'] if h_agg_score > a_agg_score else a_stats['chaos']:.1f}/10 (Wysoki Chaos)</span>
                </div>
                """, unsafe_allow_html=True)
                
            # H2H Kartek (jeśli są dane)
            h2h = get_h2h_stats(h_team, a_team, last_n=5)
            if h2h:
                st.write("")
                st.subheader("⚔️ Historia Kartek w H2H")
                h2h_table = "<table class='bet-table'><thead><tr><th>Data</th><th>Mecz</th><th>Żółte</th><th>Czerwone</th></tr></thead><tbody>"
                for _, row in h2h['data'].iterrows():
                    # Sumujemy kartki z obu stron
                    ty = int(row.get('HY', 0) + row.get('AY', 0))
                    tr = int(row.get('HR', 0) + row.get('AR', 0))
                    d_str = pd.to_datetime(row['Date'], dayfirst=True, errors='coerce').strftime('%d.%m.%Y')
                    h2h_table += f"<tr><td>{d_str}</td><td>{row['HomeTeam']} - {row['AwayTeam']}</td><td style='color:#ffcc00; font-weight:bold;'>{ty}</td><td style='color:#ff4b4b; font-weight:bold;'>{tr}</td></tr>"
                st.markdown(h2h_table + "</tbody></table>", unsafe_allow_html=True)

    with tab5:
        st.header("⛳ Corner Kick Analytics")
        st.markdown("<p style='color: #9da5b1;'>Analiza potencjału na rzuty rożne w oparciu o ostatnie 5 spotkań (aktualna forma).</p>", unsafe_allow_html=True)
        
        # 🔥 Pobieramy statystyki z ostatnich 5 meczów
        h_stats_recent = get_advanced_stats(h_team, 'Home', 'Wszystkie', last_n=5)
        a_stats_recent = get_advanced_stats(a_team, 'Away', 'Wszystkie', last_n=5)
        
        if h_stats_recent and a_stats_recent:
            # Obliczenia potencjału
            h_corner_pot = (h_stats_recent['corners'] + a_stats_recent['opp_corners']) / 2
            a_corner_pot = (a_stats_recent['corners'] + h_stats_recent['opp_corners']) / 2
            
            # --- TO BYŁ BRAKUJĄCY ELEMENT ---
            total_expected_corners = h_corner_pot + a_corner_pot
            # --------------------------------
            
            # Reszta Twojego kodu wyświetlającego karty...
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown(f"""
                <div style="background: rgba(0, 184, 255, 0.05); border: 1px solid rgba(0, 184, 255, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #00b8ff; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Potencjał Rożnych: {h_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{h_corner_pot:.1f}</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. nabijanych: {h_stats_recent['corners']:.1f} | Dopuszczanych: {h_stats_recent['opp_corners']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)
            # ... (tutaj reszta kodu z kartą gościa i paskiem sumy rożnych)

            with col_r2:
                st.markdown(f"""
                <div style="background: rgba(0, 184, 255, 0.05); border: 1px solid rgba(0, 184, 255, 0.2); padding: 20px; border-radius: 15px; text-align: center;">
                    <div style="color: #00b8ff; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Potencjał Rożnych: {a_team}</div>
                    <div style="color: white; font-size: 2.5rem; font-weight: 900;">{a_corner_pot:.1f}</div>
                    <div style="color: #9da5b1; font-size: 0.8rem; margin-top: 5px;">Śr. nabijanych: {a_stats['corners']:.1f} | Dopuszczanych: {a_stats['opp_corners']:.1f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            
            # Pasek całkowitej przewidywanej liczby rożnych
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
            
            # Logika podpowiedzi linii
            line_low = np.floor(total_expected_corners - 1.5)
            line_mid = np.floor(total_expected_corners - 0.5)
            
            with c_tip1:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #00ff88;"><span style="color: #9da5b1; font-size: 0.7rem;">BEZPIECZNA</span><br><b style="color: white;">Powyżej {line_low:.1f}</b></div>""", unsafe_allow_html=True)
            with c_tip2:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #ffcc00;"><span style="color: #9da5b1; font-size: 0.7rem;">OPTYMALNA</span><br><b style="color: white;">Powyżej {line_mid:.1f}</b></div>""", unsafe_allow_html=True)
            with c_tip3:
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; text-align: center; border-bottom: 3px solid #ff4b4b;"><span style="color: #9da5b1; font-size: 0.7rem;">RYZYKOWNA</span><br><b style="color: white;">Powyżej {line_mid + 1:.1f}</b></div>""", unsafe_allow_html=True)

            # H2H Rożnych
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
# --- EKRAN 2: SKANER LIGI ---
# =====================================================================
elif menu_choice == "🤖 Skaner Ligi":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #00d4ff; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px;">🤖 Automatyczny Skaner Ligi</h2>
        <p style="color: #9da5b1; font-size: 0.9rem;">AI analizuje całą tabelę w poszukiwaniu najlepszych trendów pod zakłady bukmacherskie.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Uruchom Głęboki Skan Wybranej Ligi", use_container_width=True):
        with st.spinner('Sztuczna inteligencja analizuje setki meczów...'):
            current_season_df = df[df['Season'] == '2526']
            all_teams_in_league = current_season_df['HomeTeam'].unique()
            league_stats = []
            
            for t in all_teams_in_league:
                t_stats = get_advanced_stats(t, 'Home', "Wszystkie", last_n=5)
                if t_stats:
                    sym, txt, col = get_team_form_trend(t, 'Home', "Wszystkie", last_n=5)
                    power = (t_stats['dom'] * 0.3) + (t_stats['killer']/10.0 * 0.35) + (t_stats['safety'] * 0.35)
                    league_stats.append({'team': t, 'power': (power / 5.5) * 100, 'form_sym': sym, 'avg_goals': t_stats['gf'] + t_stats['ga'], 'defense': t_stats['safety']})
            
            league_stats.sort(key=lambda x: x['power'], reverse=True)
            top_teams, bottom_teams = league_stats[:3], league_stats[-3:]
            league_stats.sort(key=lambda x: x['avg_goals'], reverse=True)
            over_teams = league_stats[:3]

            st.write("")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown("<div style='background: rgba(0, 255, 136, 0.05); border-top: 4px solid #00ff88; padding: 15px; border-radius: 10px; height: 100%;'><h4 style='color: #00ff88; text-align: center; margin-top:0;'>🟢 TOP 3: Graj na nich</h4>", unsafe_allow_html=True)
                for i, t in enumerate(top_teams): st.markdown(f"<b>{i+1}. {t['team']}</b><br><span style='font-size: 0.8rem; color: #9da5b1;'>Moc AI: <span style='color:#00ff88;'>{t['power']:.1f}%</span> | Forma: {t['form_sym']}</span><hr style='margin: 8px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with col_s2:
                st.markdown("<div style='background: rgba(255, 75, 75, 0.05); border-top: 4px solid #ff4b4b; padding: 15px; border-radius: 10px; height: 100%;'><h4 style='color: #ff4b4b; text-align: center; margin-top:0;'>🔴 FLOP 3: Graj przeciwko</h4>", unsafe_allow_html=True)
                for i, t in enumerate(reversed(bottom_teams)): st.markdown(f"<b>{i+1}. {t['team']}</b><br><span style='font-size: 0.8rem; color: #9da5b1;'>Obrona: <span style='color:#ff4b4b;'>{t['defense']:.1f}/10</span> | Forma: {t['form_sym']}</span><hr style='margin: 8px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with col_s3:
                st.markdown("<div style='background: rgba(0, 212, 255, 0.05); border-top: 4px solid #00d4ff; padding: 15px; border-radius: 10px; height: 100%;'><h4 style='color: #00d4ff; text-align: center; margin-top:0;'>⚽ TOP 3: Gole (Over 2.5)</h4>", unsafe_allow_html=True)
                for i, t in enumerate(over_teams): st.markdown(f"<b>{i+1}. {t['team']}</b><br><span style='font-size: 0.8rem; color: #9da5b1;'>Śr. goli w meczu: <span style='color:#00d4ff;'>{t['avg_goals']:.2f}</span></span><hr style='margin: 8px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# --- EKRAN 3: BET TRACKER ---
# =====================================================================
elif menu_choice == "🏦 Bet Tracker":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #00ff88; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px;">🏦 Dziennik Typera (Bet Tracker)</h2>
        <p style="color: #9da5b1; font-size: 0.9rem;">Twój osobisty skarbiec. Śledź zakłady, analizuj Yield i kontroluj swój bankroll jak zawodowiec.</p>
    </div>
    """, unsafe_allow_html=True)

    FILE_NAME = "bet_history.csv"
    if not os.path.exists(FILE_NAME):
        pd.DataFrame(columns=["Data", "Mecz", "Typ", "Kurs", "Stawka", "Status", "Zysk_Strata"]).to_csv(FILE_NAME, index=False)

    history_df = pd.read_csv(FILE_NAME)

    total_bets = len(history_df)
    won_bets = len(history_df[history_df["Status"] == "Wygrana"])
    lost_bets = len(history_df[history_df["Status"] == "Przegrana"])
    total_staked = history_df["Stawka"].sum()
    total_profit = history_df["Zysk_Strata"].sum()
    yield_pct = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
    win_rate = (won_bets / (won_bets + lost_bets) * 100) if (won_bets + lost_bets) > 0 else 0.0

    profit_color = "#00ff88" if total_profit > 0 else ("#ff4b4b" if total_profit < 0 else "white")
    yield_color = "#00ff88" if yield_pct > 0 else ("#ff4b4b" if yield_pct < 0 else "white")

    def make_stat_card(title, value, top_color, text_color="white"):
        return f"""<div style="background: linear-gradient(135deg, #1e212b, #161922); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.3); text-align: center; position: relative; overflow: hidden;"><div style="position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: {top_color};"></div><div style="color: #9da5b1; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">{title}</div><div style="color: {text_color}; font-size: 2.2rem; font-weight: 900; line-height: 1;">{value}</div></div>"""

    c_stat1, c_stat2, c_stat3, c_stat4 = st.columns(4)
    with c_stat1: st.markdown(make_stat_card("Zagrane Kupony", total_bets, "#00b8ff"), unsafe_allow_html=True)
    with c_stat2: st.markdown(make_stat_card("Skuteczność", f"{win_rate:.1f}%", "#ffcc00", "#ffcc00"), unsafe_allow_html=True)
    with c_stat3: st.markdown(make_stat_card("Czysty Zysk", f"{total_profit:.2f}", profit_color, profit_color), unsafe_allow_html=True)
    with c_stat4: st.markdown(make_stat_card("ROI / Yield", f"{yield_pct:.1f}%", yield_color, yield_color), unsafe_allow_html=True)

    st.divider()

    st.markdown("<h3 style='color: white; margin-bottom: 15px;'>➕ Dodaj nowy e-Kupon</h3>", unsafe_allow_html=True)
    with st.form("add_bet_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns([2, 1.2])
        with col_f1:
            f_match = st.text_area("Rozpisz mecze na kuponie (każdy w nowej linii)", value="", height=125)
            f_pick = st.text_input("Główne Typy (np. Zwycięstwa, BTTS, Mix)", value="")
        with col_f2:
            f_date = st.date_input("Data zagrania")
            f_odds = st.number_input("Kurs całkowity (AKO)", min_value=1.01, value=2.00, step=0.05)
            f_stake = st.number_input("Stawka (PLN)", min_value=1.0, value=50.0, step=5.0)
            f_status = st.selectbox("Status Kuponu", ["Oczekuje ⏳", "Wygrana ✅", "Przegrana ❌"])

        if st.form_submit_button("💾 Zapisz Kupon do Bazy"):
            profit = 0.0
            if f_status == "Wygrana ✅": profit = (f_stake * f_odds) - f_stake
            elif f_status == "Przegrana ❌": profit = -f_stake

            new_bet = pd.DataFrame([{"Data": f_date.strftime("%Y-%m-%d"), "Mecz": f_match.replace('\n', ' | '), "Typ": f_pick, "Kurs": f_odds, "Stawka": f_stake, "Status": f_status.replace(" ✅", "").replace(" ❌", "").replace(" ⏳", ""), "Zysk_Strata": round(profit, 2)}])
            pd.concat([history_df, new_bet], ignore_index=True).to_csv(FILE_NAME, index=False)
            st.rerun()

    st.write("")
    st.markdown("<h3 style='color: white; margin-bottom: 15px;'>📋 Historia Twoich Zakładów</h3>", unsafe_allow_html=True)
    
    if len(history_df) > 0:
        display_df = history_df.iloc[::-1].copy()
        table_html = "<style>.tracker-table { width: 100%; border-collapse: collapse; border-radius: 12px; overflow: hidden; background: linear-gradient(180deg, #1e212b 0%, #161922 100%); border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; } .tracker-table th { background: rgba(0, 0, 0, 0.4); color: #9da5b1; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; padding: 15px 10px; border-bottom: 2px solid rgba(255,255,255,0.05); text-align: center; } .tracker-table td { padding: 12px 10px; color: #ffffff; border-bottom: 1px solid rgba(255,255,255,0.02); text-align: center; font-size: 0.9rem; transition: background 0.3s ease; } .tracker-table tr:hover td { background: rgba(0, 184, 255, 0.05); }</style><table class='tracker-table'><thead><tr><th style='width: 100px;'>Data</th><th style='text-align: left;'>Kupon (Mecze)</th><th>Typ</th><th>AKO</th><th>Stawka</th><th>Zysk / Strata</th><th>Status</th></tr></thead><tbody>"
        
        for _, row in display_df.iterrows():
            if "Wygrana" in row['Status']: s_html, p_html = "<div style='background: rgba(0,255,136,0.1); color: #00ff88; padding: 4px 8px; border-radius: 6px; font-weight: bold; border: 1px solid rgba(0,255,136,0.2);'>WYGRANA</div>", f"<span style='color: #00ff88; font-weight: 900;'>+{row['Zysk_Strata']} PLN</span>"
            elif "Przegrana" in row['Status']: s_html, p_html = "<div style='background: rgba(255,75,75,0.1); color: #ff4b4b; padding: 4px 8px; border-radius: 6px; font-weight: bold; border: 1px solid rgba(255,75,75,0.2);'>PRZEGRANA</div>", f"<span style='color: #ff4b4b; font-weight: 900;'>{row['Zysk_Strata']} PLN</span>"
            else: s_html, p_html = "<div style='background: rgba(255,204,0,0.1); color: #ffcc00; padding: 4px 8px; border-radius: 6px; font-weight: bold; border: 1px solid rgba(255,204,0,0.2);'>OCZEKUJE</div>", "<span style='color: #9da5b1;'>---</span>"
            mecz_txt = str(row['Mecz']).replace(" | ", "<br><span style='color: #00b8ff; font-size: 0.7rem; margin-right: 5px;'>➕</span>")
            table_html += f"<tr><td style='color: #9da5b1; font-size: 0.8rem;'>{row['Data']}</td><td style='text-align: left; font-weight: bold; line-height: 1.5;'>{mecz_txt}</td><td style='color: #00d4ff; font-size: 0.85rem; font-weight: bold;'>{row['Typ']}</td><td style='font-weight: 900; font-size: 1.1rem;'>{row['Kurs']}</td><td style='color: #9da5b1;'>{row['Stawka']} zł</td><td>{p_html}</td><td>{s_html}</td></tr>"
        
        st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
        
        with st.expander("⚙️ Narzędzia Administracyjne / Korekta Błędów"):
            options = [f"[{idx}] {row['Data']} | {str(row['Mecz']).replace(' | ', ' + ')[:32] + ('...' if len(str(row['Mecz'])) > 35 else '')} | {row['Status']}" for idx, row in history_df.iterrows()]
            if options:
                selected = st.selectbox("Wybierz kupon do usunięcia:", options)
                col_z1, col_z2 = st.columns(2)
                with col_z1:
                    if st.button("🗑️ Usuń ZAZNACZONY kupon"):
                        history_df.drop(int(selected.split("]")[0].replace("[", ""))).reset_index(drop=True).to_csv(FILE_NAME, index=False)
                        st.rerun()
                with col_z2:
                    if st.button("🚨 Usuń WSZYSTKIE kupony (Reset)"):
                        if os.path.exists(FILE_NAME): os.remove(FILE_NAME); st.rerun()
    else:
        st.markdown("""<div style="background: rgba(255,255,255,0.02); padding: 40px; border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1); text-align: center;"><div style="font-size: 3rem; margin-bottom: 10px;">🕸️</div><div style="color: #9da5b1; font-size: 1.1rem;">Baza jest pusta. Dodaj swój pierwszy zakład, aby aktywować Tracker!</div></div>""", unsafe_allow_html=True)