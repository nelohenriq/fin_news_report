import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import yfinance as yf
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import logging

class CryptoAnalyzer:
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.model = None
        self.lookback_period = 60  # Days of historical data to consider
        self.prediction_period = 7  # Days to predict ahead

    def fetch_historical_data(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        """Fetch historical price data for the given crypto ticker."""
        try:
            crypto = yf.Ticker(ticker)
            df = crypto.history(period=period)
            return df
        except Exception as e:
            logging.error(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, df: pd.DataFrame) -> dict:
        """Calculate various technical indicators."""
        try:
            # Initialize indicators
            sma = SMAIndicator(close=df['Close'], window=20)
            ema = EMAIndicator(close=df['Close'], window=20)
            macd = MACD(close=df['Close'])
            rsi = RSIIndicator(close=df['Close'])
            bb = BollingerBands(close=df['Close'])

            indicators = {
                'sma': sma.sma_indicator().iloc[-1],
                'ema': ema.ema_indicator().iloc[-1],
                'macd': macd.macd().iloc[-1],
                'macd_signal': macd.macd_signal().iloc[-1],
                'rsi': rsi.rsi().iloc[-1],
                'bb_upper': bb.bollinger_hband().iloc[-1],
                'bb_lower': bb.bollinger_lband().iloc[-1],
                'current_price': df['Close'].iloc[-1]
            }

            # Generate trading signals
            indicators['signals'] = {
                'rsi_oversold': indicators['rsi'] < 30,
                'rsi_overbought': indicators['rsi'] > 70,
                'price_above_sma': indicators['current_price'] > indicators['sma'],
                'macd_bullish': indicators['macd'] > indicators['macd_signal'],
                'price_at_bb_lower': indicators['current_price'] < indicators['bb_lower'],
                'price_at_bb_upper': indicators['current_price'] > indicators['bb_upper']
            }

            return indicators
        except Exception as e:
            logging.error(f"Error calculating technical indicators: {e}")
            return {}

    def prepare_data_for_prediction(self, df: pd.DataFrame) -> tuple:
        """Prepare data for LSTM model."""
        try:
            # Use closing prices for prediction
            data = df['Close'].values.reshape(-1, 1)
            scaled_data = self.scaler.fit_transform(data)

            X, y = [], []
            for i in range(self.lookback_period, len(scaled_data) - self.prediction_period):
                X.append(scaled_data[i - self.lookback_period:i])
                y.append(scaled_data[i:i + self.prediction_period])

            X = np.array(X)
            y = np.array(y)

            return X, y
        except Exception as e:
            logging.error(f"Error preparing data for prediction: {e}")
            return np.array([]), np.array([])

    def train_model(self, X: np.ndarray, y: np.ndarray):
        """Train LSTM model for price prediction."""
        try:
            self.model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.lookback_period, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(self.prediction_period)
            ])

            self.model.compile(optimizer='adam', loss='mse')
            self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        except Exception as e:
            logging.error(f"Error training model: {e}")

    def predict_prices(self, df: pd.DataFrame) -> dict:
        """Generate price predictions."""
        try:
            if len(df) < self.lookback_period:
                return {}

            X, y = self.prepare_data_for_prediction(df)
            if len(X) == 0 or len(y) == 0:
                return {}

            self.train_model(X, y)

            # Prepare last sequence for prediction
            last_sequence = df['Close'].values[-self.lookback_period:]
            last_sequence = self.scaler.transform(last_sequence.reshape(-1, 1))
            last_sequence = last_sequence.reshape(1, self.lookback_period, 1)

            # Generate prediction
            prediction = self.model.predict(last_sequence)
            prediction = self.scaler.inverse_transform(prediction)[0]

            return {
                'predicted_prices': prediction.tolist(),
                'prediction_dates': pd.date_range(
                    start=df.index[-1] + pd.Timedelta(days=1),
                    periods=self.prediction_period
                ).strftime('%Y-%m-%d').tolist()
            }
        except Exception as e:
            logging.error(f"Error generating predictions: {e}")
            return {}

def analyze_crypto(state: dict) -> dict:
    """Main function to analyze crypto assets."""
    try:
        crypto_tickers = [t for t in state["tickers"] if t.endswith('-USD')]
        analyzer = CryptoAnalyzer()
        crypto_analysis = {}

        for ticker in crypto_tickers:
            # Fetch historical data
            df = analyzer.fetch_historical_data(ticker)
            if df.empty:
                continue

            # Get technical analysis
            technical_indicators = analyzer.calculate_technical_indicators(df)

            # Get price predictions
            predictions = analyzer.predict_prices(df)

            # Calculate volatility
            volatility = df['Close'].pct_change().std() * np.sqrt(252)  # Annualized volatility

            # Calculate risk metrics
            max_drawdown = ((df['Close'].cummax() - df['Close']) / df['Close'].cummax()).max()
            sharpe_ratio = (df['Close'].pct_change().mean() * 252) / (df['Close'].pct_change().std() * np.sqrt(252))

            crypto_analysis[ticker] = {
                'technical_indicators': technical_indicators,
                'predictions': predictions,
                'risk_metrics': {
                    'volatility': volatility,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio
                }
            }

        state['crypto_analysis'] = crypto_analysis
        return state
    except Exception as e:
        logging.error(f"Error in crypto analysis: {e}")
        state['error'] = str(e)
        return state
