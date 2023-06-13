import torch
from torch import nn


import huff_and_map



class NeuralNetwork(torch.nn.Module):
    def __init__(self):
        super(NeuralNetwork, self).__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(18, 64),
            nn.LeakyReLU(0.1),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        y_pred = self.layers(x)
        return y_pred


nn_model = NeuralNetwork()
nn_model.load_state_dict(torch.load('model'))
nn_model.eval()


def prediction(lat, lon, square):
    huff = huff_and_map.calculate_huff(lat, lon, square)

    expected = nn_model(torch.tensor([[huff, square, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]]))

    return int(expected)
