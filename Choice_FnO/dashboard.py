import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, date

# Streamlit configuration
st.set_page_config(page_title="Nifty Ladder Bot", layout="wide")

# CSS for rich aesthetics (as requested in Web App guidelines, adapted for Streamlit)
st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .css-1d391kg {
        background-color: #161b22;
    }
    .metric-card {
        background: linear-gradient(145deg, #1f2428, #24292e);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.5);
        text-align: center;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #58a6ff;
    }
    .metric-label {
        font-size: 1rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Nifty Fut+Opt Ladder Bot")
st.markdown("Paper Trading Dashboard - Choice Broking API")

from dotenv import load_dotenv, set_key

load_dotenv()

# Setup Bot Instance in Session State so it persists across reruns
if "credentials_provided" not in st.session_state:
    if all([os.getenv("CHOICE_VENDOR_ID"), os.getenv("CHOICE_VENDOR_KEY"), os.getenv("CHOICE_API_KEY"), os.getenv("CHOICE_MOBILE_NO"), os.getenv("CHOICE_AES_KEY"), os.getenv("CHOICE_AES_IV")]):
        st.session_state.credentials_provided = True
    else:
        st.session_state.credentials_provided = False

if not st.session_state.credentials_provided:
    st.subheader("🔑 Login - Choice API Credentials")
    with st.form("login_form"):
        st.write("Please provide your Choice Broking API credentials to access the dashboard.")
        col_cred1, col_cred2 = st.columns(2)
        with col_cred1:
            vendor_id = st.text_input("Vendor ID", value=os.getenv("CHOICE_VENDOR_ID", ""))
            vendor_key = st.text_input("Vendor Key", type="password", value=os.getenv("CHOICE_VENDOR_KEY", ""))
            api_key = st.text_input("API Key", type="password", value=os.getenv("CHOICE_API_KEY", ""))
        with col_cred2:
            mobile_no = st.text_input("Mobile No", value=os.getenv("CHOICE_MOBILE_NO", ""))
            aes_key = st.text_input("AES Key", type="password", value=os.getenv("CHOICE_AES_KEY", ""))
            aes_iv = st.text_input("AES IV", type="password", value=os.getenv("CHOICE_AES_IV", ""))
        
        base_url = st.text_input("Base URL", value=os.getenv("CHOICE_BASE_URL", "https://japi.choiceindia.com"))
        
        submit = st.form_submit_button("Login to Dashboard")
        if submit:
            if not all([vendor_id, vendor_key, api_key, mobile_no, aes_key, aes_iv]):
                st.error("Please fill in all credentials.")
            else:
                env_file = ".env"
                if not os.path.exists(env_file):
                    open(env_file, 'w').close()
                set_key(env_file, "CHOICE_VENDOR_ID", vendor_id)
                set_key(env_file, "CHOICE_VENDOR_KEY", vendor_key)
                set_key(env_file, "CHOICE_API_KEY", api_key)
                set_key(env_file, "CHOICE_MOBILE_NO", mobile_no)
                set_key(env_file, "CHOICE_AES_KEY", aes_key)
                set_key(env_file, "CHOICE_AES_IV", aes_iv)
                set_key(env_file, "CHOICE_BASE_URL", base_url)
                
                os.environ["CHOICE_VENDOR_ID"] = vendor_id
                os.environ["CHOICE_VENDOR_KEY"] = vendor_key
                os.environ["CHOICE_API_KEY"] = api_key
                os.environ["CHOICE_MOBILE_NO"] = mobile_no
                os.environ["CHOICE_AES_KEY"] = aes_key
                os.environ["CHOICE_AES_IV"] = aes_iv
                os.environ["CHOICE_BASE_URL"] = base_url
                st.session_state.credentials_provided = True
                st.rerun()
    st.stop()

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "App Logs", "Order Logs", "Rollover Logs", "Leg Logs"])

if page != "Dashboard":
    st.title(f"📄 {page}")
    log_files = {
        "App Logs": "logs/app.log",
        "Order Logs": "logs/order_log.csv",
        "Rollover Logs": "logs/rollover_log.csv",
        "Leg Logs": "logs/leg_log.csv"
    }
    log_file = log_files.get(page)
    
    if log_file and os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_data = f.read()
            
        st.download_button(
            label=f"⬇️ Download {page}",
            data=log_data,
            file_name=os.path.basename(log_file),
            mime="text/csv" if log_file.endswith(".csv") else "text/plain"
        )
        
        if log_file.endswith(".csv"):
            try:
                df = pd.read_csv(log_file)
                # Reverse to show latest logs first
                st.dataframe(df.iloc[::-1], use_container_width=True)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                st.text_area("Log Content", log_data, height=500)
        else:
            st.text_area("Log Content", log_data, height=500)
    else:
        st.info(f"Log file not found: {log_file}")
    
    st.stop()

@st.cache_resource
def get_bot():
    from main import bot_instance
    return bot_instance

bot = get_bot()

# Controls
col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Start Bot", width="stretch", type="primary" if not bot.is_running else "secondary"):
        bot.start()
        st.toast("Bot Started!")
with col2:
    if st.button("⏹️ Stop Bot", width="stretch", type="primary" if bot.is_running else "secondary"):
        bot.stop()
        st.toast("Bot Stopped!")
    if st.button("🔄 Force Weekly Rollover", width="stretch"):
        from expiry_calc import get_weekly_expiry
        bot.state_manager.state["weekly_expiry"] = get_weekly_expiry().isoformat()
        bot.state_manager.save()
        bot.rollover_manager.perform_weekly_rollover(bot.feed.current_ltp)
        st.toast("Weekly Rollover Triggered!")
    if st.button("🔄 Force Monthly Rollover", width="stretch"):
        from expiry_calc import get_current_and_next_monthly_expiries
        _, next_exp = get_current_and_next_monthly_expiries()
        bot.state_manager.state["next_monthly_expiry"] = next_exp.isoformat()
        bot.state_manager.save()
        bot.rollover_manager.perform_monthly_rollover(bot.feed.current_ltp)
        st.toast("Monthly Rollover Triggered!")

with st.expander("⚠️ Danger Zone - Reset Bot"):
    st.warning("This will permanently delete all logs and reset the bot's state to factory defaults.")
    if st.button("Fully Reset Bot & Logs", type="primary"):
        bot.stop()
        
        # Reset state memory and save to file
        bot.state_manager.state = {
            "base": None,
            "direction": "FLAT",
            "legs": {},
            "closed_legs": [],
            "realized_pnl": 0.0,
            "total_legs_opened": 0,
            "weekly_expiry": None,
            "monthly_expiry": None
        }
        bot.state_manager.save()
        
        # Clear log files
        import shutil
        if os.path.exists("logs"):
            shutil.rmtree("logs", ignore_errors=True)
            os.makedirs("logs", exist_ok=True)
            
        st.toast("Bot and logs have been completely reset!")
        time.sleep(1)
        st.rerun()

st.markdown("---")

# Dashboard state fetching
STATE_FILE = "state_snapshot.json"
state = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        pass

# Metrics
col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)

ltp = bot.feed.current_ltp if bot.is_running else state.get("last_ltp", "N/A")
base = state.get("base", "N/A")
direction = state.get("direction", "FLAT")
active_legs_count = len(state.get("legs", {}))
realized_pnl = state.get("realized_pnl", 0.0)

# Calculate PnL for active legs
total_pnl = 0.0
legs_data = []
if state.get("legs"):
    for leg_id, ldata in state["legs"].items():
        pnl = 0.0
        fut_price = ldata.get('entry_price', 0)
        short_price = ldata.get('short_opt', {}).get('premium', 0)
        long_price = ldata.get('long_opt', {}).get('premium', 0)
        
        if bot.is_running:
            short_t = bot.feed.symbol_master.get_option_token(ldata['short_opt']['expiry'], ldata['short_opt']['strike'], ldata['short_opt']['type'])
            short_sym = bot.feed.symbol_master.get_symbol(short_t) if short_t else f"NIFTY_{ldata['short_opt']['strike']}_{ldata['short_opt']['type']}"
            
            long_t = bot.feed.symbol_master.get_option_token(ldata['long_opt']['expiry'], ldata['long_opt']['strike'], ldata['long_opt']['type'])
            long_sym = bot.feed.symbol_master.get_symbol(long_t) if long_t else f"NIFTY_{ldata['long_opt']['strike']}_{ldata['long_opt']['type']}"
            
            from datetime import datetime
            try:
                m_exp = datetime.strptime(ldata["monthly_expiry"], "%Y-%m-%d")
                fut_sym = f"NIFTY{m_exp.strftime('%y%b').upper()}FUT"
            except Exception:
                fut_sym = "NIFTY_FUT"
                
            fut_price = bot.feed.prices.get(fut_sym, fut_price)
            short_price = bot.feed.prices.get(short_sym, short_price)
            long_price = bot.feed.prices.get(long_sym, long_price)
        else:
            fut_price = state.get("last_ltp", fut_price)
            
        fut_pnl = (fut_price - ldata['entry_price']) * 65 if ldata['future_side'] == "LONG" else (ldata['entry_price'] - fut_price) * 65
        short_pnl = (ldata['short_opt']['premium'] - short_price) * 65
        long_pnl = (long_price - ldata['long_opt']['premium']) * 65
        
        legacy_rollover = ldata.get("realized_pnl", 0.0) - (ldata.get("hist_fut_pnl", 0.0) + ldata.get("hist_short_pnl", 0.0) + ldata.get("hist_long_pnl", 0.0))
        
        fut_pnl += ldata.get("hist_fut_pnl", 0.0)
        short_pnl += ldata.get("hist_short_pnl", 0.0)
        long_pnl += ldata.get("hist_long_pnl", 0.0) + legacy_rollover
        
        pnl = fut_pnl + short_pnl + long_pnl
            
        total_pnl += pnl
        
        # Calculate break even point
        try:
            short_entry = float(ldata.get("short_opt", {}).get("premium", 0))
            long_entry = float(ldata.get("long_opt", {}).get("premium", 0))
            net_premium = short_entry - long_entry
            
            future_entry = float(ldata.get("entry_price", 0))
            if ldata.get("future_side") == "LONG":
                break_even = round(future_entry - net_premium, 2)
            else:
                break_even = round(future_entry + net_premium, 2)
        except (ValueError, TypeError):
            break_even = "N/A"
            
        def format_opt_sym(opt_data):
            if not opt_data:
                return "N/A"
            try:
                from datetime import datetime
                # Format to look like NIFTY 09JUL 24500 CE
                exp = datetime.strptime(opt_data['expiry'], "%Y-%m-%d")
                exp_str = exp.strftime("%d%b").upper()
                return f"NIFTY {exp_str} {opt_data['strike']} {opt_data['type']}"
            except Exception:
                return f"NIFTY {opt_data.get('strike')} {opt_data.get('type')}"

        trigger_p = ldata.get("trigger_price")
        future_s = ldata.get("future_side")
        if trigger_p is not None and future_s:
            exit_price = (trigger_p + 50) if future_s == "LONG" else (trigger_p - 50)
        else:
            exit_price = "N/A"

        legs_data.append({
            "Leg ID": leg_id,
            "Future Side": future_s,
            "Trigger Price": trigger_p,
            "Exit Price": exit_price,
            "Future Entry": ldata.get("entry_price"),
            "Future Live": fut_price,
            "Short Opt": format_opt_sym(ldata.get("short_opt")),
            "Short Entry": ldata.get("short_opt", {}).get("premium"),
            "Short Live": short_price,
            "Long Opt": format_opt_sym(ldata.get("long_opt")),
            "Long Entry": ldata.get("long_opt", {}).get("premium"),
            "Long Live": long_price,
            "Break Even": break_even,
            "Future PnL": round(fut_pnl, 2),
            "Short Opt PnL": round(short_pnl, 2),
            "Long Opt PnL": round(long_pnl, 2),
            "Total PnL": round(pnl, 2),
            "Entry Time": ldata.get("entry_time")
        })

col_m1.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Status</div>
    <div class="metric-value" style="color: {'#2ea043' if bot.is_running else '#f85149'}">
        {"RUNNING" if bot.is_running else "STOPPED"}
    </div>
</div>
""", unsafe_allow_html=True)

col_m2.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Current LTP</div>
    <div class="metric-value">{ltp}</div>
</div>
""", unsafe_allow_html=True)

col_m3.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Base / Dir</div>
    <div class="metric-value">{base} / {direction[:3]}</div>
</div>
""", unsafe_allow_html=True)

col_m4.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Active Legs</div>
    <div class="metric-value">{active_legs_count}</div>
</div>
""", unsafe_allow_html=True)

unrealized_pnl_color = "#2ea043" if total_pnl >= 0 else "#f85149"
col_m5.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Unrealized PnL</div>
    <div class="metric-value" style="color: {unrealized_pnl_color}">{round(total_pnl, 2)}</div>
</div>
""", unsafe_allow_html=True)

realized_pnl_color = "#2ea043" if realized_pnl >= 0 else "#f85149"
col_m6.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Realized PnL</div>
    <div class="metric-value" style="color: {realized_pnl_color}">{round(realized_pnl, 2)}</div>
</div>
""", unsafe_allow_html=True)


# Data views
st.subheader("Active Legs")

if active_legs_count > 0:
    agg_net_qty = 0
    total_fut_entry_val = 0
    total_short_prem = 0
    total_long_prem = 0
    
    for leg_id, ldata in state.get("legs", {}).items():
        qty = 1 if ldata.get("future_side") == "LONG" else -1
        agg_net_qty += qty
        try:
            total_fut_entry_val += float(ldata.get("entry_price", 0)) * qty
            short_prem = float(ldata.get("short_opt", {}).get("premium", 0))
            long_prem = float(ldata.get("long_opt", {}).get("premium", 0))
            total_short_prem += short_prem
            total_long_prem += long_prem
        except (ValueError, TypeError):
            pass
            
    total_net_prem = total_short_prem - total_long_prem
            
    if agg_net_qty != 0:
        avg_fut_entry = abs(total_fut_entry_val / agg_net_qty)
        avg_opt_prem = total_net_prem / abs(agg_net_qty)
        if agg_net_qty > 0:
            agg_be = avg_fut_entry - avg_opt_prem
            fut_str = f"{agg_net_qty} LONG @ {round(avg_fut_entry, 2)}"
        else:
            agg_be = avg_fut_entry + avg_opt_prem
            fut_str = f"{abs(agg_net_qty)} SHORT @ {round(avg_fut_entry, 2)}"
            
        opt_str = f"Short: {round(total_short_prem, 2)} | Long: {round(total_long_prem, 2)}"
        be_str = f"{round(agg_be, 2)}"
    else:
        fut_str = "FLAT (Net 0)"
        be_str = "N/A"
        
    st.markdown(f"**Aggregate Portfolio Position:** Futures = `{fut_str}`")

if legs_data:
    st.dataframe(pd.DataFrame(legs_data), width="stretch")
else:
    st.info("No active legs.")

st.subheader("Recent Legs")
LEG_LOG = "logs/leg_log.csv"
if os.path.exists(LEG_LOG):
    try:
        df = pd.read_csv(LEG_LOG).tail(10) # Show last 10
        st.dataframe(df, width="stretch")
    except Exception as e:
        st.warning(f"Could not load order log: {e}")
else:
    st.info("No orders placed yet.")

from streamlit_autorefresh import st_autorefresh
# Auto-refresh every 2000 milliseconds (2 seconds)
st_autorefresh(interval=2000, key="data_refresh")
