import numpy as np

def calculate_indicators(history):
    """
    history: [{'close': 100, 'volume': 10, ...}, ...] 리스트
    Pandas 의존성을 줄이고 NumPy만 사용하여 계산 (32bit 환경 호환성)
    """
    if len(history) < 2:
        return [0.0] * 14

    closes = np.array([h['close'] for h in history])
    
    # 1. MACD (간이 EMA 구현)
    def get_ema(values, span):
        alpha = 2 / (span + 1)
        ema = [values[0]]
        for v in values[1:]:
            ema.append(ema[-1] + alpha * (v - ema[-1]))
        return np.array(ema)

    ema12 = get_ema(closes, 12)
    ema26 = get_ema(closes, 26)
    macd = ema12[-1] - ema26[-1]
    
    # 2-3. Bollinger Bands
    window = min(len(closes), 20)
    sma20 = np.mean(closes[-window:])
    std20 = np.std(closes[-window:])
    boll_ub = sma20 + (std20 * 2)
    boll_lb = sma20 - (std20 * 2)
    
    # 4. RSI
    diffs = np.diff(closes)
    window_rsi = min(len(diffs), 14)
    if window_rsi > 0:
        gains = np.where(diffs[-window_rsi:] > 0, diffs[-window_rsi:], 0)
        losses = np.where(diffs[-window_rsi:] < 0, -diffs[-window_rsi:], 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50.0
    
    # 5-8. SMA 및 기타 (CCI, DX 간이 대용)
    sma30 = np.mean(closes[-min(len(closes), 30):])
    sma60 = np.mean(closes[-min(len(closes), 60):])
    cci = (closes[-1] - sma20) / (0.015 * std20 + 1e-9)
    dx = rsi # DX는 계산 복잡성으로 RSI로 대치 또는 패딩
    
    finrl_indicators = [
        float(macd), float(boll_ub), float(boll_lb), float(rsi),
        float(cci), float(dx), float(sma30), float(sma60)
    ]
    
    # 9-14. 수급 지표 (최근 평균)
    def get_supply_avg(key, n):
        vals = [h[key] for h in history[-min(len(history), n):]]
        return float(np.mean(vals))

    supply_indicators = [
        float(history[-1]['foreigner']),
        float(history[-1]['institution']),
        float(history[-1]['individual']),
        get_supply_avg('foreigner', 5),
        get_supply_avg('institution', 5),
        get_supply_avg('individual', 5)
    ]
    
    return finrl_indicators + supply_indicators
