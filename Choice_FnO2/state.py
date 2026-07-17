import json
import os
from datetime import datetime

STATE_FILE = "state_snapshot.json"

class BotState:
    def __init__(self):
        self.state = {
            "base": None,           # ref point, mult of 10
            "direction": "FLAT",    # "ABOVE" / "BELOW" / "FLAT"
            "legs": {},             # L1, L2, etc.
            "closed_legs": [],      # List of closed leg records
            "realized_pnl": 0.0,    # Cumulative PnL of all closed positions
            "total_legs_opened": 0, # ever-increasing counter
            "weekly_expiry": None,  # YYYY-MM-DD
            "monthly_expiry": None  # YYYY-MM-DD
        }
        self.load()

    def load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    self.state = json.load(f)
                    
                # Upgrade legacy leg IDs (e.g., L1 -> L1_20260707)
                if "legs" in self.state:
                    new_legs = {}
                    changed = False
                    for leg_id, leg_data in self.state["legs"].items():
                        if "_" not in leg_id:
                            entry_time = leg_data.get("entry_time", "")
                            if entry_time:
                                try:
                                    date_str = datetime.strptime(entry_time[:10], "%Y-%m-%d").strftime("%Y%m%d")
                                    new_id = f"{leg_id}_{date_str}"
                                    new_legs[new_id] = leg_data
                                    changed = True
                                    continue
                                except Exception:
                                    pass
                        new_legs[leg_id] = leg_data
                    
                    if changed:
                        self.state["legs"] = new_legs
                        self.save()
            except Exception as e:
                print(f"Error loading state: {e}")

    def save(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"Error saving state: {e}")

    def add_leg(self, leg_id, leg_data):
        self.state["legs"][leg_id] = leg_data
        self.save()

    def remove_leg(self, leg_id):
        if leg_id in self.state["legs"]:
            del self.state["legs"][leg_id]
            self.save()

    def update_leg(self, leg_id, leg_data):
        if leg_id in self.state["legs"]:
            self.state["legs"][leg_id].update(leg_data)
            self.save()
            
    def get_last_leg(self):
        if not self.state["legs"]:
            return None, None
        
        # Sort legs by entry_time to correctly identify the most recently opened leg
        def get_time(leg_item):
            # leg_item is a tuple (leg_id, leg_data)
            return leg_item[1].get("entry_time", "")
            
        sorted_legs = sorted(self.state["legs"].items(), key=get_time)
        return sorted_legs[-1][0], sorted_legs[-1][1]
