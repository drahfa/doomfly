"""Summarize the matched training/frozen-control study from its audit archives.

Only completed rounds (engine reported finished) count. Rounds interrupted by a
restart are censored. Blocks follow study.json: 50 completed rounds per block.
Run: .venv-neural/bin/python outputs/doom/local-study-20260911/compare.py
"""
import gzip, json, sys, urllib.request, zlib
from pathlib import Path
from statistics import mean, median

STUDY = Path(__file__).resolve().parent
BLOCK = 50
PORTS = {'training': 8766, 'control': 8767}


def rounds(arm):
    ends = {}
    for path in sorted((STUDY / arm / 'archive').glob('*.jsonl.gz')):
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        break  # partially flushed last line of the live file
                    game = event['game']
                    if game['finished']:
                        ends[(event['run_id'], event['episode'])] = {
                            'ticks': game['tick'], 'kills': game['kills'],
                            'neural_s': event['neural_ms'] / 1000}
        except (EOFError, OSError, zlib.error):
            pass  # the live gzip member is still being written
    return sorted(ends.values(), key=lambda r: r['neural_s'])


def live(arm):
    try:
        state = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORTS[arm]}/state', timeout=5))
    except Exception:
        return None
    return state


def describe(rows):
    if not rows:
        return '—'
    ticks = [r['ticks'] for r in rows]
    return (f"n={len(rows):3d}  survival mean {mean(ticks):6.1f} / median {median(ticks):5.0f} tics"
            f"  kills/round {mean(r['kills'] for r in rows):.2f}")


def main():
    data = {arm: rounds(arm) for arm in PORTS}
    for arm in PORTS:
        state = live(arm)
        status = 'offline'
        if state and state.get('status') == 'running':
            status = (f"{state['protocol']['phase']}, brain {state['clocks']['neural_seconds']:.0f} s,"
                      f" speed {state['clocks']['speed']:.3f}x, round {state['game']['episode']}")
            if state.get('learning'):
                m = state['learning']
                status += (f", weights changed {m['changed_edges']}/{m['plastic_edges']}"
                           f" (enabled={m['enabled']}), mean efficacy {m['mean_efficacy']:.3f}")
        print(f"{arm:8s} [{status}]")
        print(f"         all completed rounds: {describe(data[arm])}")
    blocks = max(len(v) for v in data.values()) // BLOCK
    if blocks:
        print(f"\nBlocks of {BLOCK} completed rounds (equal round index):")
    for b in range(blocks):
        print(f"  block {b + 1}:")
        for arm in PORTS:
            chunk = data[arm][b * BLOCK:(b + 1) * BLOCK]
            note = '' if len(chunk) == BLOCK else '  (incomplete)'
            print(f"    {arm:8s} {describe(chunk)}{note}")
    shortest = min(len(v) for v in data.values())
    tail = data['training'][BLOCK:shortest], data['control'][BLOCK:shortest]
    if len(tail[0]) >= 20:
        from scipy.stats import mannwhitneyu
        p = mannwhitneyu([r['ticks'] for r in tail[0]], [r['ticks'] for r in tail[1]], alternative='two-sided').pvalue
        print(f"\nRounds {BLOCK + 1}-{shortest}, training vs control survival: Mann-Whitney p={p:.3g}"
              " (descriptive; one seed, one brain, not a validation gate)")
    else:
        print(f"\nNot enough rounds yet for a comparison beyond the first {BLOCK}"
              f" (training {len(data['training'])}, control {len(data['control'])} completed).")


if __name__ == '__main__':
    sys.exit(main())
