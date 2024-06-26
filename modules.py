from torch import nn
import torch.nn.functional as F
from attention import SEAttention


class BasicConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, transpose=False, act_norm=False):
        super(BasicConv2d, self).__init__()
        self.act_norm = act_norm
        if not transpose:
            self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size, stride=stride, padding=padding)
        else:
            self.conv = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=kernel_size, stride=stride,
                                           padding=padding, output_padding=stride // 2)
        self.norm = nn.GroupNorm(2, out_channels)
        self.act = nn.LeakyReLU(0.2, inplace=True)
        self.self_attention = SEAttention(out_channels)

    def forward(self, x):
        y = self.conv(x)
        if self.act_norm:
            y = self.act(self.norm(y))
        y = self.self_attention(y)
        return y


# 添加残差结构
# class ConvSC(nn.Module):
#     def __init__(self, C_in, C_out, stride, transpose=False, act_norm=True):
#         super(ConvSC, self).__init__()
#         # 如果步长为1，则无需转置
#         if stride == 1:
#             transpose = False
#         self.conv = BasicConv2d(C_in, C_out, kernel_size=3, stride=stride, padding=1,
#                                 transpose=transpose, act_norm=act_norm)
#
#         # 初始化恒等映射或调整尺寸的1x1卷积层来作为shortcut连接
#         self.use_shortcut = (C_in != C_out) or (stride != 1)
#         if self.use_shortcut:
#             if not transpose:  # Encoder: 使用普通卷积
#                 self.shortcut = nn.Conv2d(C_in, C_out, kernel_size=1, stride=stride, bias=False)
#             else:  # Decoder: 使用转置卷积
#                 self.shortcut = nn.ConvTranspose2d(C_in, C_out, kernel_size=1, stride=stride,
#                                                    padding=0, output_padding=stride - 1, bias=False)
#         else:
#             self.shortcut = nn.Identity()
#
#     def forward(self, x):
#         identity = self.shortcut(x)  # shortcut路径
#         y = self.conv(x)  # 主路径
#         out = y + identity  # 添加残差连接
#         return out


class ConvSC(nn.Module):
    def __init__(self, C_in, C_out, stride, transpose=False, act_norm=True):
        super(ConvSC, self).__init__()
        if stride == 1:
            transpose = False
        self.transpose = transpose
        self.conv = BasicConv2d(C_in, C_out, kernel_size=3, stride=stride,
                                padding=1, transpose=transpose, act_norm=act_norm)

    def forward(self, x):
        y = self.conv(x)
        return y


class GroupConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, groups, act_norm=False):
        super(GroupConv2d, self).__init__()
        self.act_norm = act_norm
        if in_channels % groups != 0:
            groups = 1
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size, stride=stride, padding=padding,groups=groups)
        self.norm = nn.GroupNorm(groups, out_channels)
        self.activate = nn.LeakyReLU(0.2, inplace=True)
    
    def forward(self, x):
        y = self.conv(x)
        if self.act_norm:
            y = self.activate(self.norm(y))
        return y


class Inception(nn.Module):
    def __init__(self, C_in, C_hid, C_out, incep_ker=[3, 5, 7, 11], groups=8):
        super(Inception, self).__init__()
        self.conv1 = nn.Conv2d(C_in, C_hid, kernel_size=1, stride=1, padding=0)
        layers = []
        for ker in incep_ker:
            layers.append(GroupConv2d(C_hid, C_out, kernel_size=ker, stride=1, padding=ker//2, groups=groups, act_norm=True))
        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        y = 0
        for layer in self.layers:
            y += layer(x)
        return y
