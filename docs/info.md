---
title: ASIC Onboarding Project
---

## How it works

This project implements an SPI-controlled PWM peripheral. An SPI interface
receives 16-bit transactions containing a register address and data value.
The written registers control which output pins are enabled, which outputs
use PWM mode, and the PWM duty cycle. The PWM peripheral generates a 3 kHz
signal derived from the 10 MHz clock and drives 16 output pins independently.

## How to test

Send SPI transactions at ~100 kHz using Mode 0 (data sampled on rising SCLK
edge). Each transaction is 16 bits: 1 R/W bit, 7 address bits, 8 data bits.

Write to the following registers:
- 0x00: Enable outputs on uo_out[7:0]
- 0x01: Enable outputs on uio_out[7:0]
- 0x02: Enable PWM on uo_out[7:0]
- 0x03: Enable PWM on uio_out[7:0]
- 0x04: PWM duty cycle (0x00 = 0%, 0xFF = 100%)

## External hardware

A microcontroller or SPI master device connected to ui_in[0] (SCLK),
ui_in[1] (COPI), and ui_in[2] (nCS).
