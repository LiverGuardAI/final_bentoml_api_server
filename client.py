"""
LiverGuard CDSS - BentoML Client

Django에서 BentoML 서비스 호출용 클라이언트
"""

import bentoml
from typing import Dict, List


class LiverGuardClient:
    def __init__(self, server_url: str = "http://localhost:3001"):
        self.server_url = server_url
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = bentoml.SyncHTTPClient(self.server_url)
        return self._client
    
    def health_check(self) -> Dict:
        try:
            return self.client.health()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def predict_stage(self, clinical: List[float], ct: List[float]) -> Dict:
        try:
            return self.client.predict_stage(clinical=clinical, ct=ct)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def predict_relapse(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        try:
            return self.client.predict_relapse(clinical=clinical, mrna=mrna, ct=ct)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def predict_survival(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        try:
            return self.client.predict_survival(clinical=clinical, mrna=mrna, ct=ct)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def predict_all(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        try:
            return self.client.predict_all(clinical=clinical, mrna=mrna, ct=ct)
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import numpy as np
    
    client = LiverGuardClient("http://localhost:3001")
    
    print("=== Health Check ===")
    print(client.health_check())
    
    clinical = np.random.randn(11).tolist()
    mrna = np.random.randn(20).tolist()
    ct = np.random.randn(512).tolist()
    
    print("\n=== Task 1 ===")
    print(client.predict_stage(clinical, ct))
    
    print("\n=== Task 2 ===")
    print(client.predict_relapse(clinical, mrna, ct))
    
    print("\n=== Task 3 ===")
    print(client.predict_survival(clinical, mrna, ct))
