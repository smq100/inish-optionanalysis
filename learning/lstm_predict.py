import numpy as np
import pandas as pd

from learning.lstm_base import LSTM_Base

from utils import logger


_logger = logger.get_logger()


class LSTM_Predict(LSTM_Base):
    def __init__(self, ticker: str, history: pd.DataFrame, inputs: list[str], days: int):
        super().__init__(ticker, history, inputs, days)

        # Look ahread for more than 1 day
        self.lookahead = 10

        self._initialize()

    def _predict(self):
        prediction_scaled = self.regressor.predict(self.X_test, verbose=0)
        _logger.debug(f'{__name__}: {prediction_scaled.shape=}')

        # Perform manual inverse transformation of price (last column)
        prediction_unscaled = prediction_scaled
        prediction_unscaled -= self.scaler.min_[-1]
        prediction_unscaled /= self.scaler.scale_[-1]
        _logger.debug(f'{__name__}: {prediction_unscaled.shape=}')

        # Reshape to allow shifting along X
        padding = np.empty((prediction_unscaled.shape[0], self.X_test.shape[0]-1))
        padding[:] = np.nan
        _logger.debug(f'{__name__}: {padding.shape=}')

        prediction = np.concatenate((prediction_unscaled, padding), axis=1)
        _logger.debug(f'{__name__}: {prediction.shape=}')

        # Create df shifting results to their X locations
        self.prediction = pd.DataFrame(prediction)
        for n in range(len(self.prediction)):
            sr = self.prediction.iloc[n]
            self.prediction.loc[n] = sr.shift(n)

        _logger.debug(f'{__name__}:\n{self.prediction}')
