#!/usr/bin/env python3
"""Prototype and verify layout-aware reading order."""

import pymupdf
from rapid_layout import RapidLayout
from rapidocr import RapidOCR

def _cluster_columns(lines, width):
    if len(lines) < 2:
        return lines
    gap = max(24.0, width * 0.08)
    ordered = sorted(lines, key=lambda l: l["bbox"][0])
    clusters = []
    for line in ordered:
        x0 = line["bbox"][0]
        if not clusters or x0 - clusters[-1][-1]["bbox"][0] > gap:
            clusters.append([line])
        else:
            clusters[-1].append(line)
    merged = []
    for cluster in clusters:
        if merged:
            prev_x1 = max(l["bbox"][2] for l in merged[-1])
            curr_x0 = min(l["bbox"][0] for l in cluster)
            if curr_x0 < prev_x1:
                merged[-1].extend(cluster)
                continue
        merged.append(cluster)
    if len(merged) < 2:
        return sorted(lines, key=lambda l: (l["bbox"][1], l["bbox"][0]))
    ordered_lines = []
    for cluster in sorted(merged, key=lambda g: min(l["bbox"][0] for l in g)):
        ordered_lines.extend(sorted(cluster, key=lambda l: (l["bbox"][1], l["bbox"][0])))
    return ordered_lines

def order_lines_v2(lines, width):
    if len(lines) < 2:
        return lines
    spanning = [l for l in lines if (l["bbox"][2] - l["bbox"][0]) > 0.5 * width]
    if not spanning:
        return _cluster_columns(lines, width)

    spanning.sort(key=lambda l: l["bbox"][1])
    result = []
    current_y = 0.0
    for span in spanning:
        sy0 = span["bbox"][1]
        sy1 = span["bbox"][3]
        between = [l for l in lines if current_y <= l["bbox"][1] < sy0 and l not in spanning]
        if between:
            result.extend(_cluster_columns(between, width))
        result.append(span)
        current_y = sy1
    remaining = [l for l in lines if l["bbox"][1] >= current_y and l not in spanning]
    if remaining:
        result.extend(_cluster_columns(remaining, width))
    return result

def order_items_with_layout(items, layout_blocks, width, height):
    if len(items) < 2:
        return items

    valid_blocks = [b for b in layout_blocks if b.get("score", 1.0) >= 0.4] if layout_blocks else []
    if not valid_blocks:
        return order_lines_v2(items, width)

    block_lines = [[] for _ in valid_blocks]
    unassigned = []

    for item in items:
        cx = (item["bbox"][0] + item["bbox"][2]) / 2
        cy = (item["bbox"][1] + item["bbox"][3]) / 2

        matched_idx = None
        min_area = float("inf")

        for idx, block in enumerate(valid_blocks):
            bx0, by0, bx1, by1 = block["bbox"]
            if (bx0 - 5 <= cx <= bx1 + 5) and (by0 - 5 <= cy <= by1 + 5):
                area = max(1.0, (bx1 - bx0) * (by1 - by0))
                if area < min_area:
                    min_area = area
                    matched_idx = idx

        if matched_idx is not None:
            block_lines[matched_idx].append(item)
        else:
            unassigned.append(item)

    def block_key(idx):
        block = valid_blocks[idx]
        cls = block.get("class", "text")
        b = block["bbox"]
        priority = 1
        if cls == "header" or (b[3] < height * 0.15 and (b[2] - b[0]) > width * 0.5):
            priority = 0
        elif cls == "footer" or (b[1] > height * 0.85 and (b[2] - b[0]) > width * 0.5):
            priority = 2
        return (priority, round(b[1] / 30), b[0])

    ordered_block_indices = sorted(range(len(valid_blocks)), key=block_key)

    result = []
    for idx in ordered_block_indices:
        b_lines = block_lines[idx]
        if not b_lines:
            continue
        bw = valid_blocks[idx]["bbox"][2] - valid_blocks[idx]["bbox"][0]
        result.extend(order_lines_v2(b_lines, bw))

    if unassigned:
        result.extend(order_lines_v2(unassigned, width))

    return result

if __name__ == "__main__":
    doc = pymupdf.open("artifacts/scratch/INF2002/6 - Visual Design.pdf")
    img_bytes = doc.extract_image(30)["image"]
    doc.close()

    ocr = RapidOCR()
    layout = RapidLayout()

    layout_res = layout(img_bytes)
    ocr_res = ocr(img_bytes)

    blocks = []
    for box, cls, score in zip(layout_res.boxes, layout_res.class_names, layout_res.scores):
        blocks.append({"bbox": tuple(box), "class": cls, "score": score})

    items = []
    for b, t in zip(ocr_res.boxes, ocr_res.txts):
        xs = [p[0] for p in b]
        ys = [p[1] for p in b]
        items.append({"bbox": (min(xs), min(ys), max(xs), max(ys)), "text": t})

    ordered = order_items_with_layout(items, blocks, 1176.0, 688.0)
    out_text = " ".join(it["text"] for it in ordered)
    print("=== Ordered Text Preview ===")
    print(out_text[:1200])
