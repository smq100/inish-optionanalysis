import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.models import Sequential

from base import Threaded
from data import store as store
from utils import utils as utils

_logger = utils.get_logger()
_prediction_days = 60
_epochs = 25
_history_train = 5000
_history_test = 1000

class Prediction(Threaded):
    def __init__(self, ticker:str):
        if store.is_symbol_valid(ticker):
            self.ticker = ticker.upper()
            self.actual_prices = []
            self.prediction_prices = []
            self._data = pd.DataFrame
            self._x_train = []
            self._y_train = []
            self._model = None
            self._scaler = None
        else:
            _logger.error(f'Error initializing {__class__}')
            raise ValueError

    def prepare(self):
        self._data = store.get_history(self.ticker, _history_train)

        self._scaler = MinMaxScaler(feature_range=(0,1))
        scaled_data = self._scaler.fit_transform(self._data['close'].values.reshape(-1,1))

        self._x_train = [scaled_data[x-_prediction_days:x, 0] for x in range(_prediction_days, len(scaled_data))]
        self._y_train = [scaled_data[x, 0] for x in range(_prediction_days, len(scaled_data))]

        self._x_train, self._y_train = np.array(self._x_train), np.array(self._y_train)
        self._x_train = np.reshape(self._x_train, (self._x_train.shape[0], self._x_train.shape[1], 1))

    def create_net(self):
        self._model = Sequential()
        self._model.add(LSTM(units=50, return_sequences=True, input_shape=(self._x_train.shape[1], 1)))
        self._model.add(Dropout(0.2))
        self._model.add(LSTM(units=50 , return_sequences=True))
        self._model.add(Dropout(0.2))
        self._model.add(LSTM(units=50))
        self._model.add(Dropout(0.2))
        self._model.add(Dense(units=1))

        self._model.compile(optimizer='adam', loss='mean_squared_error', metrics=['accuracy'])
        self._model.fit(self._x_train, self._y_train, epochs=_epochs, batch_size=32)

        val_loss, val_acc = self._model.evaluate(self._x_train, self._y_train)
        _logger.info(f'{val_loss = }')
        _logger.info(f'{val_acc = }')

    def test(self):
        test_data = self._data[-_history_test:]
        self.actual_prices = test_data['close'].values

        total_dataset = pd.concat((self._data['close'], test_data['close']), axis=0)

        model_inputs = total_dataset[len(total_dataset) - len(test_data) - _prediction_days:].values
        model_inputs = model_inputs.reshape(-1, 1)
        model_inputs = self._scaler.fit_transform(model_inputs)

        x_test = [model_inputs[x-_prediction_days:x, 0] for x in range(_prediction_days, len(model_inputs))]
        x_test = np.array(x_test)
        x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

        self.prediction_prices = self._model.predict(x_test)
        self.prediction_prices = self._scaler.inverse_transform(self.prediction_prices)

    def plot(self):
        plt.plot(self.actual_prices, color='black', label='Actual')
        plt.plot(self.prediction_prices, color='green', label='Predict')
        plt.title(f'{self.ticker} Price Prediction')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend(loc='upper left')
        plt.show()


if __name__ == '__main__':
    predict = Prediction('AAPL')
    predict.prepare()
    predict.create_net()
    predict.test()
    predict.plot()