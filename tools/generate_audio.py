"""
tools/generate_audio.py  (فاز ۱۰)

تولید فایل‌های صوتی واقعی بازی (۱۴ افکت + ۲ موسیقی‌ی حلقه‌ای) با سنتز رویه‌ای.
قبلاً پوشه‌ی assets/audio خالی بود و بازی کاملاً بی‌صدا بود.

* سنتز: فقط کتابخانه‌ی استاندارد پایتون (math, random با seed ثابت, struct, wave).
* کدگذاری OGG/Vorbis: با ffmpeg (فقط ابزار زمان توسعه؛ فایل‌های خروجی commit می‌شن،
  پس CI/بیلد به ffmpeg نیاز ندارد).
* نام فایل‌ها دقیقاً از core/audio_manager.py (SFX_VARIANTS / MUSIC_TRACKS) گرفته می‌شود.

اجرا:  python tools/generate_audio.py [--out assets/audio] [--wav-only]
"""
import argparse
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SR = 22050
TWO_PI = 2.0 * math.pi


# ---------- ابزارهای سنتز ----------

def _env(i, n, attack=0.005, release=0.5):
    """پوش ساده: حمله‌ی کوتاه + افت نمایی. i اندیس نمونه، n طول."""
    t = i / SR
    a = min(1.0, t / attack) if attack > 0 else 1.0
    decay = math.exp(-5.0 * (i / n))
    tail = min(1.0, (n - i) / (SR * 0.004))  # ۴ms آخر -> صفر (بدون click)
    return a * decay * tail


def tone(freq, dur, wave_kind='sine', amp=1.0, f_end=None, attack=0.004, decay_rate=5.0, noise=0.0, rng=None):
    n = max(1, int(dur * SR))
    out = []
    phase = 0.0
    rng = rng or random.Random(1)
    for i in range(n):
        frac = i / n
        f = freq if f_end is None else freq + (f_end - freq) * frac
        phase += TWO_PI * f / SR
        if wave_kind == 'sine':
            v = math.sin(phase)
        elif wave_kind == 'square':
            v = 1.0 if math.sin(phase) >= 0 else -1.0
            v *= 0.6
        elif wave_kind == 'saw':
            v = 2.0 * ((phase / TWO_PI) % 1.0) - 1.0
            v *= 0.7
        else:  # tri
            v = 2.0 * abs(2.0 * ((phase / TWO_PI) % 1.0) - 1.0) - 1.0
        if noise:
            v = v * (1.0 - noise) + (rng.random() * 2 - 1) * noise
        t = i / SR
        a = min(1.0, t / attack) if attack > 0 else 1.0
        e = a * math.exp(-decay_rate * frac) * min(1.0, (n - i) / (SR * 0.004))
        out.append(v * e * amp)
    return out


def noise_burst(dur, amp=1.0, lowpass=0.2, decay_rate=6.0, rng=None):
    rng = rng or random.Random(2)
    n = max(1, int(dur * SR))
    out = []
    y = 0.0
    for i in range(n):
        x = rng.random() * 2 - 1
        y += lowpass * (x - y)
        frac = i / n
        e = math.exp(-decay_rate * frac) * min(1.0, (n - i) / (SR * 0.004))
        out.append(y * e * amp * 2.5)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def concat(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def silence(dur):
    return [0.0] * int(dur * SR)


def place(track, at, base_len=None):
    """track را از زمان at (ثانیه) شروع می‌کند."""
    return silence(at) + track


def normalize(samples, peak=0.85):
    m = max((abs(v) for v in samples), default=0.0)
    if m <= 1e-9:
        return samples
    k = peak / m
    return [v * k for v in samples]


def note(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    if name[1] in '#b':
        key, octave = name[:2], int(name[2:])
    else:
        key, octave = name[0], int(name[1:])
    semitone = names[key] + 12 * (octave + 1)
    return 440.0 * 2 ** ((semitone - 69) / 12.0)


# ---------- افکت‌ها ----------

def sfx_shot_fire(variant):
    rng = random.Random(10 + variant)
    f0, f1 = (1800, 260) if variant == 1 else (1500, 200)
    sweep = tone(f0, 0.20, 'saw', 0.55, f_end=f1, decay_rate=4.0)
    zap = tone(f0 * 0.5, 0.20, 'sine', 0.5, f_end=f1 * 0.5, decay_rate=5.0)
    hiss = noise_burst(0.08, 0.3, lowpass=0.5, rng=rng)
    return mix(sweep, zap, hiss)


def sfx_mirror_hit(variant):
    f = {1: 1200.0, 2: 1500.0, 3: 1800.0}[variant]
    a = tone(f, 0.16, 'sine', 0.8, decay_rate=7.0)
    b = tone(f * 2.01, 0.10, 'sine', 0.35, decay_rate=9.0)
    c = tone(f * 3.0, 0.05, 'sine', 0.15, decay_rate=10.0)
    return mix(a, b, c)


def sfx_target_destroy(variant):
    rng = random.Random(30 + variant)
    boom = noise_burst(0.35, 0.9, lowpass=0.12 if variant == 1 else 0.18, decay_rate=5.0, rng=rng)
    pitch = tone(700 if variant == 1 else 900, 0.30, 'tri', 0.6, f_end=110, decay_rate=4.0)
    sparkle = tone(2400, 0.08, 'sine', 0.25, f_end=1200, decay_rate=8.0)
    return mix(boom, pitch, sparkle)


def sfx_obstacle_hit():
    rng = random.Random(40)
    thud = tone(110, 0.22, 'sine', 1.0, f_end=60, decay_rate=5.5)
    crack = noise_burst(0.10, 0.6, lowpass=0.35, decay_rate=9.0, rng=rng)
    return mix(thud, crack)


def sfx_level_win():
    seq = ['C5', 'E5', 'G5', 'C6']
    parts = []
    for i, nm in enumerate(seq):
        dur = 0.14 if i < 3 else 0.45
        t = tone(note(nm), dur, 'tri', 0.7, decay_rate=2.5 if i == 3 else 4.0)
        t2 = tone(note(nm) * 2, dur, 'sine', 0.2, decay_rate=4.0)
        parts.append(place(mix(t, t2), i * 0.12))
    return mix(*parts)


def sfx_level_lose():
    seq = ['E4', 'D#4', 'D4', 'A3']
    parts = []
    for i, nm in enumerate(seq):
        dur = 0.18 if i < 3 else 0.5
        parts.append(place(tone(note(nm), dur, 'saw', 0.5, decay_rate=3.5 if i == 3 else 5.0), i * 0.16))
    return mix(*parts)


def sfx_low_time_warning():
    beep = tone(880, 0.10, 'square', 0.5, decay_rate=1.5)
    return mix(beep, place(beep, 0.18))


def sfx_button_tap():
    return mix(tone(1000, 0.045, 'sine', 0.8, decay_rate=6.0),
               tone(1500, 0.03, 'sine', 0.25, decay_rate=8.0))


def sfx_purchase():
    a = tone(note('E6'), 0.09, 'sine', 0.7, decay_rate=3.0)
    b = tone(note('A6'), 0.30, 'sine', 0.7, decay_rate=3.5)
    sh = tone(note('A7'), 0.12, 'sine', 0.2, decay_rate=7.0)
    return mix(a, place(b, 0.07), place(sh, 0.07))


# ---------- موسیقی (حلقه‌ای؛ همه‌ی نت‌ها داخل میزان خودشان محو می‌شوند => بدون click) ----------

def _pad_note(freq, dur, amp):
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        x = i / n
        env = min(1.0, t / 0.08) * (1.0 - x ** 6) * min(1.0, (n - i) / (SR * 0.01))
        v = (math.sin(TWO_PI * freq * t) + 0.5 * math.sin(TWO_PI * freq * 2.0 * t + 0.4)
             + 0.25 * math.sin(TWO_PI * freq * 3.0 * t)) / 1.75
        out.append(v * env * amp)
    return out


def _pluck(freq, dur, amp):
    return tone(freq, dur, 'tri', amp, decay_rate=5.5, attack=0.003)


def _bass(freq, dur, amp):
    return tone(freq, dur, 'sine', amp, decay_rate=3.0, attack=0.004)


def _add_at(buf, track, at):
    start = int(at * SR)
    end = start + len(track)
    if end > len(buf):
        track = track[:len(buf) - start]
    for i, v in enumerate(track):
        buf[start + i] += v


def music_menu():
    bpm = 84.0
    beat = 60.0 / bpm
    bar = 4 * beat
    chords = [('A3', 'C4', 'E4'), ('F3', 'A3', 'C4'), ('C3', 'E3', 'G3'), ('G3', 'B3', 'D4')] * 2
    arp = [['A4', 'C5', 'E5', 'C5'], ['F4', 'A4', 'C5', 'A4'], ['C5', 'E5', 'G5', 'E5'], ['B4', 'D5', 'G5', 'D5']] * 2
    roots = ['A2', 'F2', 'C2', 'G2'] * 2
    total = bar * len(chords)
    buf = [0.0] * int(total * SR)
    for b, chord in enumerate(chords):
        t0 = b * bar
        for nm in chord:
            _add_at(buf, _pad_note(note(nm), bar * 0.96, 0.17), t0)
        _add_at(buf, _bass(note(roots[b]), bar * 0.9, 0.45), t0)
        for k, nm in enumerate(arp[b]):
            _add_at(buf, _pluck(note(nm), beat * 0.95, 0.22), t0 + k * beat)
            _add_at(buf, _pluck(note(nm) * 2.0, beat * 0.45, 0.07), t0 + k * beat + beat * 0.5)
    return normalize(buf, 0.6)


def music_gameplay():
    bpm = 118.0
    beat = 60.0 / bpm
    bar = 4 * beat
    prog = [('A2', ['A4', 'C5', 'E5', 'A5']), ('F2', ['F4', 'A4', 'C5', 'F5']),
            ('C3', ['G4', 'C5', 'E5', 'G5']), ('G2', ['G4', 'B4', 'D5', 'G5'])] * 2
    total = bar * len(prog)
    buf = [0.0] * int(total * SR)
    for b, (root, arp) in enumerate(prog):
        t0 = b * bar
        for k in range(8):  # بیس هشتایی
            _add_at(buf, _bass(note(root), beat * 0.45, 0.42), t0 + k * beat * 0.5)
        for k in range(16):  # آرپژ شانزده‌تایی
            nm = arp[k % 4]
            _add_at(buf, tone(note(nm), beat * 0.22, 'square', 0.10, decay_rate=5.0, attack=0.002), t0 + k * beat * 0.25)
        for k in range(4):  # ضرب
            _add_at(buf, tone(70, 0.12, 'sine', 0.55, f_end=45, decay_rate=5.0), t0 + k * beat)
        for k in (1, 3):
            _add_at(buf, noise_burst(0.06, 0.18, lowpass=0.6, decay_rate=8.0, rng=random.Random(50 + b + k)),
                    t0 + k * beat)
    return normalize(buf, 0.55)


# ---------- جدول خروجی ----------

def build_all():
    """نام فایل (بدون پسوند) -> نمونه‌ها."""
    return {
        'shot_fire_1': sfx_shot_fire(1), 'shot_fire_2': sfx_shot_fire(2),
        'mirror_hit_1': sfx_mirror_hit(1), 'mirror_hit_2': sfx_mirror_hit(2), 'mirror_hit_3': sfx_mirror_hit(3),
        'target_destroy_1': sfx_target_destroy(1), 'target_destroy_2': sfx_target_destroy(2),
        'obstacle_hit_1': sfx_obstacle_hit(),
        'level_win': sfx_level_win(), 'level_lose': sfx_level_lose(),
        'low_time_warning': sfx_low_time_warning(),
        'button_tap': sfx_button_tap(), 'purchase': sfx_purchase(),
        'menu_theme': music_menu(), 'gameplay_theme': music_gameplay(),
    }


def write_wav(path, samples):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', max(-32767, min(32767, int(v * 32767)))) for v in samples))


def expected_names():
    from core.audio_manager import SFX_VARIANTS, MUSIC_TRACKS
    names = {os.path.splitext(f)[0] for files in SFX_VARIANTS.values() for f in files}
    names |= {os.path.splitext(f)[0] for f in MUSIC_TRACKS.values()}
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'assets', 'audio'))
    ap.add_argument('--wav-only', action='store_true')
    args = ap.parse_args()

    tracks = {}
    for name, samples in build_all().items():
        peak = 0.85 if not name.endswith('_theme') else 0.6
        tracks[name] = normalize(samples, peak)
    missing = expected_names() - set(tracks)
    if missing:
        print('خطا: فایل‌های مورد انتظار AudioManager تولید نشدند:', sorted(missing))
        return 1
    extra = set(tracks) - expected_names()
    if extra:
        print('هشدار: فایل اضافی (در AudioManager نیست):', sorted(extra))

    os.makedirs(args.out, exist_ok=True)
    have_ffmpeg = shutil.which('ffmpeg') is not None
    if not args.wav_only and not have_ffmpeg:
        print('خطا: ffmpeg پیدا نشد (فقط برای تولید OGG لازم است). از --wav-only استفاده کن.')
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        for name, samples in sorted(tracks.items()):
            if args.wav_only:
                write_wav(os.path.join(args.out, name + '.wav'), samples)
                continue
            wav_path = os.path.join(tmp, name + '.wav')
            write_wav(wav_path, samples)
            ogg_path = os.path.join(args.out, name + '.ogg')
            quality = '2' if name.endswith('_theme') else '3'
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav_path, '-c:a', 'libvorbis',
                            '-q:a', quality, '-map_metadata', '-1', '-fflags', '+bitexact',
                            '-flags:a', '+bitexact', ogg_path], check=True)
            print(f"{name}.ogg  {os.path.getsize(ogg_path) / 1024:.1f} KB  {len(samples) / SR:.2f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
