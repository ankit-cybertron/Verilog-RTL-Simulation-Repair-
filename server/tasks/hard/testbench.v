// hard/testbench.v
// Testbench for traffic_light FSM — 20 test vectors
// HOLD_CYCLES=3: each state holds for 3 clock cycles

`timescale 1ns/1ps

module tb_traffic_light;
    reg  clk, rst;
    wire red, green, yellow;
    integer failed = 0;

    // DUT with HOLD_CYCLES=3
    traffic_light #(.HOLD_CYCLES(3)) dut (
        .clk(clk), .rst(rst),
        .red(red), .green(green), .yellow(yellow)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task check;
        input exp_red, exp_green, exp_yellow;
        input [7:0] vid;
        begin
            if (red===exp_red && green===exp_green && yellow===exp_yellow)
                $display("VECTOR %0d: PASS red=%0d green=%0d yellow=%0d", vid, red, green, yellow);
            else begin
                $display("VECTOR %0d: FAIL exp_r=%0d exp_g=%0d exp_y=%0d got_r=%0d got_g=%0d got_y=%0d",
                    vid, exp_red, exp_green, exp_yellow, red, green, yellow);
                failed = failed + 1;
            end
        end
    endtask

    integer i;
    initial begin
        // Reset
        rst = 1;
        repeat(2) @(posedge clk); #1;

        // After reset: RED state, cycle 0
        check(1,0,0, 0);

        rst = 0;

        // RED holds for 3 cycles (HOLD_CYCLES=3)
        @(posedge clk); #1; check(1,0,0, 1);  // RED cycle 1
        @(posedge clk); #1; check(1,0,0, 2);  // RED cycle 2

        // Transition to GREEN
        @(posedge clk); #1; check(0,1,0, 3);  // GREEN cycle 0
        @(posedge clk); #1; check(0,1,0, 4);  // GREEN cycle 1
        @(posedge clk); #1; check(0,1,0, 5);  // GREEN cycle 2

        // Transition to YELLOW
        @(posedge clk); #1; check(0,0,1, 6);  // YELLOW cycle 0
        @(posedge clk); #1; check(0,0,1, 7);  // YELLOW cycle 1
        @(posedge clk); #1; check(0,0,1, 8);  // YELLOW cycle 2

        // Transition back to RED (full cycle test)
        @(posedge clk); #1; check(1,0,0, 9);  // RED again cycle 0
        @(posedge clk); #1; check(1,0,0, 10); // RED cycle 1
        @(posedge clk); #1; check(1,0,0, 11); // RED cycle 2

        // Second GREEN
        @(posedge clk); #1; check(0,1,0, 12); // GREEN cycle 0
        @(posedge clk); #1; check(0,1,0, 13); // GREEN cycle 1
        @(posedge clk); #1; check(0,1,0, 14); // GREEN cycle 2

        // Second YELLOW
        @(posedge clk); #1; check(0,0,1, 15); // YELLOW cycle 0
        @(posedge clk); #1; check(0,0,1, 16); // YELLOW cycle 1
        @(posedge clk); #1; check(0,0,1, 17); // YELLOW cycle 2

        // Mid-cycle reset test
        @(posedge clk); #1;                    // Should be RED again
        rst = 1; @(posedge clk); #1;
        check(1,0,0, 18);                      // Reset to RED

        rst = 0; @(posedge clk); #1;
        check(1,0,0, 19);                      // Still RED (cycle 1 of 3)

        $display("SIMULATION_DONE failed=%0d", failed);
        $finish;
    end
endmodule