# CC - OLED Display Driver Library

一个用于嵌入式系统的 OLED 显示屏驱动库，支持多种字体和图形绘制功能。

## 📦 项目内容

- `CC.exe` - 编译后的可执行文件
- `CC.zip` - 项目压缩包
- `LICENSE` - Boost Software License 1.0
- `oled/` - OLED 驱动源代码目录

## 📁 oled 目录文件

| 文件 | 说明 |
|------|------|
| `OLED.h` | OLED 驱动头文件，包含所有函数声明 |
| `OLED.c` | OLED 驱动实现文件 |
| `OLED_Data.h` | 字模数据头文件 |
| `OLED_Data.c` | 字模数据实现文件 |

## 🚀 主要功能

### 初始化与刷新
- `OLED_Init()` - 初始化 OLED 显示屏
- `OLED_GPIO_Init()` - 初始化 GPIO 引脚
- `OLED_Update()` - 更新整个屏幕
- `OLED_UpdateArea()` - 更新指定区域

### 屏幕控制
- `OLED_Clear()` - 清空整个屏幕
- `OLED_ClearArea()` - 清空指定区域
- `OLED_Reverse()` - 反色整个屏幕
- `OLED_ReverseArea()` - 反色指定区域

### 文本显示
- `OLED_ShowChar()` - 显示单个字符
- `OLED_ShowString()` - 显示字符串
- `OLED_ShowNum()` - 显示无符号整数
- `OLED_ShowSignedNum()` - 显示有符号整数
- `OLED_ShowHexNum()` - 显示十六进制数
- `OLED_ShowBinNum()` - 显示二进制数
- `OLED_ShowFloatNum()` - 显示浮点数
- `OLED_Printf()` - 格式化输出文本

### 图形绘制
- `OLED_DrawPoint()` - 绘制点
- `OLED_DrawLine()` - 绘制直线
- `OLED_DrawRectangle()` - 绘制矩形
- `OLED_DrawTriangle()` - 绘制三角形
- `OLED_DrawCircle()` - 绘制圆形
- `OLED_DrawEllipse()` - 绘制椭圆
- `OLED_DrawArc()` - 绘制圆弧
- `OLED_ShowImage()` - 显示图片

## 🔧 使用示例

```c
#include "OLED.h"

int main(void) {
    // 初始化 OLED
    OLED_Init();
    
    // 清空屏幕
    OLED_Clear();
    
    // 显示字符串 (x, y, "文本", 字体大小)
    OLED_ShowString(0, 0, "Hello OLED", OLED_8X16);
    
    // 显示数字
    OLED_ShowNum(0, 20, 12345, 5, OLED_8X16);
    
    // 绘制矩形
    OLED_DrawRectangle(10, 40, 50, 30, OLED_UNFILLED);
    
    // 更新屏幕显示
    OLED_Update();
    
    while(1) {
        // 主循环
    }
}
```

## ⚙️ 配置说明

### 字体大小
- `OLED_8X16` - 8x16 像素字体（默认）
- `OLED_6X8` - 6x8 像素字体

### 填充模式
- `OLED_UNFILLED` - 空心/轮廓
- `OLED_FILLED` - 实心/填充

## 📝 注意事项

1. 确保 GPIO 引脚配置正确（SDA、SCL）
2. 字体大小参数影响字符偏移计算
3. 显示浮点数时需要指定整数和小数部分的位数
4. 绘图函数支持轮廓和填充两种模式

## 📄 许可证

本项目采用 [Boost Software License - Version 1.0](LICENSE) 开源。

## 🔗 来源

江谢科技 - jiangxiekeji.com

---

**分支：loh** - 使用说明优化版本
