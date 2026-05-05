`default_nettype none

module spi_peripheral (
    input  wire clk,
    input  wire rst_n,
    input  wire sclk,
    input  wire copi,
    input  wire ncs,
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);

    // CDC 2-stage synchronizers
    reg sclk_s1, sclk_sync;
    reg copi_s1, copi_sync;
    reg ncs_s1,  ncs_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_s1 <= 0; sclk_sync <= 0;
            copi_s1 <= 0; copi_sync <= 0;
            ncs_s1  <= 1; ncs_sync  <= 1;
        end else begin
            sclk_s1 <= sclk; sclk_sync <= sclk_s1;
            copi_s1 <= copi; copi_sync <= copi_s1;
            ncs_s1  <= ncs;  ncs_sync  <= ncs_s1;
        end
    end

    // Edge detection
    reg sclk_prev, ncs_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_prev <= 0;
            ncs_prev  <= 1;
        end else begin
            sclk_prev <= sclk_sync;
            ncs_prev  <= ncs_sync;
        end
    end

    wire sclk_rising = (sclk_sync && !sclk_prev);
    wire ncs_falling = (!ncs_sync && ncs_prev);
    wire ncs_rising  = (ncs_sync  && !ncs_prev);

    // Shift register and bit counter
    reg [15:0] shift_reg;
    reg [4:0]  bit_count;
    reg        active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg <= 0;
            bit_count <= 0;
            active    <= 0;
        end else begin
            if (ncs_falling) begin
                active    <= 1;
                bit_count <= 0;
                shift_reg <= 0;
            end
            if (active && sclk_rising) begin
                shift_reg <= {shift_reg[14:0], copi_sync};
                bit_count <= bit_count + 1;
            end
            if (ncs_rising) begin
                active <= 0;
            end
        end
    end

    // Decode and write registers on nCS rising edge
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_reg_out_7_0  <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0  <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle  <= 8'h00;
        end else if (ncs_rising && active) begin
            if (shift_reg[15] == 1'b1) begin
                case (shift_reg[14:8])
                    7'h00: en_reg_out_7_0  <= shift_reg[7:0];
                    7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                    7'h02: en_reg_pwm_7_0  <= shift_reg[7:0];
                    7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                    7'h04: pwm_duty_cycle  <= shift_reg[7:0];
                    default: ; // ignore invalid addresses
                endcase
            end
        end
    end

endmodule