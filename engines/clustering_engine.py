# engines/clustering_engine.py

from datetime import datetime
from collections import defaultdict

class SimpleClusterer:

    def __init__(self):
        self.index = defaultdict(list)

    def make_key(self, merchant_id, complaint_type, txn_time_iso):
        if merchant_id:
            hour = "nohour"
            if txn_time_iso:
                try:
                    hour = datetime.fromisoformat(txn_time_iso).strftime("%Y%m%d%H")
                except:
                    pass
            return f"{merchant_id}::{complaint_type}::{hour}"
        return f"GEN::{complaint_type}"

    def assign(self, merchant_id, complaint_type, txn_time_iso, case_id=None):
        key = self.make_key(merchant_id, complaint_type, txn_time_iso)
        if case_id:
            self.index[key].append(case_id)
        count = len(self.index[key])
        return f"{key}#{count}"
