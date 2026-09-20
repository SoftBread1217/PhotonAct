# PhotonAct

**PhotonAct 将测量或仿真的光学器件响应曲线转换成可微的 PyTorch 激活函数。**

[![CI](https://github.com/SoftBread1217/PhotonAct/actions/workflows/ci.yml/badge.svg)](https://github.com/SoftBread1217/PhotonAct/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10--3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![PhotonAct 工作流程](assets/workflow.svg)

```bash
python -m pip install -e .
photonact inspect examples/curves/sample_phh.csv
python examples/minimal.py
```

> **当前状态：** 早期测试版 v0.0.1。曲线读取、数据检查、可微插值、命令行工具和安装包已在
> Python 3.10-3.12 上测试。内置 `sample_phh` 是人工编写的合成演示曲线，不是实验数据，
> 也不是从论文图片数字化得到的数据。

[English README](README.md)

## 现在能做什么

第一版只建立一个完整而容易理解的闭环：

```text
CSV/JSON 曲线 -> 数据检查 -> CurveActivation -> PyTorch 自动求导
```

```python
import torch
from photonact import CurveActivation

layer = CurveActivation.from_file("examples/curves/sample_phh.csv", branch="up")
x = torch.tensor([0.25, 0.75, 1.25], requires_grad=True)
layer(x).sum().backward()
print(x.grad)
```

## 建议的学习顺序

1. 运行 [examples/minimal.py](examples/minimal.py)，观察输出和梯度。
2. 阅读 `photonact/curves.py`，理解 CSV/JSON 如何变成曲线对象。
3. 阅读 `photonact/activations/curve.py`，理解分段线性插值。
4. 修改 `sample_phh.csv` 中的一个输出值，再运行示例。
5. 阅读 `tests/test_curves.py`，学习如何验证梯度和边界行为。

## 数据格式

CSV 至少包含 `input_power` 和 `output_power`，可选 `branch`。同一分支内的输入必须严格递增。
同名 `.meta.json` 可以记录单位、来源、有效范围、归一化状态、许可证和引用信息。详细说明见
[docs/curve_data.md](docs/curve_data.md)。

## 插值与数据边界

v0.0.1 使用可微的分段线性插值，因为它比高阶样条更容易阅读、测试和解释。多分支曲线必须明确
选择分支；超出范围可选择 `clamp`、`linear` 或 `error`。

相关论文说明底层曲线数据暂未公开，因此本项目不附带论文曲线，也不声称复现论文准确率。
`sample_phh` 仅用于展示接口，使用自己的数据时必须如实记录测量、仿真或数字化来源。

## 项目边界

PhotonAct 专注于连接“光学响应曲线”和“机器学习模型”：检查带有来源说明的曲线数据，将曲线
封装成小型可微 `torch.nn.Module`，明确分支、外推、归一化和未来硬件效应的语义，并提供可以
审计配置和原始结果的可复现实验。

PhotonAct 不是电磁场求解器，不能代替器件表征，也不会在缺少来源证据时声称模型与真实硬件
一致。论文底层曲线数据尚未公开时，本项目不会声称完整复现该论文。

## 路线图

各版本目标和验收证据见 [docs/roadmap.md](docs/roadmap.md)。

代码采用 [MIT License](LICENSE)。贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)，引用信息见
[CITATION.cff](CITATION.cff)。
