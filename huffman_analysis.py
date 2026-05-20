"""
ゴリリンガル 符号化方式比較分析
- 標準: 各バイト → 4文字 (5^4 = 625 ≥ 256)
- バイナリハフマン: ビット列 → base-5変換（現行実装）
- 5進ハフマン (quinary Huffman): 各シンボルを直接5文字アルファベットで符号化
"""

import heapq
from collections import Counter
import math

# ウホッ！？ の5文字
CHARS = ['ウ', 'ホ', 'ッ', '！', '？']

# ===== サンプルテキスト (20文) =====
SAMPLES = [
    "今日はいい天気ですね。",
    "ありがとうございます。",
    "おはようございます。今日も一日頑張りましょう。",
    "日本語はとても面白い言語です。",
    "東京は大きな都市です。人口が多い。",
    "ゴリリンガルはウホッ！？だけで文字を表現します。",
    "プログラミングは楽しいですよ。特にPythonが好きです。",
    "山田さんは毎朝コーヒーを飲みます。",
    "新幹線に乗って大阪へ行きました。",
    "この映画はとても感動的でした。もう一度見たいです。",
    "桜の花が咲いています。春が来ましたね。",
    "人工知能の技術は急速に発展しています。",
    "毎日少しずつ勉強することが大切です。",
    "友達と一緒にランチを食べました。美味しかったです。",
    "このコードはどのように動いているのでしょうか？",
    "ハフマン符号化を使うと、データを圧縮できます。",
    "猫は自由な動物です。犬は忠実な動物です。",
    "音楽を聴きながら仕事をすると集中できます。",
    "インターネットのおかげで世界が繋がっています。",
    "健康のために毎日30分歩くようにしています。",
]


# ===== 標準エンコード =====
def standard_encode(text: str) -> str:
    utf8 = text.encode('utf-8')
    result = []
    for byte in utf8:
        digits = []
        b = byte
        for _ in range(4):
            digits.append(b % 5)
            b //= 5
        result.append(''.join(CHARS[d] for d in digits))
    return ''.join(result)


# ===== バイナリ ハフマン（現行実装と同様） =====
class BinaryNode:
    def __init__(self, byte, freq, left=None, right=None):
        self.byte = byte
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


def build_binary_huffman(freq_map: dict) -> dict:
    """バイナリハフマン木を構築し、byte→bitstring のマップを返す"""
    if len(freq_map) == 1:
        byte = next(iter(freq_map))
        return {byte: '0'}

    heap = [BinaryNode(b, f) for b, f in freq_map.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        heapq.heappush(heap, BinaryNode(None, left.freq + right.freq, left, right))

    codes = {}
    def traverse(node, prefix=''):
        if node.left is None and node.right is None:
            codes[node.byte] = prefix or '0'
            return
        if node.left:  traverse(node.left,  prefix + '0')
        if node.right: traverse(node.right, prefix + '1')

    traverse(heap[0])
    return codes


def make_canonical_binary(raw_codes: dict) -> dict:
    """正規ハフマン符号に変換"""
    entries = sorted(raw_codes.items(), key=lambda x: (len(x[1]), x[0]))
    canon = {}
    code = 0
    prev_len = len(entries[0][1])
    for byte, raw in entries:
        clen = len(raw)
        if clen > prev_len:
            code <<= (clen - prev_len)
            prev_len = clen
        canon[byte] = bin(code)[2:].zfill(clen)
        code += 1
    return canon


def binary_huffman_encode(text: str) -> str:
    utf8 = text.encode('utf-8')
    freq = Counter(utf8)
    raw_codes = build_binary_huffman(dict(freq))
    canon_codes = make_canonical_binary(raw_codes)

    # ビット列を作る
    bits = ''.join(canon_codes[b] for b in utf8)
    pad_len = (8 - len(bits) % 8) % 8
    bits += '0' * pad_len

    data_bytes = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]

    # ヘッダー: [0xFF, 0xFE, padLen, numEntries, ...{byteVal, codeLen}]
    entries_sorted = sorted(raw_codes.items(), key=lambda x: (len(x[1]), x[0]))
    header = [0xFF, 0xFE, pad_len, len(entries_sorted) & 0xFF]
    for byte, raw in entries_sorted:
        header += [byte, len(raw)]

    all_bytes = header + data_bytes
    return ''.join(
        ''.join(CHARS[d] for d in _byte_to_base5(b))
        for b in all_bytes
    )


def _byte_to_base5(byte: int) -> list:
    digits = []
    for _ in range(4):
        digits.append(byte % 5)
        byte //= 5
    return digits


# ===== 5進ハフマン木 =====
QUINARY = 5  # 分岐数

class QNode:
    def __init__(self, symbols, freq, children=None):
        self.symbols = symbols   # 葉の場合は {byte_value}
        self.freq = freq
        self.children = children or []

    def __lt__(self, other):
        return self.freq < other.freq


def build_quinary_huffman(freq_map: dict) -> dict:
    """5進ハフマン木を構築し、byte→5文字列 のコードマップを返す"""
    if len(freq_map) == 1:
        byte = next(iter(freq_map))
        return {byte: CHARS[0]}  # 'ウ' 1文字

    heap = [QNode({b}, f) for b, f in freq_map.items()]
    heapq.heapify(heap)

    # 5進木の場合、末端調整: (n-1) % (5-1) == 0 になるようダミー追加
    # 完全5分木になるよう (n + k) % 4 == 1 を満たすk個のダミーを追加
    remainder = (len(heap) - 1) % (QUINARY - 1)
    if remainder != 0:
        dummy_count = (QUINARY - 1) - remainder
        for _ in range(dummy_count):
            heapq.heappush(heap, QNode(set(), 0))

    while len(heap) > 1:
        children = [heapq.heappop(heap) for _ in range(QUINARY)]
        total_freq = sum(c.freq for c in children)
        merged_symbols = set().union(*[c.symbols for c in children])
        parent = QNode(merged_symbols, total_freq, children)
        heapq.heappush(heap, parent)

    codes = {}
    def traverse(node, prefix=''):
        if not node.children:
            for byte in node.symbols:
                codes[byte] = prefix or CHARS[0]
            return
        for i, child in enumerate(node.children):
            traverse(child, prefix + CHARS[i])

    traverse(heap[0])
    # ダミー(空シンボル)を除去
    codes.pop(None, None)
    codes = {k: v for k, v in codes.items() if isinstance(k, int)}
    return codes


def quinary_huffman_encode(text: str) -> str:
    """5進ハフマン符号化: byte → 5文字コードの列"""
    utf8 = text.encode('utf-8')
    freq = Counter(utf8)
    codes = build_quinary_huffman(dict(freq))

    # データ部
    encoded_data = ''.join(codes[b] for b in utf8)

    # ヘッダー: コードテーブルをbase-5直接エンコード
    # 形式: [0xFF, 0xFE] + [numEntries] + [{byteVal, codeLen}×n] → 各バイトを4文字base-5
    entries = sorted(codes.items(), key=lambda x: (len(x[1]), x[0]))
    header_bytes = [0xFF, 0xFE, len(entries) & 0xFF]
    for byte_val, code in entries:
        header_bytes += [byte_val, len(code)]

    header_encoded = ''.join(
        ''.join(CHARS[d] for d in _byte_to_base5(b))
        for b in header_bytes
    )

    return header_encoded + encoded_data


# ===== 統計表示 =====
def analyze(texts):
    print("=" * 80)
    print("ゴリリンガル 符号化方式比較")
    print("=" * 80)
    print(f"{'No.':<4} {'テキスト':<30} {'文字数':>5} {'標準':>6} {'2進HF':>6} {'5進HF':>6} | {'標準→2進HF':>10} {'標準→5進HF':>10}")
    print("-" * 80)

    total_std = total_bin = total_quin = 0
    total_utf8 = 0

    for i, text in enumerate(texts, 1):
        std   = standard_encode(text)
        binh  = binary_huffman_encode(text)
        quinh = quinary_huffman_encode(text)

        n_std  = len(std)
        n_bin  = len(binh)
        n_quin = len(quinh)
        n_utf8 = len(text.encode('utf-8'))

        ratio_bin  = (n_bin  - n_std) / n_std * 100
        ratio_quin = (n_quin - n_std) / n_std * 100

        total_std  += n_std
        total_bin  += n_bin
        total_quin += n_quin
        total_utf8 += n_utf8

        sign_b = "+" if ratio_bin  >= 0 else ""
        sign_q = "+" if ratio_quin >= 0 else ""
        short_text = text[:18] + ("…" if len(text) > 18 else "")
        print(f"{i:<4} {short_text:<30} {len(text):>5} {n_std:>6} {n_bin:>6} {n_quin:>6} | {sign_b}{ratio_bin:>8.1f}% {sign_q}{ratio_quin:>8.1f}%")

    print("-" * 80)
    r_bin_total  = (total_bin  - total_std) / total_std * 100
    r_quin_total = (total_quin - total_std) / total_std * 100
    print(f"{'合計/平均':<35} {total_utf8:>5} {total_std:>6} {total_bin:>6} {total_quin:>6} | {r_bin_total:>+9.1f}% {r_quin_total:>+9.1f}%")
    print()

    # 理論値の計算
    all_bytes = b''.join(t.encode('utf-8') for t in texts)
    freq_all = Counter(all_bytes)
    total_bytes = len(all_bytes)

    # エントロピー
    entropy = -sum((f/total_bytes) * math.log2(f/total_bytes) for f in freq_all.values())
    print(f"バイト列のエントロピー: {entropy:.4f} bits/byte")
    print(f"  標準エンコード:    4 × log₅(2) = {4 * math.log(2)/math.log(5):.4f} 5進桁/byte  (= 固定長4文字)")
    print(f"  2進ハフマン下限:   {entropy / math.log2(5):.4f} 5進桁/byte  (エントロピー ÷ log₂5)")
    print(f"  5進ハフマン下限:   {entropy / math.log(5) * math.log(2):.4f} 5進桁/byte  (エントロピー ÷ log₅2... ※同値)")
    print()

    # 実測
    raw_chars_std  = total_std
    raw_chars_bin  = total_bin
    raw_chars_quin = total_quin
    print(f"実測 5進文字/byte:")
    print(f"  標準:       {raw_chars_std / total_bytes:.4f}")
    print(f"  2進ハフマン:{raw_chars_bin  / total_bytes:.4f}")
    print(f"  5進ハフマン:{raw_chars_quin / total_bytes:.4f}")
    print()

    # 頻度上位10バイト
    print("頻度上位10バイトと各符号長:")
    print(f"{'バイト':>6}  {'文字':>5}  {'頻度':>6}  {'標準':>5}  {'2進HF':>5}  {'5進HF':>5}")
    print("-" * 50)

    # 全テキストでコードを構築
    freq_dict = dict(freq_all)
    bin_codes  = make_canonical_binary(build_binary_huffman(freq_dict))
    quin_codes = build_quinary_huffman(freq_dict)

    for byte_val, cnt in freq_all.most_common(10):
        try:
            char_repr = bytes([byte_val]).decode('utf-8')
        except:
            char_repr = f"[{byte_val:02X}]"

        b_len = len(bin_codes.get(byte_val, '?'))
        q_len = len(quin_codes.get(byte_val, '?'))
        # 5進ハフマンは5進文字列なので、等価ビット数 = q_len × log₂5
        b_equiv = b_len / math.log2(5)  # ビット→5進桁
        q_char = q_len
        print(f"  0x{byte_val:02X}  {char_repr:>5}  {cnt:>6}  {'4文字':>5}  {b_len:>4}bit  {q_char:>4}文字")


def analyze_static(texts):
    """全サンプルから事前にグローバル頻度テーブルを構築→ヘッダー不要で各テキストをエンコード"""
    print()
    print("=" * 80)
    print("【グローバル静的テーブル方式】全20文から頻度を計算してツリーを固定")
    print("  → 各テキストのエンコード時にヘッダー不要")
    print("=" * 80)

    # 全テキストの頻度を合算してツリー構築
    all_bytes_combined = b''.join(t.encode('utf-8') for t in texts)
    global_freq = dict(Counter(all_bytes_combined))

    # グローバル2進ハフマン符号
    global_bin_codes  = make_canonical_binary(build_binary_huffman(global_freq))
    # グローバル5進ハフマン符号
    global_quin_codes = build_quinary_huffman(global_freq)

    print(f"\n全サンプルのユニークバイト種類: {len(global_freq)}")
    print(f"全サンプルの総バイト数: {len(all_bytes_combined)}")

    print(f"\n{'No.':<4} {'テキスト':<30} {'文字数':>5} {'標準':>6} {'2進HF':>6} {'5進HF':>6} | {'標準→2進HF':>10} {'標準→5進HF':>10}")
    print("-" * 80)

    total_std = total_bin = total_quin = 0

    for i, text in enumerate(texts, 1):
        utf8 = text.encode('utf-8')

        # 標準エンコード
        std_len = len(utf8) * 4

        # 静的2進ハフマン（ヘッダーなし）
        bits = ''.join(global_bin_codes[b] for b in utf8)
        pad = (8 - len(bits) % 8) % 8
        bits += '0' * pad
        data_bytes_bin = [int(bits[j:j+8], 2) for j in range(0, len(bits), 8)]
        bin_len = len(data_bytes_bin) * 4  # 各バイト→4文字

        # 静的5進ハフマン（ヘッダーなし）
        quin_str = ''.join(global_quin_codes[b] for b in utf8)
        quin_len = len(quin_str)

        total_std  += std_len
        total_bin  += bin_len
        total_quin += quin_len

        r_bin  = (bin_len  - std_len) / std_len * 100
        r_quin = (quin_len - std_len) / std_len * 100
        sign_b = "+" if r_bin  >= 0 else ""
        sign_q = "+" if r_quin >= 0 else ""
        short = text[:18] + ("…" if len(text) > 18 else "")
        print(f"{i:<4} {short:<30} {len(text):>5} {std_len:>6} {bin_len:>6} {quin_len:>6} | {sign_b}{r_bin:>8.1f}% {sign_q}{r_quin:>8.1f}%")

    print("-" * 80)
    r_b = (total_bin  - total_std) / total_std * 100
    r_q = (total_quin - total_std) / total_std * 100
    print(f"{'合計':<35} {total_std:>6} {total_bin:>6} {total_quin:>6} | {r_b:>+9.1f}% {r_q:>+9.1f}%")

    print()
    entropy = -sum((f/len(all_bytes_combined)) * math.log2(f/len(all_bytes_combined))
                   for f in global_freq.values())
    print(f"エントロピー:         {entropy:.4f} bits/byte")
    print(f"5進桁の理論最小値:    {entropy / math.log2(5):.4f} 文字/byte")
    print(f"標準エンコード:       4.0000 文字/byte")
    print(f"静的2進ハフマン:      {total_bin / len(all_bytes_combined):.4f} 文字/byte")
    print(f"静的5進ハフマン:      {total_quin / len(all_bytes_combined):.4f} 文字/byte")

    # 5進ハフマン符号の分布
    print()
    print("グローバル5進ハフマン: 頻度上位15バイトのコード例")
    print(f"{'バイト':>6}  {'文字':>5}  {'頻度':>6}  {'5進コード':<20}  {'長さ':>4}")
    print("-" * 55)
    for byte_val, cnt in Counter(all_bytes_combined).most_common(15):
        try:
            char_repr = bytes([byte_val]).decode('utf-8')
        except:
            char_repr = f"[{byte_val:02X}]"
        code = global_quin_codes.get(byte_val, '?')
        print(f"  0x{byte_val:02X}  {char_repr:>5}  {cnt:>6}  {code:<20}  {len(code):>4}")

    print()
    print("【まとめ】")
    print(f"  標準       : 固定4文字/byte → 合計 {total_std} 文字")
    print(f"  静的2進HF  : ヘッダーなし    → 合計 {total_bin} 文字  ({r_b:+.1f}%)")
    print(f"  静的5進HF  : ヘッダーなし    → 合計 {total_quin} 文字  ({r_q:+.1f}%)")
    print(f"  理論限界   : {entropy/math.log2(5):.4f} 文字/byte → 合計 {int(len(all_bytes_combined)*entropy/math.log2(5))} 文字  (エントロピー限界)")


def analyze_coverage(texts):
    """未知バイト問題の確認と対策の比較"""
    print()
    print("=" * 80)
    print("【未知バイト問題】サンプルに登場しないバイトは符号化できない")
    print("=" * 80)

    all_bytes = b''.join(t.encode('utf-8') for t in texts)
    global_freq = dict(Counter(all_bytes))

    covered = set(global_freq.keys())
    all_256  = set(range(256))
    missing  = all_256 - covered

    print(f"\nサンプル中のユニークバイト: {len(covered)} / 256")
    print(f"未登場バイト: {len(missing)} 個")
    print(f"  例: {sorted(missing)[:20]} ...")

    # 未知バイトを含むテキストでエラーになることを確認
    test_unknown = "Hello, World! 🦍"  # 英語+絵文字（サンプルにない文字）
    test_bytes = test_unknown.encode('utf-8')
    unknown_in_test = [b for b in test_bytes if b not in covered]
    print(f"\nテスト文字列: '{test_unknown}'")
    print(f"  UTF-8バイト列: {list(test_bytes)}")
    print(f"  未知バイト: {unknown_in_test} → ⚠️ エンコード不可！")

    # ===== 対策: 全256バイトをスムージング頻度1で追加 =====
    print()
    print("── 対策: 未登場バイトに頻度1を割り当てて全256バイトをカバー ──")

    # 全256バイトに最低頻度1を保証
    smoothed_freq = {b: global_freq.get(b, 1) for b in range(256)}

    quin_smooth = build_quinary_huffman(smoothed_freq)
    bin_smooth  = make_canonical_binary(build_binary_huffman(smoothed_freq))

    # カバレッジ確認
    print(f"スムージング後のユニークバイト: {len(quin_smooth)} / 256")
    assert len(quin_smooth) == 256, "全256バイトをカバーできていない"
    print(f"  → 全256バイトをカバー ✓")

    # 未知バイト含むテキストをエンコード
    bits_test = ''.join(bin_smooth[b] for b in test_bytes)
    pad = (8 - len(bits_test) % 8) % 8
    bits_test += '0' * pad
    bin_test_len = len([0 for _ in range(0, len(bits_test), 8)]) * 4
    quin_test_str = ''.join(quin_smooth[b] for b in test_bytes)
    std_test_len = len(test_bytes) * 4

    print(f"\nテスト文字列 '{test_unknown}':")
    print(f"  標準: {std_test_len} 文字")
    print(f"  静的2進HF(スムージング済み): {bin_test_len} 文字")
    print(f"  静的5進HF(スムージング済み): {len(quin_test_str)} 文字")
    print(f"  エンコード例(5進HF): {quin_test_str[:60]}...")

    # ===== スムージング有/無の圧縮率比較 =====
    print()
    print("── 全20文でスムージングあり/なしの圧縮率比較 ──")
    quin_orig = build_quinary_huffman(global_freq)
    total_std = total_orig = total_smooth = 0
    for text in texts:
        utf8 = text.encode('utf-8')
        total_std    += len(utf8) * 4
        total_orig   += sum(len(quin_orig[b])   for b in utf8)
        total_smooth += sum(len(quin_smooth[b]) for b in utf8)

    r_orig   = (total_orig   - total_std) / total_std * 100
    r_smooth = (total_smooth - total_std) / total_std * 100
    print(f"  標準:           {total_std} 文字")
    print(f"  5進HF(スムージングなし): {total_orig} 文字  ({r_orig:+.1f}%)")
    print(f"  5進HF(スムージングあり): {total_smooth} 文字  ({r_smooth:+.1f}%)")
    print(f"  ※ スムージングによる追加コスト: {total_smooth - total_orig} 文字 ({(total_smooth-total_orig)/total_std*100:.1f}%)")

    # 未知バイトのコード長分布
    print()
    print("未知バイトのコード長（スムージング後）:")
    unknown_lens = [len(quin_smooth[b]) for b in sorted(missing)]
    from collections import Counter as C2
    dist = sorted(C2(unknown_lens).items())
    for length, count in dist:
        print(f"  長さ {length} 文字: {count} バイト")

    print()
    print("【結論】")
    print("  スムージング(頻度1)を追加することで:")
    print(f"  ・全256バイトをカバー（未知バイトOK）")
    print(f"  ・圧縮率への影響はわずか {(total_smooth-total_orig)/total_std*100:.1f}% の増加のみ")
    print(f"  ・未知バイトは長いコード（最大 {max(unknown_lens)} 文字）が割り当てられる")


def export_js_table(texts):
    """静的テーブルをJavaScriptコードとして出力"""
    all_bytes = b''.join(t.encode('utf-8') for t in texts)
    global_freq = dict(Counter(all_bytes))
    # 全256バイトをスムージング
    smoothed_freq = {b: global_freq.get(b, 1) for b in range(256)}
    codes = build_quinary_huffman(smoothed_freq)
    assert len(codes) == 256

    lines = ['// 静的5進ハフマンテーブル（全256バイト対応）',
             '// サンプル20文から生成、未登場バイトは頻度1でスムージング済み',
             'const STATIC_QHUFF_ENC = [']
    for b in range(256):
        comma = ',' if b < 255 else ''
        lines.append(f'  "{codes[b]}"{comma}  // 0x{b:02X}')
    lines.append('];')

    # デコード用: コード文字列 → バイト値
    lines.append('')
    lines.append('const STATIC_QHUFF_DEC = {')
    for b in range(256):
        comma = ',' if b < 255 else ''
        lines.append(f'  "{codes[b]}": {b}{comma}')
    lines.append('};')

    with open('static_table.js', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('\nstatic_table.js を生成しました。')
    print(f'テーブルエントリ数: {len(codes)}')
    code_lens = sorted(set(len(v) for v in codes.values()))
    print(f'コード長の種類: {code_lens}')
    for l in code_lens:
        count = sum(1 for v in codes.values() if len(v) == l)
        print(f'  {l}文字: {count}バイト')


if __name__ == '__main__':
    analyze(SAMPLES)
    analyze_static(SAMPLES)
    analyze_coverage(SAMPLES)
    export_js_table(SAMPLES)
