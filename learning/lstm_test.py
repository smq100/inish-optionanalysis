import numpy as np
import pandas as pd

from learning.lstm_base import LSTM_Base

from utils import logger


_logger = logger.get_logger()


class LSTM_Test(LSTM_Base):
    def __init__(self, ticker: str, history: pd.DataFrame, inputs: list[str], days: int):
        super().__init__(ticker, history, inputs, days)
        self._initialize()

    def _predict(self):
        prediction_scaled = self.regressor.predict(self.X_test, verbose=0)
        _logger.debug(f'{__name__}: {prediction_scaled.shape=}')

        # Perform inverse transformation to rescale back to original range
        # Since we used 5 variables for transform, the inverse expects same dimensions
        # Therefore, copy our values 5 times and discard them after inverse transform
        copy = np.repeat(prediction_scaled, self.scaled_data.shape[1], axis=-1)
        prediction_unscaled = self.scaler.inverse_transform(copy)[:,0]
        _logger.debug(f'{__name__}: {prediction_unscaled.shape=}')

        self.prediction = pd.DataFrame(prediction_unscaled)
        _logger.debug(f'{__name__}:\n{self.prediction}')
