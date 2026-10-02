"""Exact cyan GO-arrow masks, extracted from this ROM's actual video frames."""
from pathlib import Path
import cv2
import numpy as np

MASKS=dict(np.load(Path(__file__).resolve().parent/'vision/go-arrows.npz'))
def arrow(picture):
    if picture is None:return None
    a=np.asarray(picture).astype(np.int16)
    m=((a[:,:,1]>a[:,:,0]+40)&(a[:,:,2]>a[:,:,0]+40)&(a[:,:,1]>140)&(a[:,:,2]>140)).astype(np.uint8)
    m[:48]=0
    best=None;error=4
    for name,template in MASKS.items():
        score=cv2.matchTemplate(m,template,cv2.TM_SQDIFF)
        value,_,location,_=cv2.minMaxLoc(score)
        if value<4 and (best is None or value<error-.5):
            best=dict(buttons=name.split('_'),location=location,error=float(value));error=value
    return best
