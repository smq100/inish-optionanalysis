import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras import Sequential
from keras.layers import Dense, LSTM, Dropout
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

from base import Threaded
from data import store as store
from utils import cache, logger


_logger = logger.get_logger()

class Learning(Threaded):
    def __init__(self, ticker: str, days: int = 1000):
        if days < 30:
            raise ValueError('Days must be larger than 30')

        self.ticker = ticker.upper()
        self.days = days
        self.lookback = 60
        self.lookahead = 10

        self.history = store.get_history(self.ticker, days=self.days)

        # Drop date column and move close column to the end as the target, then convert to numpy
        input_data = self.history[['open', 'high', 'low', 'volume', 'close']].values

        # Normalize to values bwtween 0-1
        self.scaler = MinMaxScaler(feature_range=(0,1))
        input_data = self.scaler.fit_transform(input_data)

        # Build data
        total_size = len(self.history)
        X=[]
        y=[]
        for i in range(0, total_size-self.lookback-self.lookahead):
            lb=[]
            for j in range(0, self.lookback):
                lb += [input_data[i+j, :]]

            la=[]
            for j in range(0, self.lookahead):
                la += [input_data[self.lookback+i+j, -1]]

            X += [lb]
            y += [la]

        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)

        _logger.debug(f'{__name__}: {X.shape=}')
        _logger.debug(f'{__name__}: {y.shape=}')

        # 15% of the data for testing
        # 85% of the rest for training
        # 15% of the rest for validation
        self.test_size = int(total_size * 0.15)

        self.X_test = X[-self.test_size:, :]
        self.y_test = y[-self.test_size:, :]
        X_rest = X[:-self.test_size, :]
        y_rest = y[:-self.test_size, :]
        self.X_train, self.X_valid, self.y_train, self.y_valid = train_test_split(X_rest, y_rest, test_size=0.15, random_state=101)

        # Reshape to be friendly to LSTM model
        self.X_train = self.X_train.reshape(self.X_train.shape[0], self.lookback, 5)
        self.X_valid = self.X_valid.reshape(self.X_valid.shape[0], self.lookback, 5)
        self.X_test = self.X_test.reshape(self.X_test.shape[0], self.lookback, 5)

        _logger.debug(f'{__name__}: {self.X_train.shape=}')
        _logger.debug(f'{__name__}: {self.X_valid.shape=}')
        _logger.debug(f'{__name__}: {self.y_train.shape=}')
        _logger.debug(f'{__name__}: {self.y_valid.shape=}')
        _logger.debug(f'{__name__}: {self.X_test.shape=}')

    def run(self):
        self._create_model()
        self._compile_and_fit()
        self._predict()
        self._plot()

    def _create_model(self):
        # Create model
        self.regressor = Sequential()

        # Add 1st lstm layer: 50 neurons
        self.regressor.add(LSTM(units = 50, return_sequences = True, input_shape = (self.X_train.shape[1], 5)))
        self.regressor.add(Dropout(rate = 0.2))

        # Add 2nd lstm layer
        self.regressor.add(LSTM(units = 50, return_sequences = True))
        self.regressor.add(Dropout(rate = 0.2))

        # Add 3rd lstm layer
        self.regressor.add(LSTM(units = 50, return_sequences = True))
        self.regressor.add(Dropout(rate = 0.2))

        # Add 4th lstm layer
        self.regressor.add(LSTM(units = 50, return_sequences = False))
        self.regressor.add(Dropout(rate = 0.2))

        # Add output layer
        self.regressor.add(Dense(units = self.lookahead))

    def _compile_and_fit(self):
        self.regressor.compile(optimizer='adam', loss='mean_squared_error', metrics=['accuracy'])

        # EarlyStoping: It will stop the traning if score of model didn't increase.
        #               This prevent model from overfitting. We are to set max in 10 epoches
        #               if it didn't increase then we will stop the training
        # ReduceLROnPlateau: Use for reduce the learning rate. If in 3 steps the score
        #               didn't increase we will reduce the learning rate to improve the training
        # ModelCheckpoint: Use for save model only when the score increased
        callbacks = [
            EarlyStopping(patience=10, verbose=1),
            ReduceLROnPlateau(factor=0.1, patience=3, min_lr=0.00001, verbose=1),
            ModelCheckpoint('model.h5', verbose=1, save_best_only=True, save_weights_only=True)
        ]

        # Fit the model
        self.regressor.fit(self.X_train, self.y_train, epochs=10, batch_size=8, validation_data=(self.X_valid, self.y_valid), callbacks=callbacks)

        results = self.regressor.evaluate(self.X_test, self.y_test, batch_size=8)

        _logger.debug(f'{__name__}: Test MSE: {results[0]}') # Mean Square Error
        _logger.debug(f'{__name__}: Test MAE: {results[1]}') # Mean Absolute Error

    def _predict(self):
        prediction_scaled = self.regressor.predict(self.X_test)

        # Perform manual inverse transformation of price (last column)
        prediction_unscaled = prediction_scaled
        prediction_unscaled -= self.scaler.min_[-1]
        prediction_unscaled /= self.scaler.scale_[-1]

        # Reshape to allow shifting along X
        padding = np.empty((prediction_unscaled.shape[0], self.X_test.shape[0]-1))
        padding[:] = np.nan
        prediction = np.concatenate((prediction_unscaled, padding), axis=1)

        _logger.debug(f'{__name__}: {prediction_unscaled.shape=}')
        _logger.debug(f'{__name__}: {padding.shape=}')
        _logger.debug(f'{__name__}: {prediction.shape=}')

        # Create df shifting results to their X locations
        self.prediction_df = pd.DataFrame(prediction)
        for n in range(len(self.prediction_df)):
            sr = self.prediction_df.iloc[n]
            self.prediction_df.loc[n] = sr.shift(n)

        _logger.debug(f'{__name__}:\n{self.prediction_df}')

    def _plot(self):
        real_data = self.history[-self.test_size:].reset_index()
        plots = [row for row in self.prediction_df.itertuples(index=False)]

        plt.figure(figsize=(18, 8))
        for item in plots:
            plt.plot(item, color= 'green')

        plt.plot(real_data['close'], color='grey')
        plt.title('Close')
        plt.show()
