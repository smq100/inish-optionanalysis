import matplotlib.pyplot as plt

from data import store as store
from utils import ui


def price_history(ticker: str, show: bool = False) -> plt.Figure:
    plt.style.use(ui.CHART_STYLE)
    figure, ax1 = plt.subplots(figsize=(17, 10))

    plt.grid()
    plt.margins(x=0.1)

    figure.canvas.manager.set_window_title(f'{ticker.upper()}')

    ax1.secondary_yaxis('right')

    history = store.get_history(ticker, 1000)
    company = store.get_company(ticker)

    plt.title(f'{company["name"]}')

    if history.iloc[-1]['close'] < 30.0:
        ax1.yaxis.set_major_formatter('{x:.2f}')
    else:
        ax1.yaxis.set_major_formatter('{x:.0f}')

    # Highs & Lows
    length = len(history)
    dates = [history.iloc[index]['date'].strftime(ui.DATE_FORMAT) for index in range(length)]

    plt.xticks(range(0, length+1, int(length/12)))
    plt.xticks(rotation=45)
    plt.subplots_adjust(bottom=0.15)

    ax1.plot(dates, history['high'], '-g', linewidth=0.5)
    ax1.plot(dates, history['low'], '-r', linewidth=0.5)
    ax1.fill_between(dates, history['high'], history['low'], facecolor='gray', alpha=0.4)

    if show:
        plt.figure(figure)
        plt.show()

    return figure


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    logger.get_logger(logging.DEBUG)

    if len(sys.argv) > 1:
        figure = price_history(sys.argv[1], True)
    else:
        figure = price_history('aapl', True)
