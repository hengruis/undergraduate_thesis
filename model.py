import torch
from torch import nn

# num of classes for each attribute
num_classes = [
    8,  # coat length
    5,  # collar design
    5,  # lapel design
    5,  # neck design
    10,  # neckline design
    6,  # pant length
    6,  # skirt length
    9  # sleeve length
]

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

"""
    structure:
        multi-task classification ->
        global average pooling (Grad-AAM)->
        ReLU ->
        ROI extraction ->
        ROI pooling ->
        output
"""


# --------------------------------- ResNet --------------------------------- #

def conv3x3(in_planes, out_planes, stride=(1, 1)):
    return nn.Conv2d(in_planes, out_planes, kernel_size=(3, 3), stride=stride,
                     padding=(1, 1), bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=(1, 1), downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, layers, attribute):
        self.attr = attribute
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=(7, 7), stride=(2, 2),
                               padding=(3, 3), bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=(2, 2))
        self.layer3 = self._make_layer(block, 256, layers[2], stride=(2, 2))
        self.layer4 = self._make_layer(block, 512, layers[3], stride=(2, 2))
        self.avgpool = nn.AvgPool2d(16, stride=1)

        # each attribute assigned to a single FC layer
        self.fc1_coat_length = nn.Linear(512 * block.expansion, num_classes[0])
        self.fc2_collar_design = nn.Linear(512 * block.expansion, num_classes[1])
        self.fc3_lapel_design = nn.Linear(512 * block.expansion, num_classes[2])
        self.fc4_neck_design = nn.Linear(512 * block.expansion, num_classes[3])
        self.fc5_neckline_design = nn.Linear(512 * block.expansion, num_classes[4])
        self.fc6_pant_length = nn.Linear(512 * block.expansion, num_classes[5])
        self.fc7_skirt_length = nn.Linear(512 * block.expansion, num_classes[6])
        self.fc8_sleeve_length = nn.Linear(512 * block.expansion, num_classes[7])

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def _make_layer(self, block, planes, blocks, stride=(1, 1)):
        downsample = None
        if stride != (1, 1) or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=(1, 1), stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = [block(self.inplanes, planes, stride, downsample)]
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)  # [2, 512, 10, 10]
        x = x.view(x.size(0), -1)

        if self.attr == 'coat_length':
            x = self.fc1_coat_length(x)
        elif self.attr == 'collar_design':
            x = self.fc2_collar_design(x)
        elif self.attr == 'lapel_design':
            x = self.fc3_lapel_design(x)
        elif self.attr == 'neck_design':
            x = self.fc4_neck_design(x)
        elif self.attr == 'neckline_design':
            x = self.fc5_neckline_design(x)
        elif self.attr == 'pant_length':
            x = self.fc6_pant_length(x)
        elif self.attr == 'skirt_length':
            x = self.fc7_skirt_length(x)
        elif self.attr == 'sleeve_length':
            x = self.fc8_sleeve_length(x)

        return x
