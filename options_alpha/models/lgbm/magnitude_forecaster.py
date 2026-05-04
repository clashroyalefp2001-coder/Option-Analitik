import lightgbm as lgb
import pandas as pd

class MagnitudeForecaster:
    def __init__(self):
        self.model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05)
        
    def train(self, X, y):
        self.model.fit(X, y)
        
    def predict(self, X):
        return self.model.predict(X)
