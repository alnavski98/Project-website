## Overview

The LED baton is an embedded electronics project based on an
ATmega328P microcontroller and a WS2812B addressable LED strip.

## Objectives

- Create several selectable lighting modes
- Monitor battery voltage
- Support USB-C charging
- Keep the firmware modular

## Hardware

The project uses:

- ATmega328P
- WS2812B LEDs
- BQ25887 battery charger
- Physical buttons
- Two-cell battery pack

## Firmware

The firmware is written in C and divided into modules for:

- LED control
- UART communication
- Battery monitoring
- Button input
- Lighting patterns

## Testing

The system was tested using a bench power supply, multimeter,
oscilloscope and serial output.

## Lessons learned

The project improved my understanding of timing-sensitive LED
communication, battery management and modular embedded firmware.