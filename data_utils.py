import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from multiprocessing import cpu_count
import os

from text import text_to_sequence
import hparams as hp
# from alignment import get_alignment
import Tacotron2.hparams as hp_tacotron2
import Tacotron2.model as model_tacotron2
import Tacotron2.layers as layers_tacotron2
import Tacotron2.train as train_tacotron2


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class FastSpeechDataset(Dataset):
    """ LJSpeech """

    def __init__(self, dataset_path=hp.dataset_path):
        # self.tacotron2 = tacotron2

        self.dataset_path = dataset_path
        self.text_path = os.path.join(self.dataset_path, "train.txt")
        self.text = process_text(self.text_path)

    def __len__(self):
        return len(self.text)

    def __getitem__(self, idx):
        index = idx + 1
        mel_name = os.path.join(
            self.dataset_path, "ljspeech-mel-%05d.npy" % index)
        mel_np = np.load(mel_name)

        character = self.text[idx]
        character = text_to_sequence(character, hp.text_cleaners)
        character = np.array(character)

        # alignment = get_alignment(character)

        if not hp.pre_target:
            return {"text": character, "mel": mel_np}
        else:
            alignment = np.load(os.path.join(
                hp.alignment_target_path, str(idx)+".npy"))
            # print(np.shape(alignment))
            # print(alignment)
            return {"text": character, "mel": mel_np, "alignment": alignment}


def process_text(train_text_path):
    with open(train_text_path, "r", encoding="utf-8") as f:
        inx = 0
        txt = []
        for line in f.readlines():
            cnt = 0
            for index, ele in enumerate(line):
                if ele == '|':
                    cnt = cnt + 1
                    if cnt == 2:
                        inx = index
                        end = len(line)
                        # print(line)
                        txt.append(line[inx+1:end-1])
                        break

        return txt


def collate_fn(batch):
    texts = [d['text'] for d in batch]
    mels = [d['mel'] for d in batch]

    if not hp.pre_target:

        texts, pos_padded = pad_text(texts)
        mels = pad_mel(mels)

        return {"texts": texts, "pos": pos_padded, "mels": mels}
    else:
        alignment_target = [d["alignment"] for d in batch]

        texts, pos_padded = pad_text(texts)
        alignment_target = pad_alignment(alignment_target)
        mels = pad_mel(mels)

        return {"texts": texts, "pos": pos_padded, "mels": mels, "alignment": alignment_target}


def pad_text(inputs):

    def pad_data(x, length):
        pad = 0
        x_padded = np.pad(
            x, (0, length - x.shape[0]), mode='constant', constant_values=pad)
        pos_padded = np.pad(np.array([(i+1) for i in range(np.shape(x)[0])]),
                            (0, length - x.shape[0]), mode='constant', constant_values=pad)

        return x_padded, pos_padded

    max_len = max((len(x) for x in inputs))

    text_padded = np.stack([pad_data(x, max_len)[0] for x in inputs])
    pos_padded = np.stack([pad_data(x, max_len)[1] for x in inputs])

    return text_padded, pos_padded


def pad_alignment(alignment):

    def pad_data(x, length):
        pad = 0
        x_padded = np.pad(
            x, (0, length - x.shape[0]), mode='constant', constant_values=pad)

        return x_padded

    max_len = max((len(x) for x in alignment))

    alignment_padded = np.stack([pad_data(x, max_len) for x in alignment])

    return alignment_padded


def pad_mel(inputs):

    def pad(x, max_len):
        if np.shape(x)[0] > max_len:
            raise ValueError("not max_len")

        s = np.shape(x)[1]
        x = np.pad(x, (0, max_len - np.shape(x)
                       [0]), mode='constant', constant_values=0)

        return x[:, :s]

    max_len = max(np.shape(x)[0] for x in inputs)

    # def gen_gate(batchlen, maxlen):
    #     list_A = [0 for i in range(batch_len - 1)]
    #     list_B = [1 for i in range(max_len - batch_len + 1)]

    #     output = list_A + list_B
    #     output = np.array(output)

    #     return output

    # gate_target = list()

    # for batch in inputs:
    #     batch_len = np.shape(batch)[0]
    #     gate_target.append(gen_gate(batch_len, max_len))

    # gate_target = np.stack(gate_target)

    mel_output = np.stack([pad(x, max_len) for x in inputs])

    # # Get tgt_sep tgt_pos
    # batch_len = list()
    # for batch_ind in range(np.shape(gate_target)[0]):
    #     cnt = 0
    #     for ele in gate_target[batch_ind]:
    #         if ele == 1:
    #             cnt = cnt + 1
    #     # print(cnt)
    #     batch_len.append(cnt)

    # tgt_sep = np.zeros(np.shape(gate_target))
    # tgt_pos = np.zeros(np.shape(gate_target))

    # for i in range(np.shape(gate_target)[0]):
    #     for j in range(np.shape(gate_target)[1] - batch_len[i]+1):
    #         tgt_sep[i][j] = 1
    #         tgt_pos[i][j] = j + 1

    # return mel_output, gate_target, tgt_sep, tgt_pos
    return mel_output


if __name__ == "__main__":
    # Test
    # hparams = hp_tacotron2.create_hparams()
    # hparams.sampling_rate = hp.sample_rate

    # checkpoint_path = os.path.join("Tacotron2", os.path.join(
    #     "pre_trained_model", "tacotron2_statedict.pt"))

    # tacotron2 = train_tacotron2.load_model(hparams)
    # tacotron2.load_state_dict(torch.load(checkpoint_path)["state_dict"])
    # # print(tacotron2)
    # _ = tacotron2.cuda().eval().half()
    # print("#######################")

    dataset = FastSpeechDataset()
    # print("#######################")
    training_loader = DataLoader(dataset,
                                 batch_size=2,
                                 shuffle=False,
                                 collate_fn=collate_fn,
                                 drop_last=True,
                                 num_workers=1)

    for i, data in enumerate(training_loader):
        # Test
        # print(data["tgt_sep"])
        # print(data["tgt_pos"])
        # print(data["pos"])
        # print(len(data["alignment"]))

        if not hp.pre_target:
            print(np.shape(data["texts"]))
        else:
            print(np.shape(data["alignment"]))
            print(np.shape(data["texts"]))
            # print(data["alignment"])
