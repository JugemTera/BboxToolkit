import os
import time
import zipfile
import numpy as np
import os.path as osp

from PIL import Image
from functools import partial
from multiprocessing import Pool
from .misc import img_exts
from ..geometry import bbox2type


def load_rctw_17(img_dir, ann_dir=None, classes=None, nproc=10):
    if classes is not None:
        print('load_rctw_17 loads all objects as `text`, arguments classes is no use')

    imgpaths = [f for f in os.listdir(img_dir) if f[-4:] in img_exts]
    _load_func = partial(_load_rctw_17_single,
                         img_dir=img_dir,
                         ann_dir=ann_dir)

    print('Starting loading RCTW-17 dataset information.')
    start_time = time.time()
    if nproc > 1:
        pool = Pool(nproc)
        contents = pool.map(_load_func, imgpaths)
        pool.close()
    else:
        contents = list(map(_load_func, imgpaths))
    end_time = time.time()
    print(f'Finishing loading RCTW-17, get {len(contents)} images, ',
          f'using {end_time-start_time:.3f}s.')
    return contents, ['text']


def _load_rctw_17_single(imgfile, img_dir, ann_dir):
    img_id, _ = osp.splitext(imgfile)
    txtfile = None if imgfile is None else osp.join(ann_dir, img_id+'.txt')
    content = _load_rctw_17_txt(txtfile)

    imgfile = osp.join(img_dir, imgfile)
    width, height = Image.open(imgfile).size
    content.update(dict(width=width, height=height, filename=imgfile, id=img_id))
    return content


def _load_rctw_17_txt(txtfile):
    bboxes, diffs, texts = [], [], []
    if txtfile is None:
        pass
    elif not osp.isfile(txtfile):
        print(f'Cannot find {txtfile}, treated as empty txtfile')
    else:
        with open(txtfile, 'r') as f:
            for line in f:
                items = line.strip().split(',')

                bboxes.append([float(i) for i in items[:8]])
                diffs.append(int(items[8]))
                texts.append(items[-1][1:-1])

    bboxes = np.array(bboxes, dtype=np.float32) if bboxes \
            else np.zeros((0, 8), dtype=np.float32)
    diffs = np.array(diffs, dtype=np.int64) if diffs \
            else np.zeros((0, ), dtype=np.int64)
    labels = np.zeros((bboxes.shape[0], ), dtype=np.int64)
    ann = dict(bboxes=bboxes, labels=labels, diffs=diffs, texts=texts)
    return dict(ann=ann)


def save_rctw_17(save_dir, id_list, dets_list, text_list=None, with_zipfile=True):
    task = 'task1' if text_list is None else 'task2'
    if osp.exists(save_dir):
        raise ValueError(f'The save_dir should be non-exist path, but {save_dir} is existing')
    os.makedirs(save_dir)

    txtfiles = []
    for i, (img_id, dets) in enumerate(zip(id_list, dets_list)):
        dets = dets[0] if isinstance(dets, list) else dets
        txtfile = osp.join(save_dir, task+'_'+img_id+'.txt')
        txtfiles.append(txtfile)

        with open(txtfile, 'w') as f:
            bboxes, scores = dets[:, :-1], dets[:, -1]
            bboxes = bbox2type(bboxes, 'poly')
            ends = text_list[i] if text_list is not None \
                    else scores

            for bbox, end in zip(bboxes, ends):
                items = ['%.2f'%(p) for p in bbox] + [str(end)]
                f.writelines(','.join(items)+'\n')

    if with_zipfile:
        target_name = osp.split(save_dir)[-1]
        with zipfile.ZipFile(osp.join(save_dir, target_name+'.zip'), 'w',
                             zipfile.ZIP_DEFLATED) as t:
            for f in txtfiles:
                t.write(f, osp.split(f)[-1])
