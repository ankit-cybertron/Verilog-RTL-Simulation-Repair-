// easy/testbench.v
// Testbench for counter_4bit — 5 test vectors
// Prints PASS/FAIL for each vector to stdout

`timescale 1ns/1ps

module tb_counter_4bit;
    reg        clk;
    reg        rst;
    wire [3:0] count;
    integer    failed = 0;

    counter_4bit dut (
        .clk   (clk),
        .rst   (rst),
        .count (count)
    );

    // 10ns clock period
    initial clk = 0;
    always #5 clk = ~clk;

    task check;
        input [3:0] expected;
        input [7:0] vector_id;
        begin
            if (count === expected) begin
                $display("VECTOR %0d: PASS expected=%0d actual=%0d", vector_id, expected, count);
            end else begin
                $display("VECTOR %0d: FAIL expected=%0d actual=%0d", vector_id, expected, count);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        // Vector 0: Reset behaviour
        rst = 1; @(posedge clk); #1;
        check(4'd0, 0);

        // Vector 1: Release reset, count goes to 1
        rst = 0; @(posedge clk); #1;
        check(4'd1, 1);

        // Vector 2: Count goes to 2
        @(posedge clk); #1;
        check(4'd2, 2);

        // Vector 3: Count goes to 3
        @(posedge clk); #1;
        check(4'd3, 3);

        // Vector 4: Mid-count synchronous reset back to 0
        rst = 1; @(posedge clk); #1;
        check(4'd0, 4);

        $display("SIMULATION_DONE failed=%0d", failed);
        $finish;
    end
endmodule
