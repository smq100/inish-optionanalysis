import os

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# Supress TF complier flag warning
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from keras import Sequential
from keras.layers import Dense, LSTM, Dropout
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, Callback

from base import Threaded
from data import store as store
from utils import logger


PCT_TRAINING = 0.15
PCT_VALIDATION = 0.15
NEURONS = 50
DROPOUT = 0.20
EPOCHS = 10
BATCH_SIZE = 8
CACHE_FILE = './cache/model.h5'


_logger = logger.get_logger()


class KerasCallback(Callback):
    def __init__(self, outer):
        self.outer: LSTM_Test = outer
        self.outer.task_total = EPOCHS

    def on_epoch_begin(self, epoch, logs=None):
        if logs:
            _logger.debug(f'{__name__}: {logs}')

    def on_epoch_end(self, epoch, logs=None):
        self.outer.task_success += 1
        self.outer.task_completed += 1
        if logs:
            _logger.debug(f'{__name__}: {logs}')


class LSTM_Test(Threaded):
    def __init__(self, ticker: str, days: int):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if days < 30:
            raise ValueError('Days must be more than 30')

        self.ticker = ticker.upper()
        self.days = days
        self.lookback = 60
        self.lookahead = 1
        self.test_size: int
        self.input_size: int
        self.X_test: np.array
        self.y_test: np.array
        self.X_train: np.array
        self.y_train: np.array
        self.X_valid: np.array
        self.y_valid: np.array
        self.scaled_data: np.array
        self.scaler: MinMaxScaler
        self.regressor: Sequential
        self.prediction: pd.DataFrame
        self.results: list[float]

        self.history = store.get_history(self.ticker, days=self.days)
        _logger.debug(f'{__name__}:\n{self.history}')

        # Drop date column and move close column to the end as the target, then convert to numpy
        inputs = ['open', 'high', 'low', 'volume', 'close']
        self.input_size = len(inputs)
        input_data = self.history[inputs].values

        # Normalize to values bwtween 0-1
        self.scaler = MinMaxScaler(feature_range=(0,1))
        self.scaled_data = self.scaler.fit_transform(input_data)
        _logger.debug(f'{__name__}: {self.scaled_data[0]=}')
        _logger.debug(f'{__name__}: {self.scaled_data[-1]=}')

        # Build data
        X = []
        y = []
        history_size = len(self.history)

        for i in range(0, history_size-self.lookback-self.lookahead):
            lb = []
            for j in range(0, self.lookback):
                lb += [self.scaled_data[i+j, :]]

            la = []
            for j in range(0, self.lookahead):
                la += [self.scaled_data[self.lookback+i+j, -1]]

            X += [lb]
            y += [la]

        _logger.debug(f'{__name__}: {X[0][0]=}')

        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)

        _logger.debug(f'{__name__}: {X.shape=}')
        _logger.debug(f'{__name__}: {y.shape=}')

        # Create testing, training, and validation arrays
        self.test_size = int(history_size * PCT_TRAINING)

        self.X_test = X[-self.test_size:]
        self.y_test = y[-self.test_size:]
        X_rest = X[:-self.test_size]
        y_rest = y[:-self.test_size]

        self.X_train, self.X_valid, self.y_train, self.y_valid = train_test_split(X_rest, y_rest, test_size=PCT_VALIDATION, random_state=101)

        # Reshape to be friendly to LSTM model
        self.X_train = self.X_train.reshape(self.X_train.shape[0], self.lookback, self.input_size)
        self.X_valid = self.X_valid.reshape(self.X_valid.shape[0], self.lookback, self.input_size)
        self.X_test = self.X_test.reshape(self.X_test.shape[0], self.lookback, self.input_size)

        _logger.debug(f'{__name__}: {self.X_train.shape=}')
        _logger.debug(f'{__name__}: {self.X_valid.shape=}')
        _logger.debug(f'{__name__}: {self.X_test.shape=}')
        _logger.debug(f'{__name__}: {self.y_train.shape=}')
        _logger.debug(f'{__name__}: {self.y_valid.shape=}')

    @Threaded.threaded
    def run(self):
        self._create_model()
        self._compile_and_fit()
        self._predict()

    def _create_model(self):
        # Create model
        self.regressor = Sequential()

        # Add 1st lstm layer
        self.regressor.add(LSTM(units=NEURONS, return_sequences=True, input_shape=(self.X_train.shape[1], self.input_size)))
        self.regressor.add(Dropout(rate = DROPOUT))

        # Add 2nd lstm layer
        self.regressor.add(LSTM(units=NEURONS, return_sequences=True))
        self.regressor.add(Dropout(rate=DROPOUT))

        # Add 3rd lstm layer
        self.regressor.add(LSTM(units=NEURONS, return_sequences=True))
        self.regressor.add(Dropout(rate=DROPOUT))

        # Add 4th lstm layer
        self.regressor.add(LSTM(units=NEURONS, return_sequences=False))
        self.regressor.add(Dropout(rate=DROPOUT))

        # Add output layer
        self.regressor.add(Dense(units=self.lookahead))

        _logger.debug(f'{__name__}:\n{self.regressor.summary()}')

    def _compile_and_fit(self):
        self.regressor.compile(optimizer='adam', loss='mean_squared_error', metrics=['accuracy'])

        # EarlyStoping: It will stop the traning if score of model didn't increase.
        #               This prevent model from overfitting. We are to set max in 10 epoches
        #               if it didn't increase then we will stop the training
        # ReduceLROnPlateau: Use for reduce the learning rate. If in 3 steps the score
        #               didn't increase we will reduce the learning rate to improve the training
        # ModelCheckpoint: Use for save model only when the score increased
        # KerasCallback: Local callback for tracking progress

        callbacks = [
            EarlyStopping(patience=10, verbose=1),
            ReduceLROnPlateau(factor=0.1, patience=3, min_lr=0.00001, verbose=1),
            ModelCheckpoint(CACHE_FILE, verbose=1, save_best_only=True, save_weights_only=True),
            KerasCallback(self)
        ]

        # Fit the model
        self.regressor.fit(self.X_train, self.y_train, epochs=EPOCHS, batch_size=BATCH_SIZE,
            validation_data=(self.X_valid, self.y_valid), callbacks=callbacks, verbose=0)

        self.results = self.regressor.evaluate(self.X_test, self.y_test, batch_size=BATCH_SIZE)

        _logger.debug(f'{__name__}: Test MSE: {self.results[0]}') # Mean Square Error
        _logger.debug(f'{__name__}: Test MAE: {self.results[1]}') # Mean Absolute Error

    def _predict(self):
        prediction_scaled = self.regressor.predict(self.X_test, verbose=0)

        # Perform inverse transformation to rescale back to original range
        # Since we used 5 variables for transform, the inverse expects same dimensions
        # Therefore, let us copy our values 5 times and discard them after inverse transform
        copy = np.repeat(prediction_scaled, self.scaled_data.shape[1], axis=-1)
        prediction_unscaled = self.scaler.inverse_transform(copy)[:,0]
        self.prediction = pd.DataFrame(prediction_unscaled)

        _logger.debug(f'{__name__}: {prediction_scaled.shape=}')
        _logger.debug(f'{__name__}: {prediction_unscaled.shape=}')
        _logger.debug(f'{__name__}: {self.prediction.shape=}')
        _logger.debug(f'{__name__}:\n{self.prediction}')

# %%
