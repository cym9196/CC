/**
 * OLED_Controller.h — controller-specific init sequence.
 *
 * Picks the right init command list at compile time based on OLED_CONTROLLER.
 * For controllers not in the predefined list (SSD1322 / SSD1351 / ILI9341 etc.),
 * select OLED_CTRL_USER and #define OLED_INIT_USER()  yourself before
 * including OLED.h.
 *
 * Usage:
 *   #include "OLED_Controller.h"   // pick a default init sequence
 *   #include "OLED.h"             // brings in the rest
 *
 * Each init sequence is a do-while-0 block that ends with display ON.
 * The high-level OLED_Init() function (in OLED.c) wraps it in:
 *     OLED_GPIO_Init();
 *     OLED_INIT_SEQUENCE();
 *     OLED_Clear();
 *     OLED_Update();
 */
#ifndef __OLED_CONTROLLER_H
#define __OLED_CONTROLLER_H

/* SSD1306 — 0.96" / 1.3" OLED, page addressing, charge-pump-on */
#if OLED_CONTROLLER == OLED_CTRL_SSD1306
    #ifndef OLED_INIT_SEQUENCE
    #define OLED_INIT_SEQUENCE() do {                            \
        OLED_WriteCommand(0xAE); /* display off */               \
        OLED_WriteCommand(0xD5); OLED_WriteCommand(0x80);       \
        OLED_WriteCommand(0xA8); OLED_WriteCommand(0x3F);       \
        OLED_WriteCommand(0xD3); OLED_WriteCommand(0x00);       \
        OLED_WriteCommand(0x40);                                \
        OLED_WriteCommand(0x8D); OLED_WriteCommand(0x14);       \
        OLED_WriteCommand(0x20); OLED_WriteCommand(0x00);       \
        OLED_WriteCommand(0xA1);                                \
        OLED_WriteCommand(0xC8);                                \
        OLED_WriteCommand(0xDA); OLED_WriteCommand(0x12);       \
        OLED_WriteCommand(0x81); OLED_WriteCommand(0xCF);       \
        OLED_WriteCommand(0xD9); OLED_WriteCommand(0xF1);       \
        OLED_WriteCommand(0xDB); OLED_WriteCommand(0x30);       \
        OLED_WriteCommand(0xA4);                                \
        OLED_WriteCommand(0xA6);                                \
        OLED_WriteCommand(0xAF);                                \
    } while(0)
    #endif

/* SH1106 — 1.3" OLED, 132 segments (offset 2 from left for 128 display),
 * page addressing. Differs from SSD1306 mainly in charge-pump default
 * and a small COM-pins tweak for some modules. */
#elif OLED_CONTROLLER == OLED_CTRL_SH1106
    #ifndef OLED_INIT_SEQUENCE
    #define OLED_INIT_SEQUENCE() do {                            \
        OLED_WriteCommand(0xAE); /* display off */               \
        OLED_WriteCommand(0xD5); OLED_WriteCommand(0x80);       \
        OLED_WriteCommand(0xA8); OLED_WriteCommand(0x3F);       \
        OLED_WriteCommand(0xD3); OLED_WriteCommand(0x00);       \
        OLED_WriteCommand(0x40);                                \
        OLED_WriteCommand(0x8D); OLED_WriteCommand(0x14);       \
        OLED_WriteCommand(0x20); OLED_WriteCommand(0x00);       \
        OLED_WriteCommand(0xA1);                                \
        OLED_WriteCommand(0xC8);                                \
        OLED_WriteCommand(0xDA); OLED_WriteCommand(0x12);       \
        OLED_WriteCommand(0x81); OLED_WriteCommand(0xCF);       \
        OLED_WriteCommand(0xD9); OLED_WriteCommand(0xF2);       \
        OLED_WriteCommand(0xDB); OLED_WriteCommand(0x40);       \
        OLED_WriteCommand(0xA4);                                \
        OLED_WriteCommand(0xA6);                                \
        OLED_WriteCommand(0xAF);                                \
    } while(0)
    #endif

/* User-provided — caller must #define OLED_INIT_USER()  before including
 * this file.  Use this for SSD1322, SSD1351, ILI9341, etc. — controllers
 * with very different command sets. */
#elif OLED_CONTROLLER == OLED_CTRL_USER
    #ifndef OLED_INIT_USER
    #error "OLED_CONTROLLER = OLED_CTRL_USER but OLED_INIT_USER() is not defined. \
Provide your own init sequence: #define OLED_INIT_USER() { ...your commands... }"
    #endif
    #ifndef OLED_INIT_SEQUENCE
    #define OLED_INIT_SEQUENCE()  OLED_INIT_USER()
    #endif
#else
    #error "unknown OLED_CONTROLLER value; must be OLED_CTRL_SSD1306 / OLED_CTRL_SH1106 / OLED_CTRL_USER"
#endif

#endif /* __OLED_CONTROLLER_H */
