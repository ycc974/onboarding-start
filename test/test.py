# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut): # Prove PWM runs at 3000Hz
    dut._log.info("Start PWM Frequency test")

    # Set the clock period to 100 ns 
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Output enable
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    # PWM enable
    await send_spi_transaction(dut, 1, 0x02, 0x01)

    # Duty cycle reg (128/256)
    await send_spi_transaction(dut, 1, 0x04, 0x80)

    
    await ClockCycles(dut.clk, 3333)

    # Find first rising edge
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value & 0x01:
            break

    # Wait to go LOW
    while True:
        await ClockCycles(dut.clk, 1)
        if not (dut.uo_out.value & 0x01):
            break

    # Measure from one rising edge to next rising edge = one full period
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value & 0x01:
            break
    start_time = cocotb.utils.get_sim_time(units="ns")

    # Wait for next rising edge
    while True:
        await ClockCycles(dut.clk, 1)
        if not (dut.uo_out.value & 0x01):
            break
    while True:
        await ClockCycles(dut.clk, 1)
        if dut.uo_out.value & 0x01:
            break
    end_time = cocotb.utils.get_sim_time(units="ns")

    # Frequency=10^9ns/period(ns)
    period_ns = end_time - start_time
    frequency_hz = 1e9 / period_ns

    dut._log.info(f"Measured period: {period_ns} ns")
    dut._log.info(f"Measured frequency: {frequency_hz:.2f} Hz")

    # Assert frequency is within 1% of 3000 Hz
    assert 2970 <= frequency_hz <= 3030, \
        f"Frequency {frequency_hz:.2f} Hz out of range (2970-3030 Hz)"

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable output 
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    await send_spi_transaction(dut, 1, 0x02, 0x01)

    # Test 0% 
    dut._log.info("Testing duty cycle 0x00 (0%)")
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    await ClockCycles(dut.clk, 6666)
    # Sample 10 times across a full period, should always be 0
    for _ in range(10):
        await ClockCycles(dut.clk, 333)
        assert (dut.uo_out.value & 0x01) == 0, \
            f"Expected output low for 0% duty cycle, got {dut.uo_out.value}"
    dut._log.info("0% duty cycle OK")

    # Test 100% 
    dut._log.info("Testing duty cycle 0xFF (100%)")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    await ClockCycles(dut.clk, 6666)
    # Sample 10 times across a full period, should always be 1
    for _ in range(10):
        await ClockCycles(dut.clk, 333)
        assert (dut.uo_out.value & 0x01) == 1, \
            f"Expected output high for 100% duty cycle, got {dut.uo_out.value}"
    dut._log.info("100% duty cycle OK")

    # Test by measuring actual duty cycle
    test_cases = [
        (0x80, 50.0),   # 50%
        (0x40, 25.0),   # 25%
    ]

    for duty_reg, expected_pct in test_cases:
        dut._log.info(f"Testing duty cycle 0x{duty_reg:02X} ({expected_pct}%)")

        await send_spi_transaction(dut, 1, 0x04, duty_reg)
        await ClockCycles(dut.clk, 6666)

        # Wait for a rising edge
        timeout = 0
        while True:
            await ClockCycles(dut.clk, 1)
            timeout += 1
            if dut.uo_out.value & 0x01:
                break
            assert timeout < 10000, "Timed out waiting for rising edge"

        high_start = cocotb.utils.get_sim_time(units="ns")

        # Wait for falling edge
        while True:
            await ClockCycles(dut.clk, 1)
            if not (dut.uo_out.value & 0x01):
                break
        high_end = cocotb.utils.get_sim_time(units="ns")

        # Wait for next rising edge
        while True:
            await ClockCycles(dut.clk, 1)
            if dut.uo_out.value & 0x01:
                break
        period_end = cocotb.utils.get_sim_time(units="ns")

        high_time = high_end - high_start
        period = period_end - high_start
        measured_pct = (high_time / period) * 100.0

        dut._log.info(f"Measured: {measured_pct:.2f}% (expected {expected_pct}%)")

        assert abs(measured_pct - expected_pct) <= 1.0, \
            f"Duty cycle {measured_pct:.2f}% not within 1% of {expected_pct}%"

        dut._log.info(f"Duty cycle 0x{duty_reg:02X} OK")

    dut._log.info("PWM Duty Cycle test completed successfully")
