"""
Based on official PyTorch implementation from:
https://github.com/pytorch/vision/blob/master/torchvision/models/shufflenetv2.py

ShuffleNet v2 paper: <https://arxiv.org/abs/1807.11164>
"""


import torch
import torch.nn as nn


def channel_shuffle(x, groups):
    batchsize, num_channels, height, width = x.data.size()
    channels_per_group = num_channels // groups

    # reshape
    x = x.view(
        batchsize, groups,
        channels_per_group, height, width)

    x = torch.transpose(x, 1, 2).contiguous()

    # flatten
    x = x.view(batchsize, -1, height, width)

    return x


class InvertedResidual(nn.Module):
    def __init__(self, inp, oup, stride):
        super(InvertedResidual, self).__init__()
        self.stride = stride

        branch_features = oup // 2
        assert (self.stride != 1) or (inp == branch_features << 1)

        if self.stride > 1:
            self.branch1 = nn.Sequential(
                self.depthwise_conv(inp, inp, kernel_size=3, stride=self.stride, padding=1),
                nn.BatchNorm2d(inp),
                nn.Conv2d(inp, branch_features, kernel_size=1, stride=1, padding=0, bias=False),
                nn.BatchNorm2d(branch_features),
                nn.ReLU(inplace=True),
            )
        else:
            self.branch1 = nn.Sequential()

        self.branch2 = nn.Sequential(
            nn.Conv2d(
                inp if (self.stride > 1) else branch_features,
                branch_features, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(branch_features),
            nn.ReLU(inplace=True),
            self.depthwise_conv(branch_features, branch_features, kernel_size=3, stride=self.stride, padding=1),
            nn.BatchNorm2d(branch_features),
            nn.Conv2d(branch_features, branch_features, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(branch_features),
            nn.ReLU(inplace=True),
        )

    @staticmethod
    def depthwise_conv(i, o, kernel_size, stride=1, padding=0, bias=False):
        return nn.Conv2d(i, o, kernel_size, stride, padding, bias=bias, groups=i)

    def forward(self, x):
        if self.stride == 1:
            x1, x2 = x.chunk(2, dim=1)
            out = torch.cat((x1, self.branch2(x2)), dim=1)
        else:
            out = torch.cat((self.branch1(x), self.branch2(x)), dim=1)

        out = channel_shuffle(out, 2)

        return out


class ShuffleNetV2(nn.Module):
    def __init__(
        self,
        num_classes,
        img_channels,
        stages_repeats,
        stages_out_channels,
        inverted_residual=InvertedResidual
    ):
        super().__init__()
        self.num_classes = num_classes
        self.img_channels = img_channels

        if len(stages_repeats) != 3:
            raise ValueError('expected stages_repeats as list of 3 positive ints')
        if len(stages_out_channels) != 5:
            raise ValueError('expected stages_out_channels as list of 5 positive ints')
        self._stage_out_channels = stages_out_channels

        input_channels = self.img_channels
        output_channels = self._stage_out_channels[0]
        self.conv1 = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, 2, 1, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.ReLU(inplace=True),
        )
        input_channels = output_channels

        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        stage_names = ['stage{}'.format(i) for i in [2, 3, 4]]
        for name, repeats, output_channels in zip(
                stage_names, stages_repeats, self._stage_out_channels[1:]):
            seq = [inverted_residual(input_channels, output_channels, 2)]
            for i in range(repeats - 1):
                seq.append(inverted_residual(output_channels, output_channels, 1))
            setattr(self, name, nn.Sequential(*seq))
            input_channels = output_channels

        output_channels = self._stage_out_channels[-1]
        self.conv5 = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 1, 1, 0, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.ReLU(inplace=True),
        )

        self.fc = nn.Linear(output_channels, self.num_classes)

    def forward(self, input):
        output = self.conv1(input)
        output = self.maxpool(output)
        output = self.stage2(output)
        output = self.stage3(output)
        output = self.stage4(output)
        output = self.conv5(output)
        output = output.mean([2, 3])
        output = self.fc(output)
        return output


def ShuffleNet_v2_x05(num_classes, img_channels, *args, **kwargs):
    return ShuffleNetV2(num_classes, img_channels, [4, 8, 4], [24, 48, 96, 192, 1024], **kwargs)


def ShuffleNet_v2_x10(num_classes, img_channels, *args, **kwargs):
    return ShuffleNetV2(num_classes, img_channels, [4, 8, 4], [24, 116, 232, 464, 1024], **kwargs)


def ShuffleNet_v2_x15(num_classes, img_channels, *args, **kwargs):
    return ShuffleNetV2(num_classes, img_channels, [4, 8, 4], [24, 176, 352, 704, 1024], **kwargs)


def ShuffleNet_v2_x20(num_classes, img_channels, *args, **kwargs):
    return ShuffleNetV2(num_classes, img_channels, [4, 8, 4], [24, 244, 488, 976, 2048], **kwargs)
