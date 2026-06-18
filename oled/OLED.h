#ifndef __OLED_H
#define __OLED_H

#include <stdint.h>
#include "OLED_Data.h"

/*参数宏定义*********************/

/*FontSize参数取值*/
/*此参数值不仅用于判断，而且用于计算横向字符偏移，默认值为字体像素宽度*/
#define OLED_8X16				8
#define OLED_6X8				6

/*IsFilled参数数值*/
#define OLED_UNFILLED			0
#define OLED_FILLED				1

/*********************参数宏定义*/



/*屏幕尺寸宏定义 - 编译期可配。必须是 8 的倍数; 修改后整库重新编译。*/
#ifndef OLED_WIDTH
#define OLED_WIDTH  128
#endif
#ifndef OLED_HEIGHT
#define OLED_HEIGHT 64
#endif
#define OLED_PAGES  ((OLED_HEIGHT + 7) / 8)

/*I2C 传输参数 - 编译期可配。不同模块可能用不同地址。*/
/*  0x78 = SSD1306 7-bit 0x3C 左移 1 位 */
/*  0x7A = SH1106  7-bit 0x3D 左移 1 位 */
#ifndef OLED_I2C_ADDR
#define OLED_I2C_ADDR  0x78
#endif
/* I2C 控制字节: 0x00 = 命令流, 0x40 = 数据流 (SSD1306/SH1106 通用) */
#ifndef OLED_I2C_CMD
#define OLED_I2C_CMD   0x00
#endif
#ifndef OLED_I2C_DATA
#define OLED_I2C_DATA  0x40
#endif

/*控制器选择 - 决定 OLED_Init() 默认的初始化序列。*/
/*  如需更复杂的协议 (SSD1322 / SSD1351 / ILI9341 等),*/
/*  选 OLED_CTRL_USER 并在你的代码里 #define OLED_INIT_USER() 宏。*/
#ifndef OLED_CONTROLLER
#define OLED_CONTROLLER  OLED_CTRL_SSD1306
#endif
#define OLED_CTRL_SSD1306  0
#define OLED_CTRL_SH1106   1
#define OLED_CTRL_USER     2

/*函数声明*********************/

/*初始化函数*/
void OLED_Init(void);
void OLED_GPIO_Init(void);

void OLED_W_SDA(uint8_t BitValue);
void OLED_W_SCL(uint8_t BitValue);
/*更新函数*/
void OLED_Update(void);
void OLED_UpdateArea(int16_t X, int16_t Y, uint8_t Width, uint8_t Height);

/*显存控制函数*/
void OLED_Clear(void);
void OLED_ClearArea(int16_t X, int16_t Y, uint8_t Width, uint8_t Height);
void OLED_Reverse(void);
void OLED_ReverseArea(int16_t X, int16_t Y, uint8_t Width, uint8_t Height);

/*显示函数*/
void OLED_ShowChar(int16_t X, int16_t Y, char Char, uint8_t FontSize);
void OLED_ShowString(int16_t X, int16_t Y, char *String, uint8_t FontSize);
void OLED_ShowNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowSignedNum(int16_t X, int16_t Y, int32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowHexNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowBinNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowFloatNum(int16_t X, int16_t Y, double Number, uint8_t IntLength, uint8_t FraLength, uint8_t FontSize);
void OLED_ShowImage(int16_t X, int16_t Y, uint8_t Width, uint8_t Height, const uint8_t *Image);
void OLED_Printf(int16_t X, int16_t Y, uint8_t FontSize, char *format, ...);

/*绘图函数*/
void OLED_DrawPoint(int16_t X, int16_t Y);
uint8_t OLED_GetPoint(int16_t X, int16_t Y);
void OLED_DrawLine(int16_t X0, int16_t Y0, int16_t X1, int16_t Y1);
void OLED_DrawRectangle(int16_t X, int16_t Y, uint8_t Width, uint8_t Height, uint8_t IsFilled);
void OLED_DrawTriangle(int16_t X0, int16_t Y0, int16_t X1, int16_t Y1, int16_t X2, int16_t Y2, uint8_t IsFilled);
void OLED_DrawCircle(int16_t X, int16_t Y, uint8_t Radius, uint8_t IsFilled);
void OLED_DrawEllipse(int16_t X, int16_t Y, uint8_t A, uint8_t B, uint8_t IsFilled);
void OLED_DrawArc(int16_t X, int16_t Y, uint8_t Radius, int16_t StartAngle, int16_t EndAngle, uint8_t IsFilled);

/*********************函数声明*/
double round(double x);
double atan2(double y, double x);
#endif


/*****************江协科技|版权所有****************/
/*****************jiangxiekeji.com*****************/
