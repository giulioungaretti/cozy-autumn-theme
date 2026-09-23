"""Synthesize the Cozy Autumn sound scheme: warm kalimba, marimba, wood and a
café-door bell. Writes 16-bit 48 kHz stereo WAVs."""
import os, sys, wave
import numpy as np

SR = 48000
OUT = sys.argv[1]
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(SR * d)) / SR


def note(n):  # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, fc):
    X = np.fft.rfft(x, n=len(x) * 2)
    f = np.fft.rfftfreq(len(x) * 2, 1 / SR)
    X *= 1 / np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X)[:len(x)]


def kalimba(f, d=1.4, v=1.0):
    t = t_(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
    y += 0.25 * np.sin(2 * np.pi * f * 5.43 * t) * np.exp(-t * 18)
    y += 0.12 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 6)
    click = rng.normal(0, 1, len(t)) * np.exp(-t * 900) * 0.15
    att = np.clip(t / 0.003, 0, 1)
    return (y * att + lowpass(click, 3000)) * v


def marimba(f, d=1.0, v=1.0):
    t = t_(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 5)
    y += 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 22)
    y += 0.1 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 60)
    att = np.clip(t / 0.002, 0, 1)
    return y * att * v


def wood(f=900, d=0.18, v=1.0):
    t = t_(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 55) + 0.5 * np.sin(2 * np.pi * f * 2.4 * t) * np.exp(-t * 90)
    n = lowpass(rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 300) * 0.6
    return (y + n) * v


def bell(f, d=2.2, v=1.0):
    t = t_(d)
    y = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1, 2.2), (2.76, 0.5, 4), (5.40, 0.28, 7), (8.93, 0.15, 11), (0.5, 0.2, 1.5)]:
        y += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 6)) * np.exp(-t * dec)
    y *= 1 + 0.08 * np.sin(2 * np.pi * 5.5 * t)
    return y * np.clip(t / 0.002, 0, 1) * v


def shop_bell(d=2.0):
    """Little brass bell over a café door, jingling a few times."""
    out = np.zeros(int(SR * d))
    for k, (dt, v) in enumerate([(0, 1), (0.09, 0.7), (0.2, 0.5), (0.33, 0.35), (0.5, 0.2)]):
        s = bell(note(93) * rng.uniform(0.995, 1.005), d - dt, v)
        i = int(dt * SR)
        out[i:i + len(s)] += s[:len(out) - i]
    return out


def leaves(d=1.1):
    """Crunchy leaf pile."""
    out = np.zeros(int(SR * d))
    for _ in range(420):
        pos = rng.random() ** 1.8 * (d - 0.05)
        L = int(SR * rng.uniform(0.001, 0.008))
        g = rng.normal(0, 1, L) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.2, 1)
        i = int(pos * SR)
        out[i:i + L] += g
    out = np.diff(out, prepend=0) * 0.6 + out * 0.4
    out = lowpass(out, 7000)
    env = np.minimum(1, t_(d) / 0.02) * np.exp(-t_(d) * 2.2)
    return out * env


def seq(parts, d=None):
    L = max(int(s * SR) + len(x) for s, x in parts)
    out = np.zeros(L if d is None else int(d * SR))
    for s, x in parts:
        i = int(s * SR)
        n = min(len(x), len(out) - i)
        out[i:i + n] += x[:n]
    return out


def reverb(x, wet=0.22, decay=1.1):
    L = int(SR * decay)
    tt = np.arange(L) / SR
    ir = rng.normal(0, 1, L) * np.exp(-tt * 5.5 / decay)
    ir = lowpass(ir, 4000)
    ir /= np.sqrt(np.sum(ir ** 2))
    n = len(x) + L
    wetsig = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    dry = np.concatenate([x, np.zeros(L)])
    y = dry + wet * wetsig
    # trim trailing silence
    thr = np.max(np.abs(y)) * 0.002
    last = np.nonzero(np.abs(y) > thr)[0][-1] + int(0.05 * SR)
    return y[:last]


def save(name, x, peak_db=-5.0, wet=0.22):
    x = reverb(x, wet)
    fade = min(len(x), int(0.04 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)
    x = x / np.max(np.abs(x)) * 10 ** (peak_db / 20)
    # gentle stereo width via tiny delay
    d = int(0.0007 * SR)
    left = x
    right = np.concatenate([np.zeros(d), x[:-d]]) * 0.97 + x * 0.03
    st = np.stack([left, right], 1)
    pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


os.makedirs(OUT, exist_ok=True)
# E major pentatonic-ish, warm register
E4, Gs4, B4, Cs5, E5, Fs5, Gs5, B5 = (note(n) for n in (64, 68, 71, 73, 76, 78, 80, 83))

save('Default', seq([(0, wood(700, v=0.6)), (0.01, kalimba(B4, 0.9))]))
save('Notify', seq([(0, kalimba(E5, 1.2)), (0.11, kalimba(B5, 1.3, 0.8))]))
save('Message', seq([(0, marimba(Gs5, 0.8)), (0.09, marimba(B5, 1.0, 0.8))]))
save('Mail', seq([(0, marimba(E5)), (0.1, marimba(Gs5, v=0.9)), (0.2, marimba(B5, 1.2, 0.8))]))
save('Reminder', shop_bell())
save('Asterisk', seq([(0, kalimba(Gs4, 1.3)), (0, kalimba(Gs5, 1.0, 0.35))]))
save('Question', seq([(0, kalimba(B4, 1.0, 0.9)), (0.14, kalimba(E5, 1.2))]))
save('Exclamation', seq([(0, wood(820, v=0.7)), (0.02, marimba(Cs5)), (0.16, marimba(Gs4, 1.2))]))
save('Critical', seq([(0, wood(420, 0.25)), (0.12, wood(360, 0.3, 0.9)), (0.12, marimba(note(52), 1.4, 0.9)),
                      (0.12, marimba(note(55), 1.4, 0.5))]))
save('DeviceConnect', seq([(0, kalimba(B4, 0.8, 0.8)), (0.1, kalimba(E5, 1.1))]))
save('DeviceDisconnect', seq([(0, kalimba(E5, 0.8, 0.8)), (0.1, kalimba(B4, 1.1))]))
save('DeviceFail', seq([(0, wood(380, 0.25)), (0.14, wood(330, 0.3))]), peak_db=-7)
save('RecycleBin', leaves(), peak_db=-7, wet=0.1)
save('Navigate', wood(1100, 0.1, 0.8), peak_db=-16, wet=0.05)
save('UAC', seq([(0, bell(note(81), 1.8, 0.7)), (0.18, bell(note(88), 2.0, 0.5))]), peak_db=-6)
save('Logon', seq([(0, kalimba(E4, 2.0)), (0.12, kalimba(Gs4, 2.0)), (0.24, kalimba(B4, 2.0)),
                   (0.36, kalimba(E5, 2.2)), (0.5, bell(note(88), 2.4, 0.35))]), wet=0.3)
save('Logoff', seq([(0, kalimba(E5, 1.8)), (0.14, kalimba(B4, 1.8)), (0.28, kalimba(Gs4, 1.8)),
                    (0.42, kalimba(E4, 2.2))]), wet=0.3)
save('BatteryLow', seq([(0, marimba(Gs4, 1.0)), (0.2, marimba(E4, 1.2))]))
save('BatteryCritical', seq([(0, marimba(Gs4)), (0.16, marimba(E4)), (0.32, marimba(note(59), 1.4))]))
save('PrintComplete', seq([(0, marimba(B4, 0.8)), (0.1, marimba(E5, 1.0))]))
print('ok')
