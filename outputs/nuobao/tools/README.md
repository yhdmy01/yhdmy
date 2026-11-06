# Rhino 脚本

`asd_fixed.py` 是 Rhino 8 Python 3 / RhinoCommon 版本的桌面音箱/闹钟近似建模脚本。

修复内容：将不存在的 `Material.Glossiness` 替换为 RhinoCommon 支持的 `Material.Shine`，并把 0–1 的光泽参数换算为 0–255。
