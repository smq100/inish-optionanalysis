import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.models import Sequential
# from tensorflow.python.keras.backend import shape

from data import store as store
from utils import utils as utils

_logger = utils.get_logger()

ticker = 'FB'

data = store.get_history(ticker, 5000)

# Prepare data
scaler = MinMaxScaler(feature_range=(0,1))
scaled_data = scaler.fit_transform(data['close'].values.reshape(-1,1))

prediction_days = 60

x_train = [scaled_data[x-prediction_days:x, 0] for x in range(prediction_days, len(scaled_data))]
y_train = [scaled_data[x, 0] for x in range(prediction_days, len(scaled_data))]

x_train, y_train = np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

# Create neural net
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50 , return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50))
model.add(Dropout(0.2))
model.add(Dense(units=1))

model.compile(optimizer='adam', loss='mean_squared_error', metrics=['accuracy'])
model.fit(x_train, y_train, epochs=10, batch_size=32)

val_loss, val_acc = model.evaluate(x_train, y_train)
_logger.info(f'{val_loss = }')
_logger.info(f'{val_acc = }')

# Test
test_data = store.get_history(ticker, 1000)
actual_prices = test_data['close'].values

total_dataset = pd.concat((data['close'], test_data['close']), axis=0)

model_inputs = total_dataset[len(total_dataset) - len(test_data) - prediction_days:].values
model_inputs = model_inputs.reshape(-1, 1)
model_inputs = scaler.fit_transform(model_inputs)

x_test = [model_inputs[x-prediction_days:x, 0] for x in range(prediction_days, len(model_inputs))]
x_test = np.array(x_test)
x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

prediction_prices = model.predict(x_test)
prediction_prices = scaler.inverse_transform(prediction_prices)



if __name__ == '__main__':
    plt.plot(actual_prices, color='black', label='Actual')
    plt.plot(prediction_prices, color='green', label='Predict')
    plt.title(f'{ticker} Price Prediction')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.legend(loc='upper left')
    plt.show()
