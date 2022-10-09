import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Supress TensorFlow complier flag warning

from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, Callback
from keras.layers import Dense, LSTM, Dropout
from keras import Sequential
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
from dataclasses import dataclass
from abc import ABC
import abc

from utils import logger
from data import store as store
from base import Threaded


_logger = logger.get_logger()


@dataclass
class Parameters:
    PCT_TRAINING: float = 0.15
    PCT_VALIDATION: float = 0.15
    NEURONS: int = 50
    DROPOUT: float = 0.20
    EPOCHS: int = 20
    BATCH_SIZE: int = 32
    CACHE_FILE: str = './cache/model.h5'


class LSTM_Base(ABC, Threaded):
    def __init__(self, ticker: str, history: pd.DataFrame, inputs: list[str], days: int):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if history.empty:
            raise ValueError('Empty history')
        if not inputs:
            raise ValueError('Empty imputs')
        if days < 30:
            raise ValueError('Days must be more than 30')

        self.ticker = ticker.upper()
        self.history: pd.DataFrame = history
        self.inputs: list[str] = inputs
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
        self.parameters: Parameters = Parameters()

    def _initialize(self):
        _logger.debug(f'{__name__}:\n{self.history}')

        self.input_size = len(self.inputs)
        input_data = self.history[self.inputs].values

        # Normalize to values bwtween 0-1
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.scaled_data = self.scaler.fit_transform(input_data)

        # Build data
        X = []
        y = []
        history_size = len(self.history)

        for i in range(0, history_size-self.lookback-self.lookahead):
            lb = []
            for j in range(0, self.lookback):
                lb.append(self.scaled_data[i+j, :])

            la = []
            for j in range(0, self.lookahead):
                la.append(self.scaled_data[self.lookback+i+j, -1])

            X.append(lb)
            y.append(la)

        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)

        _logger.debug(f'{__name__}: {X.shape=}')
        _logger.debug(f'{__name__}: {y.shape=}')

        # Create testing, training, and validation arrays
        self.test_size = int(history_size * self.parameters.PCT_TRAINING)

        self.X_test = X[-self.test_size:]
        self.y_test = y[-self.test_size:]
        X_rest = X[:-self.test_size]
        y_rest = y[:-self.test_size]

        self.X_train, self.X_valid, self.y_train, self.y_valid = train_test_split(X_rest, y_rest, test_size=self.parameters.PCT_VALIDATION, random_state=101)

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
        self.regressor.add(LSTM(units=self.parameters.NEURONS, return_sequences=True, input_shape=(self.X_train.shape[1], self.input_size)))
        self.regressor.add(Dropout(rate=self.parameters.DROPOUT))

        # Add 2nd lstm layer
        self.regressor.add(LSTM(units=self.parameters.NEURONS, return_sequences=True))
        self.regressor.add(Dropout(rate=self.parameters.DROPOUT))

        # Add 3rd lstm layer
        self.regressor.add(LSTM(units=self.parameters.NEURONS, return_sequences=True))
        self.regressor.add(Dropout(rate=self.parameters.DROPOUT))

        # Add 4th lstm layer
        self.regressor.add(LSTM(units=self.parameters.NEURONS, return_sequences=False))
        self.regressor.add(Dropout(rate=self.parameters.DROPOUT))

        # Add output layer
        self.regressor.add(Dense(units=self.lookahead))

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
            ModelCheckpoint(self.parameters.CACHE_FILE, verbose=1, save_best_only=True, save_weights_only=True),
            KerasCallback(self)
        ]

        # Fit the model
        self.regressor.fit(self.X_train, self.y_train, epochs=self.parameters.EPOCHS, batch_size=self.parameters.BATCH_SIZE,
                           validation_data=(self.X_valid, self.y_valid), callbacks=callbacks, verbose=0)

        self.results = self.regressor.evaluate(self.X_test, self.y_test, batch_size=self.parameters.BATCH_SIZE)

        _logger.debug(f'{__name__}: Test MSE: {self.results[0]}')  # Mean Square Error
        _logger.debug(f'{__name__}: Test MAE: {self.results[1]}')  # Mean Absolute Error

    @abc.abstractmethod
    def _predict(self):
        raise NotImplementedError


class KerasCallback(Callback):
    def __init__(self, outer: LSTM_Base):
        self.outer: LSTM_Base = outer
        self.outer.task_total = self.outer.parameters.EPOCHS

    def on_epoch_begin(self, epoch, logs=None):
        if logs:
            _logger.debug(f'{__name__}: {logs}')

    def on_epoch_end(self, epoch, logs=None):
        self.outer.task_success += 1
        self.outer.task_completed += 1
        if logs:
            _logger.debug(f'{__name__}: {logs}')
