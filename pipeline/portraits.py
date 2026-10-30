"""Portraits for the page: the person's Wikidata image (P18) from Wikimedia Commons,
cropped to the face, toned as an ink print over a faint red plate inside a soft
cameo oval, with author and licence kept for the credits. Used by 13_whatif.py
(large cards) and 16_faces.py (small faces for the team builder).
"""
import base64
import html
import os
import re

import cv2
import numpy as np
import requests

from common import ROOT, UA, get_json

IMG = os.path.join(ROOT, "cache", "img")
os.makedirs(IMG, exist_ok=True)
face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET = os.path.expanduser("~/.cache/opencv/face_detection_yunet_2023mar.onnx")


def yunet_face(im):
    """The largest face OpenCV's YuNet network is at least 85% sure of, as (x, y, w, h), or None.
    Stricter than the Haar cascade, which can mistake a shirt or an ear for a face."""
    if not os.path.exists(YUNET):
        os.makedirs(os.path.dirname(YUNET), exist_ok=True)
        r = requests.get(YUNET_URL, headers=UA, timeout=60)
        r.raise_for_status()
        open(YUNET, "wb").write(r.content)
    H, W = im.shape[:2]
    det = cv2.FaceDetectorYN.create(YUNET, "", (W, H), 0.85)
    _, fs = det.detect(im)
    if fs is None or not len(fs):
        return None
    x, y, w, h = max(fs, key=lambda r: r[2] * r[3])[:4]
    return int(x), int(y), int(w), int(h)
strip = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def portrait(person, size=None, strict=False):
    """size: (w, h) to shrink the finished cameo, or None for 320x400. strict: find the face with YuNet instead of the Haar cascade."""
    fname = requests.utils.unquote(person["img"].split("/Special:FilePath/")[-1])
    body = get_json("commons", "https://commons.wikimedia.org/w/api.php", {"action": "query", "titles": "File:" + fname, "prop": "imageinfo",
                    "iiprop": "url|extmetadata|mime", "iiurlwidth": 480, "format": "json"})
    ii = next(iter(body["query"]["pages"].values()))["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    path = os.path.join(IMG, person["qid"] + "_480.img")
    if not os.path.exists(path):
        r = requests.get(ii["thumburl"], headers=UA, timeout=60)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    im = cv2.imread(path)
    if im is None:
        raise RuntimeError(f"could not read {path}")
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    H0, W0 = g.shape
    if strict:
        box = yunet_face(im)
        fs = [box] if box else []
    else:
        fs = face.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    if len(fs):
        x, y, w, h = max(fs, key=lambda r: r[2] * r[3])
        ch = int(h * 2.5); cw = int(ch * 0.8); cx = x + w // 2; top = max(0, y - int(h * 0.55))
    else:
        cw = min(W0, int(H0 * 0.8)); ch = int(cw / 0.8); cx = W0 // 2; top = 0
    x0 = max(0, min(W0 - cw, cx - cw // 2)); crop = g[top:top + ch, x0:x0 + cw]
    crop = cv2.resize(crop, (320, 400), interpolation=cv2.INTER_AREA)
    crop = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6)).apply(crop).astype(np.float32)   # lift faces in dark photos
    lo, hi = np.percentile(crop, 3), np.percentile(crop, 97)
    crop = np.clip((crop - lo) / max(1, hi - lo), 0, 1)
    crop = 1 / (1 + np.exp(-(crop - 0.5) * 3.2))                             # gentle S-curve: keeps facial detail
    crop = (crop - crop.min()) / max(1e-6, crop.max() - crop.min())
    crop = cv2.GaussianBlur(crop, (3, 3), 0)
    yy, xx = np.mgrid[0:400, 0:320]
    oval = np.clip(1.35 - np.sqrt(((xx - 160) / 132.0) ** 2 + ((yy - 182) / 172.0) ** 2) * 1.35, 0, 1)   # cameo: fade to paper outside a soft oval
    oval = cv2.GaussianBlur(oval.astype(np.float32), (0, 0), 6)
    dark = (1 - crop) * oval
    # ink-toned photo: the real face stays clear; a fine halftone grain and a faint red offset keep the print look
    out = np.zeros((400, 320, 4), np.float32)
    tone = np.clip(dark * 1.15, 0, 1) ** 0.85
    yy2, xx2 = np.mgrid[0:400, 0:320]
    screen = 0.5 + 0.5 * np.sin((xx2 + yy2) * 0.9) * np.sin((xx2 - yy2) * 0.9)     # 45-degree dot screen
    grain = np.random.default_rng(len(person["name"])).random((400, 320)).astype(np.float32)
    ink_a = np.clip(tone * (0.86 + 0.14 * screen) * (0.94 + 0.06 * grain), 0, 1)
    red_a = np.roll(np.roll(np.clip((tone - 0.45) * 1.4, 0, 1) * 0.32, 2, 0), 3, 1)
    for k, c in enumerate((62, 76, 220)):        # red plate (BGR) under the ink
        out[..., k] = c
    out[..., 3] = red_a
    a_ = ink_a + red_a * (1 - ink_a)
    for k, c in enumerate((40, 27, 29)):
        out[..., k] = np.where(a_ > 0, (c * ink_a + out[..., k] * red_a * (1 - ink_a)) / np.maximum(a_, 1e-6), 0)
    out[..., 3] = a_
    out = np.dstack([out[..., :3], out[..., 3] * 255]).clip(0, 255).astype(np.uint8)
    if size:
        out = cv2.resize(out, size, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".webp", out, [cv2.IMWRITE_WEBP_QUALITY, 82 if not size else 76])
    if not ok:
        raise RuntimeError("webp encode failed")
    lic = strip(meta.get("LicenseShortName", {}).get("value"))
    return {"src": "data:image/webp;base64," + base64.b64encode(buf.tobytes()).decode(), "credit": strip(meta.get("Artist", {}).get("value"))[:120],
            "license": lic, "file_url": ii.get("descriptionurl"), "face_found": bool(len(fs))}


